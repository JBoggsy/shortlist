"""DefaultOnboardingAgent — onboarding interview using a monolithic ReAct loop.

Same streaming/tool-calling pattern as DefaultAgent, but with an
onboarding-specific system prompt and detection of the [ONBOARDING_COMPLETE]
marker to signal that the interview is finished.
"""

import json
import logging
import uuid
from collections.abc import Generator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool

from backend.agent.base import OnboardingAgent
from backend.agent.tools import AgentTools
from backend.agent.user_profile import set_onboarded

from .agent import _extract_text, _recover_ollama_tool_calls
from .prompts import ONBOARDING_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 15

# Onboarding only needs profile + resume tools, but we bind all tools and
# let the system prompt guide usage.  Keeping it simple avoids maintaining
# a separate tool-subset list.


def _build_langchain_tools(agent_tools: AgentTools) -> list[StructuredTool]:
    """Convert AgentTools definitions into LangChain StructuredTool objects."""
    lc_tools = []
    for defn in agent_tools.get_tool_definitions():
        name = defn["name"]
        description = defn["description"]
        args_schema = defn["args_schema"]

        def _make_func(tool_name):
            def _run(**kwargs):
                return agent_tools.execute(tool_name, kwargs)
            return _run

        tool = StructuredTool(
            name=name,
            description=description,
            func=_make_func(name),
            args_schema=args_schema,
        )
        lc_tools.append(tool)
    return lc_tools


class DefaultOnboardingAgent(OnboardingAgent):
    """Onboarding interview agent — monolithic ReAct loop."""

    def __init__(self, model: BaseChatModel):
        self.model = model
        self._pending_events: list[dict] = []

        self.tools = AgentTools(
            event_callback=self._on_tool_event,
        )
        lc_tools = _build_langchain_tools(self.tools)
        self.bound_model = model.bind_tools(lc_tools) if lc_tools else model

    def _on_tool_event(self, event: dict):
        self._pending_events.append(event)

    def run(self, messages: list[dict]) -> Generator[dict, None, None]:
        lc_messages: list = [SystemMessage(content=ONBOARDING_SYSTEM_PROMPT)]
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            elif msg["role"] == "assistant":
                lc_messages.append(AIMessage(content=msg["content"]))

        full_text = ""

        for _iteration in range(MAX_ITERATIONS):
            try:
                # Stream the LLM response, accumulating chunks via
                # LangChain's built-in __add__ so tool calls are
                # properly assembled across all providers.
                collected_content = ""
                full_response = None

                for chunk in self.bound_model.stream(lc_messages):
                    if chunk.content:
                        text_piece = _extract_text(chunk.content)
                        if text_piece:
                            collected_content += text_piece
                            yield {"event": "text_delta", "data": {"content": text_piece}}

                    # Accumulate chunks — LangChain merges tool_call_chunks
                    # into complete tool_calls automatically.
                    if full_response is None:
                        full_response = chunk
                    else:
                        full_response = full_response + chunk

                full_text += collected_content

                # Check for onboarding completion marker
                if "[ONBOARDING_COMPLETE]" in full_text:
                    set_onboarded(True)
                    yield {"event": "onboarding_complete", "data": {}}

                # Extract properly assembled tool calls from the merged response
                tool_calls = []
                if full_response and getattr(full_response, "tool_calls", None):
                    for tc in full_response.tool_calls:
                        tool_calls.append({
                            "id": tc.get("id") or str(uuid.uuid4()),
                            "name": tc.get("name", ""),
                            "args": tc.get("args", {}),
                        })

                # No tool calls — we're done
                if not tool_calls:
                    break

                # Filter out any tool calls with missing names (malformed)
                valid_tool_calls = [tc for tc in tool_calls if tc["name"]]
                if not valid_tool_calls:
                    logger.warning("All tool calls had empty names — treating as text-only response")
                    break
                tool_calls = valid_tool_calls

                # Build AIMessage with tool_calls for the history
                ai_tool_calls = [
                    {"id": tc["id"], "name": tc["name"], "args": tc["args"]}
                    for tc in tool_calls
                ]
                ai_msg = AIMessage(content=collected_content, tool_calls=ai_tool_calls)
                lc_messages.append(ai_msg)

                # Execute each tool call
                for tc in tool_calls:
                    yield {
                        "event": "tool_start",
                        "data": {"id": tc["id"], "name": tc["name"], "arguments": tc["args"]},
                    }

                    result = self.tools.execute(tc["name"], tc["args"])

                    for pending in self._pending_events:
                        yield pending
                    self._pending_events.clear()

                    if "error" in result:
                        yield {
                            "event": "tool_error",
                            "data": {"id": tc["id"], "name": tc["name"], "error": result["error"]},
                        }
                    else:
                        yield {
                            "event": "tool_result",
                            "data": {"id": tc["id"], "name": tc["name"], "result": result},
                        }

                    lc_messages.append(
                        ToolMessage(
                            content=json.dumps(result),
                            tool_call_id=tc["id"],
                        )
                    )

            except Exception as exc:
                logger.exception("DefaultOnboardingAgent error on iteration %d", _iteration)
                if collected_content:
                    full_text += collected_content

                # Try Ollama tool-call recovery
                recovered = _recover_ollama_tool_calls(exc, self.tools)
                if recovered:
                    ai_tool_calls = [
                        {"id": tc["id"], "name": tc["name"], "args": tc["args"]}
                        for tc in recovered
                    ]
                    ai_msg = AIMessage(content=collected_content, tool_calls=ai_tool_calls)
                    lc_messages.append(ai_msg)
                    for tc in recovered:
                        yield {
                            "event": "tool_start",
                            "data": {"id": tc["id"], "name": tc["name"], "arguments": tc["args"]},
                        }
                        result = self.tools.execute(tc["name"], tc["args"])
                        for pending in self._pending_events:
                            yield pending
                        self._pending_events.clear()
                        if "error" in result:
                            yield {
                                "event": "tool_error",
                                "data": {"id": tc["id"], "name": tc["name"], "error": result["error"]},
                            }
                        else:
                            yield {
                                "event": "tool_result",
                                "data": {"id": tc["id"], "name": tc["name"], "result": result},
                            }
                        lc_messages.append(
                            ToolMessage(content=json.dumps(result), tool_call_id=tc["id"])
                        )
                    continue

                if _iteration >= MAX_ITERATIONS - 1:
                    yield {"event": "error", "data": {"message": str(exc)}}
                    return
                logger.info("Retrying after error on iteration %d", _iteration)
                continue

        yield {"event": "done", "data": {"content": full_text}}
