"""DefaultOnboardingAgent — onboarding interview using a monolithic ReAct loop.

Same streaming/tool-calling pattern as DefaultAgent, but with an
onboarding-specific system prompt and detection of the [ONBOARDING_COMPLETE]
marker to signal that the interview is finished.
"""

import json
import logging
import uuid
from collections.abc import Generator

import litellm

from backend.agent.base import OnboardingAgent
from backend.agent.tools import AgentTools
from backend.agent.user_profile import set_onboarded
from backend.llm.llm_factory import LLMConfig

from .agent import _accumulate_tool_calls, _build_openai_tools
from .prompts import ONBOARDING_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 15

# Onboarding only needs profile + resume tools, but we bind all tools and
# let the system prompt guide usage.  Keeping it simple avoids maintaining
# a separate tool-subset list.


class DefaultOnboardingAgent(OnboardingAgent):
    """Onboarding interview agent — monolithic ReAct loop."""

    def __init__(self, llm_config: LLMConfig):
        self.llm_config = llm_config
        self._pending_events: list[dict] = []

        self.tools = AgentTools(
            event_callback=self._on_tool_event,
        )
        self.openai_tools = _build_openai_tools(self.tools)

    def _on_tool_event(self, event: dict):
        self._pending_events.append(event)

    def _completion_kwargs(self) -> dict:
        """Build kwargs for litellm.completion()."""
        kwargs = {
            "model": self.llm_config.model,
            "max_tokens": self.llm_config.max_tokens,
            "stream": True,
        }
        if self.llm_config.api_key:
            kwargs["api_key"] = self.llm_config.api_key
        if self.llm_config.api_base:
            kwargs["api_base"] = self.llm_config.api_base
        if self.openai_tools:
            kwargs["tools"] = self.openai_tools
        return kwargs

    def run(self, messages: list[dict]) -> Generator[dict, None, None]:
        llm_messages: list[dict] = [{"role": "system", "content": ONBOARDING_SYSTEM_PROMPT}]
        for msg in messages:
            if msg["role"] == "user":
                llm_messages.append({"role": "user", "content": msg["content"]})
            elif msg["role"] == "assistant":
                llm_messages.append({"role": "assistant", "content": msg["content"]})

        full_text = ""

        for _iteration in range(MAX_ITERATIONS):
            try:
                collected_content = ""
                tool_call_chunks: dict[int, dict] = {}

                response = litellm.completion(
                    messages=llm_messages,
                    **self._completion_kwargs(),
                )

                for chunk in response:
                    delta = chunk.choices[0].delta

                    if delta.content:
                        collected_content += delta.content
                        yield {"event": "text_delta", "data": {"content": delta.content}}

                    if delta.tool_calls:
                        _accumulate_tool_calls(tool_call_chunks, delta.tool_calls)

                full_text += collected_content

                # Check for onboarding completion marker
                if "[ONBOARDING_COMPLETE]" in full_text:
                    set_onboarded(True)
                    yield {"event": "onboarding_complete", "data": {}}

                # Build completed tool calls from accumulated fragments
                tool_calls = []
                for idx in sorted(tool_call_chunks.keys()):
                    tc = tool_call_chunks[idx]
                    try:
                        args = json.loads(tc["arguments"]) if tc["arguments"] else {}
                    except json.JSONDecodeError:
                        args = {}
                    tool_calls.append({
                        "id": tc["id"] or str(uuid.uuid4()),
                        "name": tc["name"],
                        "args": args,
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

                # Build assistant message with tool_calls for the history
                assistant_tool_calls = [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["args"])},
                    }
                    for tc in tool_calls
                ]
                llm_messages.append({
                    "role": "assistant",
                    "content": collected_content or None,
                    "tool_calls": assistant_tool_calls,
                })

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

                    llm_messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(result),
                    })

            except Exception as exc:
                logger.exception("DefaultOnboardingAgent error on iteration %d", _iteration)
                if collected_content:
                    full_text += collected_content

                if _iteration >= MAX_ITERATIONS - 1:
                    yield {"event": "error", "data": {"message": str(exc)}}
                    return
                logger.info("Retrying after error on iteration %d", _iteration)
                continue

        yield {"event": "done", "data": {"content": full_text}}
