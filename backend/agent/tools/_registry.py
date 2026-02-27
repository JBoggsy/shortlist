"""Tool registration: agent_tool decorator and _TOOL_REGISTRY."""

_TOOL_REGISTRY: list[str] = []


def agent_tool(description: str, args_schema=None):
    """Mark a method as an agent tool with an LLM-facing description."""

    def decorator(method):
        method._tool_description = description
        method._tool_args_schema = args_schema
        _TOOL_REGISTRY.append(method.__name__)
        return method

    return decorator
