"""job_search tool — job board API search (JSearch/Adzuna)."""

from typing import Optional

from pydantic import BaseModel, Field

from ._registry import agent_tool


class JobSearchInput(BaseModel):
    query: str = Field(description="Job search keywords")
    location: Optional[str] = Field(default=None, description="Location filter")
    remote_only: Optional[bool] = Field(default=None, description="Remote jobs only")
    salary_min: Optional[int] = Field(default=None, description="Minimum salary")
    salary_max: Optional[int] = Field(default=None, description="Maximum salary")
    num_results: int = Field(default=10, description="Number of results (max 20)")
    provider: Optional[str] = Field(default=None, description="Force provider (adzuna/jsearch)")


class JobSearchMixin:
    @agent_tool(
        description="Search job board APIs for real job listings.",
        args_schema=JobSearchInput,
    )
    def job_search(self, query, location=None, remote_only=False,
                   salary_min=None, salary_max=None, num_results=10,
                   provider=None):
        return {"error": "job_search not implemented"}
