"""web_search tool — Tavily web search."""

from pydantic import BaseModel, Field

from ._registry import agent_tool


class WebSearchInput(BaseModel):
    query: str = Field(description="Search query")
    num_results: int = Field(default=5, description="Number of results (max 10)")


class WebSearchMixin:
    @agent_tool(
        description="Search the web using Tavily.",
        args_schema=WebSearchInput,
    )
    def web_search(self, query, num_results=5):
        return {"error": "web_search not implemented"}
