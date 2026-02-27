"""Agent tools — stubs preserving the public interface.

The AgentTools class provides tool implementations that agents invoke
during their run loops. Each tool is a method decorated with @agent_tool.

Consumers:
    - Agent implementations create AgentTools and call .execute()

The @agent_tool decorator and _TOOL_REGISTRY track registered tools.
Agent implementations are responsible for adapting these tools to their
specific LLM framework.
"""

import logging
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tool registration decorator
# ---------------------------------------------------------------------------

_TOOL_REGISTRY: list[str] = []


def agent_tool(description: str, args_schema=None):
    """Mark a method as an agent tool with an LLM-facing description."""

    def decorator(method):
        method._tool_description = description
        method._tool_args_schema = args_schema
        _TOOL_REGISTRY.append(method.__name__)
        return method

    return decorator


# ---------------------------------------------------------------------------
# Pydantic input schemas
# ---------------------------------------------------------------------------


class WebSearchInput(BaseModel):
    query: str = Field(description="Search query")
    num_results: int = Field(default=5, description="Number of results (max 10)")


class JobSearchInput(BaseModel):
    query: str = Field(description="Job search keywords")
    location: Optional[str] = Field(default=None, description="Location filter")
    remote_only: Optional[bool] = Field(default=None, description="Remote jobs only")
    salary_min: Optional[int] = Field(default=None, description="Minimum salary")
    salary_max: Optional[int] = Field(default=None, description="Maximum salary")
    num_results: int = Field(default=10, description="Number of results (max 20)")
    provider: Optional[str] = Field(default=None, description="Force provider (adzuna/jsearch)")


class ScrapeUrlInput(BaseModel):
    url: str = Field(description="The URL to scrape")


class CreateJobInput(BaseModel):
    company: str = Field(description="Company name")
    title: str = Field(description="Job title")
    url: Optional[str] = Field(default=None, description="Job posting URL")
    status: Optional[str] = Field(default=None, description="Application status")
    notes: Optional[str] = Field(default=None, description="Notes")
    salary_min: Optional[int] = Field(default=None, description="Minimum salary")
    salary_max: Optional[int] = Field(default=None, description="Maximum salary")
    location: Optional[str] = Field(default=None, description="Job location")
    remote_type: Optional[str] = Field(default=None, description="Remote type")
    tags: Optional[str] = Field(default=None, description="Comma-separated tags")
    contact_name: Optional[str] = Field(default=None, description="Contact name")
    contact_email: Optional[str] = Field(default=None, description="Contact email")
    source: Optional[str] = Field(default=None, description="Job source")
    requirements: Optional[str] = Field(default=None, description="Requirements (newline-separated)")
    nice_to_haves: Optional[str] = Field(default=None, description="Nice-to-haves (newline-separated)")
    job_fit: Optional[int] = Field(default=None, description="Job fit rating 0-5")


class ListJobsInput(BaseModel):
    status: Optional[str] = Field(default=None, description="Filter by status")
    company: Optional[str] = Field(default=None, description="Filter by company")
    title: Optional[str] = Field(default=None, description="Filter by title")
    url: Optional[str] = Field(default=None, description="Filter by URL")
    limit: int = Field(default=20, description="Max results")


class RunJobSearchInput(BaseModel):
    query: str = Field(description="Job search description")
    location: Optional[str] = Field(default=None, description="Target location")
    remote_only: Optional[bool] = Field(default=None, description="Remote only")
    salary_min: Optional[int] = Field(default=None, description="Minimum salary")
    salary_max: Optional[int] = Field(default=None, description="Maximum salary")


class ListSearchResultsInput(BaseModel):
    min_fit: Optional[int] = Field(default=None, description="Minimum fit rating 0-5")


class UpdateUserProfileInput(BaseModel):
    content: str = Field(description="Full updated markdown profile content")


class AddSearchResultInput(BaseModel):
    company: str = Field(description="Company name")
    title: str = Field(description="Job title")
    job_fit: int = Field(description="Job fit rating 0-5 based on user profile match")
    url: Optional[str] = Field(default=None, description="Job posting URL")
    salary_min: Optional[int] = Field(default=None, description="Minimum salary")
    salary_max: Optional[int] = Field(default=None, description="Maximum salary")
    location: Optional[str] = Field(default=None, description="Job location")
    remote_type: Optional[str] = Field(default=None, description="Remote type: remote, hybrid, or onsite")
    source: Optional[str] = Field(default=None, description="Where the job was found (jsearch, adzuna, web)")
    description: Optional[str] = Field(default=None, description="Brief job description summary")
    requirements: Optional[str] = Field(default=None, description="Key requirements, newline-separated")
    nice_to_haves: Optional[str] = Field(default=None, description="Nice-to-have qualifications, newline-separated")
    fit_reason: Optional[str] = Field(default=None, description="Brief explanation of the fit rating")


class ExtractApplicationTodosInput(BaseModel):
    job_id: int = Field(description="Job ID to extract todos for")


# ---------------------------------------------------------------------------
# AgentTools
# ---------------------------------------------------------------------------


