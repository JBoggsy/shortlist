"""DefaultAgent — main chat agent using a monolithic ReAct loop.

Uses LangChain's ``bind_tools`` + streaming to run a tool-calling loop:
each iteration streams an LLM response; if the response includes tool calls
they are executed and the results fed back, then the loop continues.
"""

import json
import logging
import re
import uuid
from collections.abc import Generator

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import StructuredTool

from backend.agent.base import Agent
from backend.agent.tools import AgentTools
from backend.agent.user_profile import read_profile

from .prompts import AGENT_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 15


def _extract_text(content) -> str:
    """Extract plain text from a streaming chunk's content field.

    LangChain providers return content in different formats:
    - str (OpenAI, Ollama, Gemini): the text directly
    - list of content blocks (Anthropic): [{"type": "text", "text": "..."}]
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                parts.append(block.get("text", ""))
            elif isinstance(block, str):
                parts.append(block)
        return "".join(parts)
    return ""


def _recover_ollama_tool_calls(exc, agent_tools: AgentTools) -> list[dict] | None:
    """Try to recover valid tool calls from an Ollama ResponseError.

    Ollama models sometimes prepend "thinking" text before the JSON tool-call
    arguments, which causes Ollama's server-side parser to fail with HTTP 500.
    The error message contains the raw text, which often has valid JSON embedded
    at the end. This function tries to extract it and match it to a tool.

    Returns a list of tool-call dicts (id, name, args) or None if recovery fails.
    """
    try:
        from ollama._types import ResponseError
    except ImportError:
        return None

    if not isinstance(exc, ResponseError):
        return None

    msg = str(exc)
    # Extract raw text: "error parsing tool call: raw='...', err=..."
    raw_match = re.search(r"raw='(.*)', err=", msg, re.DOTALL)
    if not raw_match:
        return None

    raw_text = raw_match.group(1)

    # Try to find the last complete JSON object in the raw text.
    # Scan backwards from the end to find the outermost { ... } pair.
    json_obj = _extract_last_json_object(raw_text)
    if json_obj is None:
        return None

    # Match the JSON keys to a tool schema
    tool_name = _match_json_to_tool(json_obj, agent_tools)
    if not tool_name:
        return None

    logger.info("Recovered Ollama tool call: %s with %d args", tool_name, len(json_obj))
    return [{
        "id": str(uuid.uuid4()),
        "name": tool_name,
        "args": json_obj,
    }]


def _extract_last_json_object(text: str) -> dict | None:
    """Find and parse the last valid JSON object in a string."""
    # Find the last '{' and try parsing from there, then back up if it fails
    end = text.rfind("}")
    if end == -1:
        return None

    # Try progressively earlier '{' positions until we find valid JSON
    start = end
    while True:
        start = text.rfind("{", 0, start)
        if start == -1:
            return None
        candidate = text[start:end + 1]
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict):
                return obj
        except (json.JSONDecodeError, ValueError):
            pass
        # Back up to try an earlier '{'
        if start == 0:
            return None


def _match_json_to_tool(json_obj: dict, agent_tools: AgentTools) -> str | None:
    """Match a JSON object's keys to the best-fitting tool schema.

    Returns the tool name or None if no good match is found.
    """
    obj_keys = set(json_obj.keys())
    if not obj_keys:
        return None

    best_name = None
    best_score = 0

    for defn in agent_tools.get_tool_definitions():
        schema = defn.get("args_schema")
        if schema is None:
            continue

        schema_fields = set(schema.model_fields.keys())
        required = {k for k, v in schema.model_fields.items() if v.is_required()}

        # All required fields must be present
        if not required.issubset(obj_keys):
            continue

        # Score = how many of the JSON keys are valid schema fields
        overlap = len(obj_keys & schema_fields)
        extra = len(obj_keys - schema_fields)

        # Penalise extra keys that don't belong to the schema
        score = overlap - extra * 0.5

        if score > best_score:
            best_score = score
            best_name = defn["name"]

    return best_name


def _build_langchain_tools(agent_tools: AgentTools) -> list[StructuredTool]:
    """Convert AgentTools definitions into LangChain StructuredTool objects."""
    lc_tools = []
    for defn in agent_tools.get_tool_definitions():
        name = defn["name"]
        description = defn["description"]
        args_schema = defn["args_schema"]

        # Create a closure that captures tool name
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


class DefaultAgent(Agent):
    """Main chat agent — monolithic ReAct loop with tool calling."""

    def __init__(
        self,
        model: BaseChatModel,
        search_api_key: str = "",
        adzuna_app_id: str = "",
        adzuna_app_key: str = "",
        adzuna_country: str = "us",
        jsearch_api_key: str = "",
        conversation_id: int | None = None,
    ):
        self.model = model
        self.conversation_id = conversation_id

        # Queued events from tool callbacks (e.g. search_result_added)
        self._pending_events: list[dict] = []

        self.tools = AgentTools(
            search_api_key=search_api_key,
            adzuna_app_id=adzuna_app_id,
            adzuna_app_key=adzuna_app_key,
            adzuna_country=adzuna_country,
            jsearch_api_key=jsearch_api_key,
            conversation_id=conversation_id,
            event_callback=self._on_tool_event,
        )
        lc_tools = _build_langchain_tools(self.tools)
        self.bound_model = model.bind_tools(lc_tools) if lc_tools else model

    def _on_tool_event(self, event: dict):
        """Callback for tool-emitted SSE events (e.g. search_result_added)."""
        self._pending_events.append(event)

    def run(self, messages: list[dict]) -> Generator[dict, None, None]:
        # Build the LangChain message list
        profile_content = read_profile()
        system_prompt = AGENT_SYSTEM_PROMPT.format(user_profile=profile_content)

        lc_messages: list = [SystemMessage(content=system_prompt)]
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
                    # Accumulate text content for SSE streaming
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

                    # Add ToolMessage to history
                    lc_messages.append(
                        ToolMessage(
                            content=json.dumps(result),
                            tool_call_id=tc["id"],
                        )
                    )

            except Exception as exc:
                logger.exception("DefaultAgent error on iteration %d", _iteration)

                # If we collected text before the error, preserve it
                if collected_content:
                    full_text += collected_content

                # Try to recover tool calls from Ollama's "error parsing
                # tool call" response — the raw text often contains
                # valid JSON that Ollama failed to parse.
                recovered = _recover_ollama_tool_calls(exc, self.tools)
                if recovered:
                    # Build an AIMessage with the recovered tool calls
                    ai_tool_calls = [
                        {"id": tc["id"], "name": tc["name"], "args": tc["args"]}
                        for tc in recovered
                    ]
                    ai_msg = AIMessage(content=collected_content, tool_calls=ai_tool_calls)
                    lc_messages.append(ai_msg)

                    # Execute the recovered tool calls
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
                    # Continue the loop — the model will see the tool result
                    continue

                # No recovery possible — retry or bail
                if _iteration >= MAX_ITERATIONS - 1:
                    yield {"event": "error", "data": {"message": str(exc)}}
                    return
                logger.info("Retrying after error on iteration %d", _iteration)
                continue

        yield {"event": "done", "data": {"content": full_text}}
