"""Job tracker tools — create_job and list_jobs."""

from typing import Optional

from pydantic import BaseModel, Field

from ._registry import agent_tool


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


class JobsMixin:
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
