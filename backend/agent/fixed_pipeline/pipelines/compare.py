"""Compare pipeline — compare or rank multiple jobs."""

import json
import logging

from ..entity_resolution import resolve_job_ref
from ..micro_agents import AnalysisAgent, ComparisonAgent, RankingAgent
from ..pipeline_base import Pipeline
from ..prompts import ANALYSIS_PROMPT, COMPARISON_PROMPT, RANKING_PROMPT
from ..schemas import CompareParams

logger = logging.getLogger(__name__)


class ComparePipeline(Pipeline):
    params_schema = CompareParams

    def execute(self):
        p = self.params
        logger.info("[ComparePipeline] mode=%s, job_ids=%s, job_refs=%s",
                    p.mode, p.job_ids, p.job_refs)

        # Resolve all job references
        resolved_jobs = []

        if p.job_ids:
            all_jobs = self.ctx.ensure_jobs()
            for jid in p.job_ids:
                for job in all_jobs:
                    if job.get("id") == jid:
                        resolved_jobs.append(job)
                        break

        for ref in p.job_refs:
            result = resolve_job_ref(ref, self.ctx.tools)
            if isinstance(result, dict):
                resolved_jobs.append(result)
            elif isinstance(result, list):
                resolved_jobs.extend(result[:2])

        if not resolved_jobs:
            if p.mode == "rank":
                resolved_jobs = self.ctx.ensure_jobs()
            if not resolved_jobs:
                yield self.text("I need to know which jobs to compare. Could you specify company names or job IDs?")
                return

        profile = self.ctx.ensure_profile()
        jobs_text = json.dumps(resolved_jobs, indent=2)

        if p.mode == "compare" and len(resolved_jobs) >= 2:
            dimensions = ", ".join(p.dimensions) if p.dimensions else "salary, role scope, culture, growth potential, remote flexibility"
            system_prompt = COMPARISON_PROMPT.format(
                jobs=jobs_text, profile=profile, dimensions=dimensions,
            )
            agent = ComparisonAgent(self.model)
            user_msg = f"Compare these {len(resolved_jobs)} jobs."
        elif p.mode == "rank":
            system_prompt = RANKING_PROMPT.format(jobs=jobs_text, profile=profile)
            agent = RankingAgent(self.model)
            user_msg = f"Rank these {len(resolved_jobs)} jobs."
        elif p.mode == "pros_cons" and resolved_jobs:
            system_prompt = ANALYSIS_PROMPT.format(
                profile=profile, jobs=jobs_text,
                question=f"What are the pros and cons of {resolved_jobs[0].get('title', 'this job')} at {resolved_jobs[0].get('company', 'this company')}?",
            )
            agent = AnalysisAgent(self.model)
            user_msg = "Analyze the pros and cons of this job."
        else:
            system_prompt = COMPARISON_PROMPT.format(
                jobs=jobs_text, profile=profile, dimensions="overall fit",
            )
            agent = ComparisonAgent(self.model)
            user_msg = "Compare these jobs."

        for chunk in agent.run(system_prompt, user_msg):
            yield self.text(chunk)


def run(model, params, ctx):
    yield from ComparePipeline(model, params, ctx).execute()
