"""Prepare pipeline — interview prep, cover letters, resume tailoring, question prep."""

import json
import logging

from ..entity_resolution import resolve_job_ref_or_fail
from ..micro_agents import (
    CoverLetterAgent,
    InterviewPrepAgent,
    QuestionGeneratorAgent,
    ResumeTailorAgent,
)
from ..pipeline_base import Pipeline
from ..prompts import (
    COVER_LETTER_PROMPT,
    INTERVIEW_PREP_PROMPT,
    QUESTION_GENERATOR_PROMPT,
    RESUME_TAILOR_PROMPT,
)
from ..schemas import PrepareParams

logger = logging.getLogger(__name__)

# Map prep types to their agent + prompt
_PREP_MAP = {
    "interview": (InterviewPrepAgent, INTERVIEW_PREP_PROMPT),
    "cover_letter": (CoverLetterAgent, COVER_LETTER_PROMPT),
    "resume_tailor": (ResumeTailorAgent, RESUME_TAILOR_PROMPT),
    "questions": (QuestionGeneratorAgent, QUESTION_GENERATOR_PROMPT),
    "general": (InterviewPrepAgent, INTERVIEW_PREP_PROMPT),
}


class PreparePipeline(Pipeline):
    params_schema = PrepareParams

    def execute(self):
        p = self.params
        logger.info("[PreparePipeline] prep_type=%s, job_ref=%s, job_id=%s",
                    p.prep_type, p.job_ref, p.job_id)

        # Resolve job reference
        job = None
        if p.job_ref or p.job_id:
            job, error = resolve_job_ref_or_fail(p.job_ref, p.job_id, self.ctx.tools)
            if error:
                yield self.text(error)
                return

        # Gather context
        profile = self.ctx.ensure_profile()
        resume_data = self.ctx.ensure_resume()
        resume_summary = self.ctx.get_resume_summary()

        job_text = json.dumps(job, indent=2) if job else "(no specific job selected)"

        # Format resume for resume_tailor (needs full resume, not just summary)
        resume_text = resume_summary
        if p.prep_type == "resume_tailor" and resume_data:
            parsed = resume_data.get("parsed")
            if parsed:
                resume_text = json.dumps(parsed, indent=2)
            elif resume_data.get("text"):
                resume_text = resume_data["text"][:4000]

        specifics = f"Additional context from the user: {p.specifics}" if p.specifics else ""

        # Select agent and prompt
        agent_class, prompt_template = _PREP_MAP.get(p.prep_type, _PREP_MAP["general"])

        if p.prep_type == "resume_tailor":
            system_prompt = prompt_template.format(
                job=job_text, profile=profile, resume=resume_text, specifics=specifics,
            )
        else:
            system_prompt = prompt_template.format(
                job=job_text, profile=profile, resume_summary=resume_summary, specifics=specifics,
            )

        if job:
            company = job.get("company", "?")
            title = job.get("title", "?")
            user_msg = f"Prepare {p.prep_type} content for {title} at {company}."
        else:
            user_msg = f"Prepare {p.prep_type} content for a job search."

        agent = agent_class(self.model)
        for chunk in agent.run(system_prompt, user_msg):
            yield self.text(chunk)


def run(model, params, ctx):
    yield from PreparePipeline(model, params, ctx).execute()
