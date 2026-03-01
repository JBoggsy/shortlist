"""SSE event helper functions for yielding standardized events."""

import uuid


def yield_text(content: str) -> dict:
    """Create a text_delta SSE event."""
    return {"event": "text_delta", "data": {"content": content}}


def yield_tool_start(name: str, arguments: dict, tool_id: str | None = None) -> dict:
    """Create a tool_start SSE event."""
    return {
        "event": "tool_start",
        "data": {
            "id": tool_id or str(uuid.uuid4()),
            "name": name,
            "arguments": arguments,
        },
    }


def yield_tool_result(name: str, result: dict, tool_id: str | None = None) -> dict:
    """Create a tool_result SSE event."""
    return {
        "event": "tool_result",
        "data": {
            "id": tool_id or str(uuid.uuid4()),
            "name": name,
            "result": result,
        },
    }


def yield_tool_error(name: str, error: str, tool_id: str | None = None) -> dict:
    """Create a tool_error SSE event."""
    return {
        "event": "tool_error",
        "data": {
            "id": tool_id or str(uuid.uuid4()),
            "name": name,
            "error": error,
        },
    }


def yield_done(full_text: str) -> dict:
    """Create a done SSE event."""
    return {"event": "done", "data": {"content": full_text}}


def yield_error(message: str) -> dict:
    """Create an error SSE event."""
    return {"event": "error", "data": {"message": message}}


def execute_tool_with_events(ctx, name: str, arguments: dict):
    """Execute a tool and yield tool_start/tool_result/tool_error events.

    Also flushes any pending events (e.g. search_result_added) emitted
    by the tool's event_callback.

    Args:
        ctx: RequestContext with tools and pending_events.
        name: Tool name to execute.
        arguments: Tool arguments dict.

    Returns:
        (result_dict, list_of_sse_events)
    """
    tool_id = str(uuid.uuid4())
    events = [yield_tool_start(name, arguments, tool_id)]

    result = ctx.tools.execute(name, arguments)

    # Flush pending events from tool callbacks
    events.extend(ctx.tools.flush_pending())

    if "error" in result:
        events.append(yield_tool_error(name, result["error"], tool_id))
    else:
        events.append(yield_tool_result(name, result, tool_id))

    return result, events
