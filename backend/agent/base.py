"""Abstract base classes defining the agent interfaces.

These ABCs specify the contracts that agent implementations must satisfy.
The rest of the application imports and calls agents via these interfaces.

Consumers:
    - backend/routes/chat.py imports Agent, OnboardingAgent
    - backend/routes/resume.py imports ResumeParser
"""

from abc import ABC, abstractmethod
from collections.abc import Generator

from langchain_core.language_models import BaseChatModel


class Agent(ABC):
    """Main chat agent.

    Constructor args (expected by routes):
        model:            LLM model instance
        search_api_key:   Tavily API key for web search
        adzuna_app_id:    Adzuna application ID
        adzuna_app_key:   Adzuna application key
        adzuna_country:   Adzuna country code (default "us")
        jsearch_api_key:  RapidAPI key for JSearch
        conversation_id:  Current conversation ID (for DB writes)

    Subclasses must implement run().
    """

    @abstractmethod
    def __init__(
        self,
        model: BaseChatModel,
        search_api_key: str = "",
        adzuna_app_id: str = "",
        adzuna_app_key: str = "",
        adzuna_country: str = "us",
        jsearch_api_key: str = "",
        conversation_id: int | None = None,
    ):
        ...

    @abstractmethod
    def run(self, messages: list[dict]) -> Generator[dict, None, None]:
        """Run the agent loop, yielding SSE event dicts.

        Args:
            messages: List of {"role": "user"|"assistant", "content": str}

        Yields SSE event dicts:
            {"event": "text_delta",          "data": {"content": str}}
            {"event": "tool_start",          "data": {"id": str, "name": str, "arguments": dict}}
            {"event": "tool_result",         "data": {"id": str, "name": str, "result": dict}}
            {"event": "tool_error",          "data": {"id": str, "name": str, "error": str}}
            {"event": "done",                "data": {"content": str}}   # full accumulated text
            {"event": "error",               "data": {"message": str}}   # fatal error
            {"event": "search_result_added", "data": {SearchResult dict}}  # from add_search_result tool
        """
        ...


class OnboardingAgent(ABC):
    """Onboarding interview agent.

    Constructor args (expected by routes):
        model: LLM model instance

    Subclasses must implement run().
    """

    @abstractmethod
    def __init__(self, model: BaseChatModel):
        ...

    @abstractmethod
    def run(self, messages: list[dict]) -> Generator[dict, None, None]:
        """Run the onboarding agent, yielding SSE event dicts.

        Same SSE protocol as Agent.run(), plus:
            {"event": "onboarding_complete", "data": {}}
        when the onboarding interview is finished.
        """
        ...


class ResumeParser(ABC):
    """Resume parsing agent (non-streaming).

    Constructor args (expected by routes):
        model: LLM model instance

    Subclasses must implement parse().
    """

    @abstractmethod
    def __init__(self, model: BaseChatModel):
        ...

    @abstractmethod
    def parse(self, raw_text: str) -> dict:
        """Parse raw resume text into structured JSON.

        Args:
            raw_text: Raw text extracted from a PDF/DOCX resume.

        Returns:
            Structured resume data as a JSON-serializable dict.

        Raises:
            RuntimeError: If parsing fails.
        """
        ...
