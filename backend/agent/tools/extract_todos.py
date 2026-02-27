"""extract_application_todos tool — LLM-extract application steps from a job posting."""

from pydantic import BaseModel, Field

from ._registry import agent_tool


class ExtractApplicationTodosInput(BaseModel):
    job_id: int = Field(description="Job ID to extract todos for")


class ExtractTodosMixin:
    @agent_tool(
        description=(
            "Extract application todos (required documents, questions, "
            "assessments, references) from a job posting URL and save them "
            "to the job's todo list."
        ),
        args_schema=ExtractApplicationTodosInput,
    )
    def extract_application_todos(self, job_id):
        return {"error": "extract_application_todos not implemented"}
