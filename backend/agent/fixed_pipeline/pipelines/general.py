"""General pipeline — career advice, app help, open-ended questions.

This is the fallback pipeline for requests that don't fit specific categories.
"""

import json
import logging

from ..micro_agents import AdvisorAgent
from ..pipeline_base import Pipeline
from ..prompts import ADVISOR_PROMPT
from ..schemas import GeneralParams

logger = logging.getLogger(__name__)


class GeneralPipeline(Pipeline):
    params_schema = GeneralParams

    def execute(self):
        p = self.params
        logger.info("[GeneralPipeline] question=%s, needs_job_context=%s",
                    (p.question or "")[:100], p.needs_job_context)

        # Always load profile for general advice
        profile = self.ctx.ensure_profile()
        resume_summary = self.ctx.get_resume_summary()

        job_context = ""
        if p.needs_job_context:
            jobs = self.ctx.ensure_jobs()
            if jobs:
                job_context = "<tracked_jobs>\n" + json.dumps(jobs[:10], indent=2) + "\n</tracked_jobs>"

        system_prompt = ADVISOR_PROMPT.format(
            profile=profile,
            resume_summary=resume_summary,
            job_context=job_context,
        )

        # Build user message from the question + conversation history
        user_message = p.question
        if not user_message:
            for msg in reversed(self.ctx.conversation_history):
                if msg["role"] == "user":
                    user_message = msg["content"]
                    break

        if not user_message:
            user_message = "Hello! How can I help with my job search?"

        # Include recent conversation history for context
        history_context = ""
        if self.ctx.conversation_history:
            recent = self.ctx.conversation_history[-6:]
            history_parts = []
            for msg in recent[:-1]:
                role = msg["role"].upper()
                content = msg["content"][:300]
                history_parts.append(f"[{role}]: {content}")
            if history_parts:
                history_context = "Recent conversation:\n" + "\n".join(history_parts) + "\n\n"

        full_user_msg = history_context + user_message

        advisor = AdvisorAgent(self.model)
        for chunk in advisor.run(system_prompt, full_user_msg):
            yield self.text(chunk)


def run(model, params, ctx):
    yield from GeneralPipeline(model, params, ctx).execute()
