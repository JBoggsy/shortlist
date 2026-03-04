"""Query jobs pipeline — read, filter, and summarize tracked jobs."""

import json
import logging

from ..micro_agents import AnalysisAgent
from ..pipeline_base import Pipeline, ToolResult
from ..prompts import ANALYSIS_PROMPT
from ..schemas import QueryJobsParams

logger = logging.getLogger(__name__)


class QueryJobsPipeline(Pipeline):
    params_schema = QueryJobsParams

    def execute(self):
        p = self.params
        logger.info("[QueryJobsPipeline] question=%s, filters=%s, format=%s",
                    (p.question or "")[:100], p.filters, p.format)

        tool_args = {}
        if p.filters:
            tool_args.update(p.filters)

        tr = ToolResult()
        yield from self.exec_tool("list_jobs", tool_args, tr)

        jobs = tr.data.get("jobs", [])
        count = tr.data.get("count", 0)

        if count == 0:
            filters_desc = ""
            if p.filters:
                filters_desc = f" matching your filters ({', '.join(f'{k}={v}' for k, v in p.filters.items())})"
            yield self.text(f"You don't have any jobs{filters_desc} in your tracker yet.")
            return

        is_complex = p.question and any(word in p.question.lower() for word in [
            "best", "recommend", "rank", "compare", "which", "should", "analyze",
            "fit", "match", "suitable", "ideal", "top", "strongest",
        ])

        if is_complex and p.question:
            profile = self.ctx.ensure_profile()
            jobs_text = json.dumps(jobs[:20], indent=2)
            system_prompt = ANALYSIS_PROMPT.format(
                profile=profile, jobs=jobs_text, question=p.question,
            )
            agent = AnalysisAgent(self.model)
            for chunk in agent.run(system_prompt, p.question):
                yield self.text(chunk)
        elif p.format == "count":
            yield self.text(f"You have **{count}** job(s) in your tracker.")
        elif p.format == "summary":
            yield self.text(_format_job_summary(jobs))
        else:
            yield self.text(_format_job_list(jobs))


def _format_job_list(jobs: list[dict]) -> str:
    """Format jobs as a readable list."""
    if not jobs:
        return "No jobs found."

    lines = [f"**Your tracked jobs ({len(jobs)}):**\n"]
    for job in jobs:
        status_emoji = {
            "saved": "📋", "applied": "📨", "interviewing": "🎤",
            "offer": "🎉", "rejected": "❌"
        }.get(job.get("status", ""), "📋")

        line = f"- {status_emoji} **{job.get('title', '?')}** at **{job.get('company', '?')}**"
        extras = []
        if job.get("status"):
            extras.append(job["status"])
        if job.get("location"):
            extras.append(job["location"])
        if job.get("remote_type"):
            extras.append(job["remote_type"])
        if job.get("job_fit"):
            extras.append(f"{'⭐' * job['job_fit']}")
        if extras:
            line += f" ({', '.join(extras)})"
        line += f" — ID: {job['id']}"
        lines.append(line)

    return "\n".join(lines)


def _format_job_summary(jobs: list[dict]) -> str:
    """Format jobs as a summary with stats."""
    if not jobs:
        return "No jobs in your tracker."

    status_counts = {}
    for job in jobs:
        status = job.get("status", "saved")
        status_counts[status] = status_counts.get(status, 0) + 1

    lines = [f"**Job Tracker Summary ({len(jobs)} total):**\n"]
    for status, count in sorted(status_counts.items()):
        lines.append(f"- {status.capitalize()}: {count}")

    recent = jobs[:3]
    if recent:
        lines.append("\n**Most recent:**")
        for job in recent:
            lines.append(f"- {job.get('title', '?')} at {job.get('company', '?')} ({job.get('status', '?')})")

    return "\n".join(lines)


def run(model, params, ctx):
    yield from QueryJobsPipeline(model, params, ctx).execute()
