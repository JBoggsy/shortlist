"""DefaultAgent — main chat agent using a monolithic ReAct loop.

Uses LiteLLM's ``completion()`` with streaming and tool calling to run a
tool-calling loop: each iteration streams an LLM response; if the response
includes tool calls they are executed and the results fed back, then the
loop continues.
"""

import json
import logging
import uuid
from collections.abc import Generator

import litellm

from backend.agent.base import Agent
from backend.agent.tools import AgentTools
from backend.agent.user_profile import read_profile
from backend.llm.llm_factory import LLMConfig

from .prompts import AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 15


def _build_openai_tools(agent_tools: AgentTools) -> list[dict]:
    """Convert AgentTools definitions into OpenAI function-calling format."""
    tools = []
    for defn in agent_tools.get_tool_definitions():
        schema = defn["args_schema"]
        tool = {
            "type": "function",
            "function": {
                "name": defn["name"],
                "description": defn["description"],
                "parameters": schema.model_json_schema() if schema else {
                    "type": "object", "properties": {}
                },
            },
        }
        tools.append(tool)
    return tools


def _accumulate_tool_calls(tool_call_chunks: dict[int, dict], delta_tool_calls: list) -> None:
    """Accumulate streaming tool call fragments into complete tool calls."""
    for tc_delta in delta_tool_calls:
        idx = tc_delta.index
        if idx not in tool_call_chunks:
            tool_call_chunks[idx] = {
                "id": tc_delta.id or "",
                "name": "",
                "arguments": "",
            }
        entry = tool_call_chunks[idx]
        if tc_delta.id:
            entry["id"] = tc_delta.id
        if tc_delta.function:
            if tc_delta.function.name:
                entry["name"] += tc_delta.function.name
            if tc_delta.function.arguments:
                entry["arguments"] += tc_delta.function.arguments


class DefaultAgent(Agent):
    """Main chat agent — monolithic ReAct loop with tool calling."""

    def __init__(
        self,
        llm_config: LLMConfig,
        search_api_key: str = "",
        rapidapi_key: str = "",
        conversation_id: int | None = None,
    ):
        self.llm_config = llm_config
        self.conversation_id = conversation_id

        # Queued events from tool callbacks (e.g. search_result_added)
        self._pending_events: list[dict] = []

        self.tools = AgentTools(
            search_api_key=search_api_key,
            rapidapi_key=rapidapi_key,
            conversation_id=conversation_id,
            event_callback=self._on_tool_event,
        )
        self.openai_tools = _build_openai_tools(self.tools)

    def _on_tool_event(self, event: dict):
        """Callback for tool-emitted SSE events (e.g. search_result_added)."""
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
        # Build the message list
        profile_content = read_profile()
        system_prompt = AGENT_SYSTEM_PROMPT.format(user_profile=profile_content)

        llm_messages: list[dict] = [{"role": "system", "content": system_prompt}]
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

                    # Accumulate text content for SSE streaming
                    if delta.content:
                        collected_content += delta.content
                        yield {"event": "text_delta", "data": {"content": delta.content}}

                    # Accumulate tool call fragments
                    if delta.tool_calls:
                        _accumulate_tool_calls(tool_call_chunks, delta.tool_calls)

                full_text += collected_content

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

                    # Flush any pending events from tool callbacks
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

                    # Add tool result to history
                    llm_messages.append({
                        "role": "tool",
                        "tool_call_id": tc["id"],
                        "content": json.dumps(result),
                    })

            except Exception as exc:
                logger.exception("DefaultAgent error on iteration %d", _iteration)

                # If we collected text before the error, preserve it
                if collected_content:
                    full_text += collected_content

                if _iteration >= MAX_ITERATIONS - 1:
                    yield {"event": "error", "data": {"message": str(exc)}}
                    return
                logger.info("Retrying after error on iteration %d", _iteration)
                continue

        yield {"event": "done", "data": {"content": full_text}}
