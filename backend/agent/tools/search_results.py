"""Search result tools — add_search_result and list_search_results."""

from typing import Optional

from pydantic import BaseModel, Field

from ._registry import agent_tool


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


class ListSearchResultsInput(BaseModel):
    min_fit: Optional[int] = Field(default=None, description="Minimum fit rating 0-5")


class SearchResultsMixin:
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
        description="List job search results from the current conversation.",
        args_schema=ListSearchResultsInput,
    )
    def list_search_results(self, min_fit=None):
        return {"error": "list_search_results not implemented"}
