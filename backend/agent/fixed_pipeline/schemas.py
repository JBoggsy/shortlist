"""Pydantic schemas for routing, pipeline params, and micro-agent outputs."""

from typing import Literal

from pydantic import BaseModel, Field


# ── Routing ─────────────────────────────────────────────────────────────

REQUEST_TYPES = Literal[
    "find_jobs", "research_url", "track_crud", "query_jobs",
    "todo_mgmt", "profile_mgmt", "prepare", "compare",
    "research", "general", "multi_step",
]


class RoutingResult(BaseModel):
    """Structured output from the Routing Agent."""
    request_type: REQUEST_TYPES
    params: dict = Field(default_factory=dict)
    entity_refs: list[str] = Field(default_factory=list)
    acknowledgment: str = ""


# ── Pipeline param schemas ──────────────────────────────────────────────

class FindJobsParams(BaseModel):
    query: str = ""
    location: str | None = None
    remote_type: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    company_type: str | None = None
    employment_type: str | None = None
    date_posted: str | None = None
    num_results: int = 10


class ResearchUrlParams(BaseModel):
    url: str = ""
    intent: str = "analyze"


class TrackCrudParams(BaseModel):
    action: Literal["create", "edit", "delete"] = "create"
    job_ref: str | None = None
    job_id: int | None = None
    fields: dict = Field(default_factory=dict)


class QueryJobsParams(BaseModel):
    filters: dict = Field(default_factory=dict)
    question: str | None = None
    format: Literal["list", "summary", "count"] = "list"


class TodoMgmtParams(BaseModel):
    action: Literal["list", "toggle", "create", "generate", "delete"] = "list"
    job_ref: str | None = None
    job_id: int | None = None
    todo_id: int | None = None
    todo_data: dict = Field(default_factory=dict)


class ProfileMgmtParams(BaseModel):
    action: Literal["read", "update"] = "read"
    section: str | None = None
    content: str | None = None
    natural_update: str | None = None


class PrepareParams(BaseModel):
    prep_type: Literal["interview", "cover_letter", "resume_tailor", "questions", "general"] = "general"
    job_ref: str | None = None
    job_id: int | None = None
    specifics: str | None = None


class CompareParams(BaseModel):
    job_refs: list[str] = Field(default_factory=list)
    job_ids: list[int] = Field(default_factory=list)
    dimensions: list[str] = Field(default_factory=list)
    mode: Literal["compare", "rank", "pros_cons"] = "compare"


class ResearchParams(BaseModel):
    topic: str = ""
    research_type: Literal["company", "salary", "interview_process", "industry", "general"] = "general"
    company: str | None = None
    role: str | None = None


class GeneralParams(BaseModel):
    question: str = ""
    needs_job_context: bool = False
    needs_profile: bool = False
    job_ref: str | None = None


class MultiStepParams(BaseModel):
    steps: list[dict] = Field(default_factory=list)


# ── Micro-agent output schemas ──────────────────────────────────────────

class EvaluatedJob(BaseModel):
    """A job result with a fit evaluation."""
    index: int = 0
    job_fit: int = Field(ge=0, le=5)
    fit_reason: str = ""


class JobEvaluationResult(BaseModel):
    """Output from the Evaluator micro-agent."""
    evaluations: list[EvaluatedJob] = Field(default_factory=list)


class JobSearchQuery(BaseModel):
    """A single optimized job search query."""
    query: str
    location: str | None = None
    remote_only: bool = False


class QueryGeneratorResult(BaseModel):
    """Output from the Query Generator micro-agent."""
    queries: list[JobSearchQuery] = Field(default_factory=list)


class JobDetails(BaseModel):
    """Structured job details extracted from raw data."""
    company: str = ""
    title: str = ""
    url: str | None = None
    salary_min: int | None = None
    salary_max: int | None = None
    location: str | None = None
    remote_type: str | None = None
    description: str | None = None
    requirements: str | None = None
    nice_to_haves: str | None = None
    source: str | None = None


class FitEvaluation(BaseModel):
    """Output from the Fit Evaluator micro-agent."""
    job_fit: int = Field(ge=0, le=5)
    fit_reason: str = ""
    strengths: list[str] = Field(default_factory=list)
    gaps: list[str] = Field(default_factory=list)


class ProfileSectionUpdate(BaseModel):
    """A single profile section update."""
    section: str
    content: str


class ProfileUpdateResult(BaseModel):
    """Output from the Profile Update micro-agent."""
    updates: list[ProfileSectionUpdate] = Field(default_factory=list)


class TodoItem(BaseModel):
    """A generated todo item."""
    title: str
    category: str = "other"
    description: str = ""


class TodoGeneratorResult(BaseModel):
    """Output from the Todo Generator micro-agent."""
    todos: list[TodoItem] = Field(default_factory=list)


class SearchQueryList(BaseModel):
    """Output from Query Generator for research queries."""
    queries: list[str] = Field(default_factory=list)
