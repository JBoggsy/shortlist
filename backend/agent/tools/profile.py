"""User profile tools — read_user_profile and update_user_profile."""

from pydantic import BaseModel, Field

from ._registry import agent_tool


class UpdateUserProfileInput(BaseModel):
    content: str = Field(description="Full updated markdown profile content")


class ProfileMixin:
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
