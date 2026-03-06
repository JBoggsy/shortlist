"""DefaultResumeParser — single-shot LLM call to parse resume text into JSON."""

import json
import logging

import litellm

from backend.agent.base import ResumeParser
from backend.llm.llm_factory import LLMConfig

from .prompts import RESUME_PARSE_PROMPT

logger = logging.getLogger(__name__)


class DefaultResumeParser(ResumeParser):
    """Resume parser — single LLM invocation, no tools."""

    def __init__(self, llm_config: LLMConfig):
        self.llm_config = llm_config

    def parse(self, raw_text: str) -> dict:
        prompt = RESUME_PARSE_PROMPT.format(raw_text=raw_text)

        kwargs = {
            "model": self.llm_config.model,
            "max_tokens": self.llm_config.max_tokens,
        }
        if self.llm_config.api_key:
            kwargs["api_key"] = self.llm_config.api_key
        if self.llm_config.api_base:
            kwargs["api_base"] = self.llm_config.api_base

        try:
            response = litellm.completion(
                messages=[
                    {"role": "system", "content": "You are a precise resume parser. Return only valid JSON."},
                    {"role": "user", "content": prompt},
                ],
                **kwargs,
            )
        except Exception as exc:
            logger.exception("LLM call failed during resume parsing")
            raise RuntimeError(f"LLM call failed: {exc}") from exc

        content = response.choices[0].message.content.strip()

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
