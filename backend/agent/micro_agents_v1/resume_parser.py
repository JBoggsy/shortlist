"""Micro agents v1 resume parser — pipeline-based.

Pipeline stages:
  1. SectionSegmenter  — classify raw text into typed sections  (1 LLM call)
  2. Three parallel extractors                                  (3 LLM calls)
     a. ContactExtractor          — contact info + summary
     b. ExperienceEducationExtractor — work, education, projects
     c. SkillsExtractor           — skills, certs, pubs, languages
  3. ResumeAssembler   — merge, deduplicate, gap-fill           (+ 1 LLM call
                         if skills section was empty)
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

import dspy

from backend.agent.base import ResumeParser
from backend.llm.llm_factory import LLMConfig

from .resume_stages import ResumeAssembler, SectionSegmenter, SectionType
from .resume_stages.contact_extractor import (
    ContactExtractor,
    ContactInfo,
    ContactSummaryOutput,
)
from .resume_stages.experience_extractor import (
    ExperienceEducationExtractor,
    ExperienceEducationOutput,
)
from .resume_stages.skills_extractor import (
    SkillsCredentialsOutput,
    SkillsExtractor,
    SkillsInfo,
)

logger = logging.getLogger(__name__)

# Which section types feed into which extractor
_CONTACT_TYPES = {SectionType.CONTACT, SectionType.SUMMARY}
_EXPERIENCE_TYPES = {
    SectionType.EXPERIENCE,
    SectionType.EDUCATION,
    SectionType.PROJECTS,
    SectionType.VOLUNTEER,
}
_SKILLS_TYPES = {
    SectionType.SKILLS,
    SectionType.CERTIFICATIONS,
    SectionType.PUBLICATIONS,
    SectionType.LANGUAGES,
}


class MicroAgentsV1ResumeParser(ResumeParser):
    """Pipeline resume parser using DSPy modules."""

    def __init__(self, llm_config: LLMConfig):
        dspy.Module.__init__(self)
        self.llm_config = llm_config

        # Store sub-modules as attributes for DSPy discovery
        self.segmenter = SectionSegmenter(llm_config)
        self.contact_extractor = ContactExtractor(llm_config)
        self.experience_extractor = ExperienceEducationExtractor(llm_config)
        self.skills_extractor = SkillsExtractor(llm_config)
        self.assembler = ResumeAssembler(llm_config=llm_config)

    def parse(self, raw_text: str) -> dict:
        # --- Stage 1: Segment raw text into classified sections ---
        logger.info("Resume parser: Stage 1 — segmenting sections")
        sections = self.segmenter.segment(raw_text)

        # Group section content by extractor
        contact_text = self._collect_text(sections, _CONTACT_TYPES)
        experience_text = self._collect_text(sections, _EXPERIENCE_TYPES)
        skills_text = self._collect_text(sections, _SKILLS_TYPES)

        # Collect "other" sections — append to whichever group seems most
        # relevant, or to experience as a fallback
        other_text = self._collect_text(sections, {SectionType.OTHER})
        if other_text:
            experience_text = (experience_text + "\n\n" + other_text).strip()

        # --- Stage 2: Run the three extractors in parallel ---
        logger.info("Resume parser: Stage 2 — running extractors in parallel")
        contact_out, experience_out, skills_out = self._run_extractors(
            contact_text, experience_text, skills_text
        )

        # --- Stage 3: Assemble final dict ---
        logger.info("Resume parser: Stage 3 — assembling final output")
        result = self.assembler.assemble(contact_out, experience_out, skills_out)

        logger.info("Resume parser: complete — %d top-level keys", len(result))
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _collect_text(sections, types) -> str:
        """Join content of all sections matching the given types."""
        parts = [s.content for s in sections if s.section_type in types]
        return "\n\n".join(parts)

    def _run_extractors(
        self,
        contact_text: str,
        experience_text: str,
        skills_text: str,
    ) -> tuple[ContactSummaryOutput, ExperienceEducationOutput, SkillsCredentialsOutput]:
        """Run the three Stage-2 extractors in parallel using threads."""
        results: dict[str, object] = {}

        with ThreadPoolExecutor(max_workers=3) as pool:
            futures = {
                pool.submit(self.contact_extractor.extract, contact_text): "contact",
                pool.submit(self.experience_extractor.extract, experience_text): "experience",
                pool.submit(self.skills_extractor.extract, skills_text): "skills",
            }
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result()
                except Exception:
                    logger.exception(
                        "Extractor '%s' failed — using empty fallback", name,
                    )

        contact_out: ContactSummaryOutput = results.get(
            "contact", ContactSummaryOutput(contact=ContactInfo()),
        )
        experience_out: ExperienceEducationOutput = results.get(
            "experience", ExperienceEducationOutput(),
        )
        skills_out: SkillsCredentialsOutput = results.get(
            "skills", SkillsCredentialsOutput(skills=SkillsInfo()),
        )
        return contact_out, experience_out, skills_out
