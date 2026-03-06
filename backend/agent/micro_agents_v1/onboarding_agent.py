"""Micro agents v1 onboarding agent."""

from collections.abc import Generator

from backend.agent.base import OnboardingAgent
from backend.llm.llm_factory import LLMConfig


class MicroAgentsV1OnboardingAgent(OnboardingAgent):
    def __init__(self, llm_config: LLMConfig):
        self.llm_config = llm_config

    def run(self, messages: list[dict]) -> Generator[dict, None, None]:
        raise NotImplementedError
        yield  # make this a generator
