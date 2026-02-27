"""scrape_url tool — fetch and return plain text from a web page."""

from pydantic import BaseModel, Field

from ._registry import agent_tool


class ScrapeUrlInput(BaseModel):
    url: str = Field(description="The URL to scrape")


class ScrapeUrlMixin:
    @agent_tool(
        description="Scrape a web page and return its text content.",
        args_schema=ScrapeUrlInput,
    )
    def scrape_url(self, url):
        return {"error": "scrape_url not implemented"}
