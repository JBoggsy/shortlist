"""read_resume tool — read the user's uploaded resume."""

from ._registry import agent_tool


class ResumeMixin:
    @agent_tool(
        description="Read the user's uploaded resume.",
    )
    def read_resume(self):
        return {"error": "read_resume not implemented"}
