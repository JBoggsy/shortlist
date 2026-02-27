"""run_job_search tool — launch the job search sub-agent."""

from typing import Optional

from pydantic import BaseModel, Field

from ._registry import agent_tool


class RunJobSearchInput(BaseModel):
    query: str = Field(description="Job search description")
    location: Optional[str] = Field(default=None, description="Target location")
    remote_only: Optional[bool] = Field(default=None, description="Remote only")
    salary_min: Optional[int] = Field(default=None, description="Minimum salary")
    salary_max: Optional[int] = Field(default=None, description="Maximum salary")


class RunJobSearchMixin:
    @agent_tool(
        description=(
            "Launch the job search sub-agent to find real job listings, "
            "score them against the user profile, and stream results into "
            "the search results panel."
        ),
        args_schema=RunJobSearchInput,
    )
    def run_job_search(self, query, location=None, remote_only=None,
                       salary_min=None, salary_max=None):
        return {"error": "run_job_search not implemented"}
