"""DefaultResumeParser — single-shot LLM call to parse resume text into JSON."""

import json
import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from backend.agent.base import ResumeParser

from .prompts import RESUME_PARSE_PROMPT

logger = logging.getLogger(__name__)


class DefaultResumeParser(ResumeParser):
    """Resume parser — single LLM invocation, no tools."""

    def __init__(self, model: BaseChatModel):
        self.model = model

    def parse(self, raw_text: str) -> dict:
        prompt = RESUME_PARSE_PROMPT.format(raw_text=raw_text)

        try:
            response = self.model.invoke([
                SystemMessage(content="You are a precise resume parser. Return only valid JSON."),
                HumanMessage(content=prompt),
            ])
        except Exception as exc:
            logger.exception("LLM call failed during resume parsing")
            raise RuntimeError(f"LLM call failed: {exc}") from exc

        content = response.content.strip()

        # Strip markdown code fences if present
        if content.startswith("```"):
            # Remove opening fence (with optional language tag)
            first_newline = content.index("\n") if "\n" in content else 3
            content = content[first_newline + 1:]
            # Remove closing fence
            if content.endswith("```"):
                content = content[:-3].strip()

        try:
            parsed = json.loads(content)
        except json.JSONDecodeError as exc:
            logger.error("Failed to parse LLM response as JSON: %s", content[:200])
            raise RuntimeError(
                "LLM returned invalid JSON. Please try again."
            ) from exc

        logger.info("Resume parsed successfully — keys: %s", list(parsed.keys()))
        return parsed
