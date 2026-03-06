"""Micro agents v1 resume parser."""

from backend.agent.base import ResumeParser
from backend.llm.llm_factory import LLMConfig


class MicroAgentsV1ResumeParser(ResumeParser):
    def __init__(self, llm_config: LLMConfig):
        self.llm_config = llm_config

    def parse(self, raw_text: str) -> dict:
        raise NotImplementedError
