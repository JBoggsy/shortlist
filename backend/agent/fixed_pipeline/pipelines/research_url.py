"""Research URL pipeline — analyze a URL (job posting, company page)."""

import json
import logging

from ..micro_agents import AnalysisSummaryAgent, DetailExtractionAgent, FitEvaluatorAgent
from ..pipeline_base import Pipeline, ToolResult
from ..prompts import ANALYSIS_SUMMARY_PROMPT, DETAIL_EXTRACTION_PROMPT, FIT_EVALUATOR_PROMPT
from ..schemas import ResearchUrlParams

logger = logging.getLogger(__name__)


class ResearchUrlPipeline(Pipeline):
    params_schema = ResearchUrlParams

    def execute(self):
        p = self.params

        if not p.url:
            yield self.text("I need a URL to analyze. Could you share the link?")
            return

        # Step 1: Scrape the URL
        tr = ToolResult()
        yield from self.exec_tool("scrape_url", {"url": p.url}, tr)

        if tr.is_error:
            yield self.text(f"\nI couldn't access that URL: {tr.error}. Could you check the link?")
            return

        raw_content = tr.data.get("content", "")
        if not raw_content:
            yield self.text("\nThe page appears to be empty or blocked. Could you paste the job description instead?")
            return

        yield self.text("\nAnalyzing the posting...")

        # Step 2: Extract structured details
        details = self._extract_details(raw_content, p.url)

        # Step 3: Load profile and evaluate fit
        profile = self.ctx.ensure_profile()
        resume_summary = self.ctx.get_resume_summary()
        evaluation = self._evaluate_fit(details, profile, resume_summary)

        # Step 4: Optionally add to tracker
        added_job = None
        if p.intent in ("add_to_tracker", "analyze"):
            job_fields = _build_job_fields(details, evaluation, p.url)
            if job_fields.get("company") and job_fields.get("title"):
                if p.intent == "add_to_tracker":
                    tr = ToolResult()
                    yield from self.exec_tool("create_job", job_fields, tr)
                    if not tr.is_error:
                        added_job = tr.data.get("job", {})

        # Step 5: Stream analysis summary
        yield self.text("\n\n")
        yield from self._summarize_analysis(details, evaluation, added_job)

    def _extract_details(self, raw_content: str, url: str) -> dict:
        try:
            system_prompt = DETAIL_EXTRACTION_PROMPT.format(raw_data=raw_content[:4000])
            agent = DetailExtractionAgent(self.model)
            result = agent.run(system_prompt, f"Extract job details from this page: {url}")
            if hasattr(result, "model_dump"):
                return result.model_dump()
            if isinstance(result, dict):
                return result
        except Exception as e:
            logger.warning("Detail extraction failed: %s", e)
        return {"url": url}

    def _evaluate_fit(self, details: dict, profile: str, resume_summary: str) -> dict:
        try:
            system_prompt = FIT_EVALUATOR_PROMPT.format(
                job=json.dumps(details, indent=2), profile=profile, resume_summary=resume_summary,
            )
            agent = FitEvaluatorAgent(self.model)
            result = agent.run(system_prompt, "Evaluate this job's fit with the user's profile.")
            if hasattr(result, "model_dump"):
                return result.model_dump()
            if isinstance(result, dict):
                return result
        except Exception as e:
            logger.warning("Fit evaluation failed: %s", e)
        return {"job_fit": 3, "fit_reason": "Could not evaluate fit", "strengths": [], "gaps": []}

    def _summarize_analysis(self, details: dict, evaluation: dict, added_job: dict | None):
        eval_text = json.dumps(evaluation, indent=2)
        if added_job:
            eval_text += f"\n\n(Job was added to tracker with ID {added_job.get('id')})"

        system_prompt = ANALYSIS_SUMMARY_PROMPT.format(
            job=json.dumps(details, indent=2), evaluation=eval_text,
        )

        agent = AnalysisSummaryAgent(self.model)
        for chunk in agent.run(system_prompt, "Summarize this job posting analysis."):
            yield self.text(chunk)


def _build_job_fields(details: dict, evaluation: dict, url: str) -> dict:
    """Build job creation fields from extracted details and evaluation."""
    fields = {}
    for key in ["company", "title", "location", "remote_type", "requirements",
                 "nice_to_haves", "salary_min", "salary_max", "source"]:
        value = details.get(key)
        if value:
            fields[key] = value
    fields["url"] = details.get("url") or url
    if evaluation.get("job_fit") is not None:
        fields["job_fit"] = evaluation["job_fit"]
    return fields


def run(model, params, ctx):
    yield from ResearchUrlPipeline(model, params, ctx).execute()
