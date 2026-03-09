"""Abstract base classes defining the agent interfaces.

These ABCs specify the contracts that agent implementations must satisfy.
The rest of the application imports and calls agents via these interfaces.

Consumers:
    - backend/routes/chat.py imports Agent, OnboardingAgent
    - backend/routes/resume.py imports ResumeParser
"""

from abc import ABC, ABCMeta, abstractmethod
from collections.abc import Generator

import dspy

from backend.llm.llm_factory import LLMConfig


class _AgentModuleMeta(ABCMeta, type(dspy.Module)):
    """Metaclass combining ABCMeta and DSPy's ProgramMeta.

    Allows agent base classes to be both ABCs (with abstract method
    enforcement) and DSPy Modules (with sub-module discovery,
    named_parameters, save/load).
    """
    pass


class Agent(ABC, dspy.Module, metaclass=_AgentModuleMeta):
    """Main chat agent.

    Constructor args (expected by routes):
        llm_config:       LLMConfig instance
        search_api_key:   Tavily API key for web search
        rapidapi_key:     RapidAPI key (for JSearch, Active Jobs DB, LinkedIn Jobs)
        conversation_id:  Current conversation ID (for DB writes)

    Subclasses must implement run().
    """

    @abstractmethod
    def __init__(
        self,
        llm_config: LLMConfig,
        search_api_key: str = "",
        rapidapi_key: str = "",
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


class OnboardingAgent(ABC, dspy.Module, metaclass=_AgentModuleMeta):
    """Onboarding interview agent.

    Constructor args (expected by routes):
        llm_config: LLMConfig instance

    Subclasses must implement run().
    """

    @abstractmethod
    def __init__(self, llm_config: LLMConfig):
        ...

    @abstractmethod
    def run(self, messages: list[dict]) -> Generator[dict, None, None]:
        """Run the onboarding agent, yielding SSE event dicts.

        Same SSE protocol as Agent.run(), plus:
            {"event": "onboarding_complete", "data": {}}
        when the onboarding interview is finished.
        """
        ...


class ResumeParser(ABC, dspy.Module, metaclass=_AgentModuleMeta):
    """Resume parsing agent (non-streaming).

    Constructor args (expected by routes):
        llm_config: LLMConfig instance

    Subclasses must implement parse().
    """

    @abstractmethod
    def __init__(self, llm_config: LLMConfig):
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
