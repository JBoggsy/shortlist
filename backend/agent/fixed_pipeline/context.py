"""RequestContext — shared context loaded once per user request."""

from dataclasses import dataclass, field

from backend.agent.tools import AgentTools


@dataclass
class RequestContext:
    """Shared context loaded once per user request.

    Avoids redundant tool calls within a single pipeline execution
    by caching profile, resume, and job data.
    """
    tools: AgentTools
    profile: str | None = None
    resume: dict | None = None
    jobs: list[dict] | None = None
    conversation_history: list[dict] = field(default_factory=list)

    def ensure_profile(self) -> str:
        """Load the user profile if not already cached."""
        if self.profile is None:
            result = self.tools.execute("read_user_profile", {})
            self.profile = result.get("content", "")
        return self.profile

    def ensure_resume(self) -> dict | None:
        """Load the user resume if not already cached."""
        if self.resume is None:
            result = self.tools.execute("read_resume", {})
            if "error" in result:
                self.resume = {}
            else:
                self.resume = result
        return self.resume

    def ensure_jobs(self, **filters) -> list[dict]:
        """Load tracked jobs if not already cached."""
        if self.jobs is None:
            result = self.tools.execute("list_jobs", filters)
            self.jobs = result.get("jobs", [])
        return self.jobs

    def get_resume_summary(self) -> str:
        """Get a brief text summary of the resume for LLM prompts."""
        resume = self.ensure_resume()
        if not resume or "error" in resume:
            return "(no resume uploaded)"
        parsed = resume.get("parsed")
        if parsed:
            parts = []
            if parsed.get("name"):
                parts.append(f"Name: {parsed['name']}")
            if parsed.get("summary"):
                parts.append(f"Summary: {parsed['summary']}")
            if parsed.get("skills"):
                parts.append(f"Skills: {', '.join(parsed['skills'][:20])}")
            if parsed.get("experience"):
                for exp in parsed["experience"][:3]:
                    parts.append(f"- {exp.get('title', '?')} at {exp.get('company', '?')}")
            return "\n".join(parts)
        text = resume.get("text", "")
        if text:
            return text[:2000]
        return "(no resume data)"
