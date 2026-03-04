"""Track CRUD pipeline — create, edit, delete jobs in the tracker."""

import logging

from ..entity_resolution import resolve_job_ref_or_fail
from ..pipeline_base import Pipeline, ToolResult
from ..schemas import TrackCrudParams

logger = logging.getLogger(__name__)


class TrackCrudPipeline(Pipeline):
    params_schema = TrackCrudParams

    def execute(self):
        p = self.params
        logger.info("[TrackCrudPipeline] action=%s, job_ref=%s, job_id=%s, fields=%s",
                    p.action, p.job_ref, p.job_id, dict(p.fields))

        if p.action == "create":
            yield from self._create()
        elif p.action == "edit":
            yield from self._edit()
        elif p.action == "delete":
            yield from self._delete()
        else:
            yield self.text(f"Unknown action: {p.action}")

    def _create(self):
        p = self.params
        fields = dict(p.fields)
        if not fields.get("company") and not fields.get("title"):
            yield self.text("I need at least a company name and job title to add a job. Could you provide those?")
            return

        tr = ToolResult()
        yield from self.exec_tool("create_job", fields, tr)

        if tr.is_error:
            yield self.text(f"\nSorry, I couldn't create that job: {tr.error}")
        else:
            job = tr.data.get("job", {})
            company = job.get("company", "Unknown")
            title = job.get("title", "Unknown")
            yield self.text(f"\nAdded **{title}** at **{company}** to your tracker.")

            extras = []
            if job.get("status") and job["status"] != "saved":
                extras.append(f"Status: {job['status']}")
            if job.get("salary_min") or job.get("salary_max"):
                salary = _format_salary(job.get("salary_min"), job.get("salary_max"))
                extras.append(f"Salary: {salary}")
            if job.get("location"):
                extras.append(f"Location: {job['location']}")
            if job.get("remote_type"):
                extras.append(f"Remote: {job['remote_type']}")
            if extras:
                yield self.text(" " + " | ".join(extras))

    def _edit(self):
        p = self.params
        job, error = resolve_job_ref_or_fail(p.job_ref, p.job_id, self.ctx.tools)
        if error:
            yield self.text(error)
            return

        fields = dict(p.fields)
        fields["job_id"] = job["id"]

        tr = ToolResult()
        yield from self.exec_tool("edit_job", fields, tr)

        if tr.is_error:
            yield self.text(f"\nSorry, I couldn't update that job: {tr.error}")
        else:
            updated = tr.data.get("updated_fields", [])
            job_data = tr.data.get("job", {})
            company = job_data.get("company", "Unknown")
            title = job_data.get("title", "Unknown")
            if updated:
                changes = ", ".join(f"{f}" for f in updated)
                yield self.text(f"\nUpdated **{title}** at **{company}**: {changes}.")
            else:
                yield self.text(f"\n**{title}** at **{company}** is already up to date.")

    def _delete(self):
        p = self.params
        job, error = resolve_job_ref_or_fail(p.job_ref, p.job_id, self.ctx.tools)
        if error:
            yield self.text(error)
            return

        tr = ToolResult()
        yield from self.exec_tool("remove_job", {"job_id": job["id"]}, tr)

        if tr.is_error:
            yield self.text(f"\nSorry, I couldn't delete that job: {tr.error}")
        else:
            deleted = tr.data.get("deleted", {})
            company = deleted.get("company", "Unknown")
            title = deleted.get("title", "Unknown")
            yield self.text(f"\nRemoved **{title}** at **{company}** from your tracker.")


def _format_salary(salary_min, salary_max):
    """Format salary range for display."""
    if salary_min and salary_max:
        return f"${salary_min:,}–${salary_max:,}"
    if salary_min:
        return f"${salary_min:,}+"
    if salary_max:
        return f"Up to ${salary_max:,}"
    return ""


def run(model, params, ctx):
    yield from TrackCrudPipeline(model, params, ctx).execute()