class AgentTools:
    """Collection of tools available to agents.

    Constructor args:
        search_api_key:    Tavily API key
        adzuna_app_id:     Adzuna app ID
        adzuna_app_key:    Adzuna app key
        adzuna_country:    Adzuna country code (default "us")
        jsearch_api_key:   RapidAPI JSearch key
        conversation_id:   Current conversation ID
        event_callback:    Callable for sub-agent SSE events
        search_model:      Optional cheaper LLM for sub-agent
        enrichment_model:  Optional LLM for job enrichment

    Key methods:
        execute(tool_name, arguments) -> dict
            Dispatch a tool call by name. Returns result dict or {"error": str}.
        get_tool_definitions() -> list[dict]
            Return tool metadata (name, description, args_schema) for all
            registered tools. Agent implementations use this to adapt tools
            to their specific LLM framework.
    """

    def __init__(self, search_api_key="", adzuna_app_id="", adzuna_app_key="",
                 adzuna_country="us", jsearch_api_key="",
                 conversation_id=None, event_callback=None,
                 search_model=None, enrichment_model=None):
        self.search_api_key = search_api_key
        self.adzuna_app_id = adzuna_app_id
        self.adzuna_app_key = adzuna_app_key
        self.adzuna_country = adzuna_country
        self.jsearch_api_key = jsearch_api_key
        self.conversation_id = conversation_id
        self.event_callback = event_callback
        self.search_model = search_model
        self.enrichment_model = enrichment_model

    def execute(self, tool_name, arguments):
        """Execute a tool by name with error handling."""
        method = getattr(self, tool_name, None)
        if method is None or not hasattr(method, "_tool_description"):
            return {"error": f"Unknown tool: {tool_name}"}
        try:
            return method(**arguments)
        except Exception as e:
            logger.exception("Tool %s raised an exception", tool_name)
            return {"error": str(e)}

    def get_tool_definitions(self):
        """Return metadata for all registered tools.

        Returns a list of dicts, each with:
            - name: str — tool method name
            - description: str — LLM-facing description
            - args_schema: Pydantic BaseModel class or None

        Agent implementations use this to adapt tools to their specific
        LLM framework (e.g. LangChain StructuredTool, OpenAI function
        calling, etc.).
        """
        definitions = []
        for name in _TOOL_REGISTRY:
            method = getattr(self, name, None)
            if method is None:
                continue
            definitions.append({
                "name": name,
                "description": getattr(method, "_tool_description", ""),
                "args_schema": getattr(method, "_tool_args_schema", None),
            })
        return definitions

    # -- Tool stubs --------------------------------------------------------
    # TODO: implement each tool body

    @agent_tool(
        description="Search the web using Tavily.",
        args_schema=WebSearchInput,
    )
    def web_search(self, query, num_results=5):
        return {"error": "web_search not implemented"}

    @agent_tool(
        description="Search job board APIs for real job listings.",
        args_schema=JobSearchInput,
    )
    def job_search(self, query, location=None, remote_only=False,
                   salary_min=None, salary_max=None, num_results=10,
                   provider=None):
        return {"error": "job_search not implemented"}

    @agent_tool(
        description="Scrape a web page and return its text content.",
        args_schema=ScrapeUrlInput,
    )
    def scrape_url(self, url):
        return {"error": "scrape_url not implemented"}

    @agent_tool(
        description="Add a new job application to the tracker.",
        args_schema=CreateJobInput,
    )
    def create_job(self, **kwargs):
        return {"error": "create_job not implemented"}

    @agent_tool(
        description="List and search jobs in the tracker database.",
        args_schema=ListJobsInput,
    )
    def list_jobs(self, limit=20, status=None, company=None, title=None, url=None):
        return {"error": "list_jobs not implemented"}

    @agent_tool(
        description="Read the user's profile document.",
    )
    def read_user_profile(self):
        return {"error": "read_user_profile not implemented"}

    @agent_tool(
        description="Update the user's profile document.",
        args_schema=UpdateUserProfileInput,
    )
    def update_user_profile(self, content):
        return {"error": "update_user_profile not implemented"}

    @agent_tool(
        description="Read the user's uploaded resume.",
    )
    def read_resume(self):
        return {"error": "read_resume not implemented"}

    @agent_tool(
        description="Launch a comprehensive job search using a sub-agent.",
        args_schema=RunJobSearchInput,
    )
    def run_job_search(self, query, location=None, remote_only=False,
                       salary_min=None, salary_max=None):
        return {"error": "run_job_search not implemented"}

    @agent_tool(
        description=(
            "Add a qualifying job to the search results panel. Only add jobs "
            "rated >=3/5 stars. Include structured data and a fit_reason."
        ),
        args_schema=AddSearchResultInput,
    )
    def add_search_result(self, company, title, job_fit, url=None,
                          salary_min=None, salary_max=None, location=None,
                          remote_type=None, source=None, description=None,
                          requirements=None, nice_to_haves=None,
                          fit_reason=None):
        return {"error": "add_search_result not implemented"}

    @agent_tool(
        description="Extract application todos from a job posting URL.",
        args_schema=ExtractApplicationTodosInput,
    )
    def extract_application_todos(self, job_id):
        return {"error": "extract_application_todos not implemented"}

    @agent_tool(
        description="List job search results from the current conversation.",
        args_schema=ListSearchResultsInput,
    )
    def list_search_results(self, min_fit=None):
        return {"error": "list_search_results not implemented"}
