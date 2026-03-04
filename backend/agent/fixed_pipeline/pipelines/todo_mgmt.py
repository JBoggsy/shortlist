"""Todo management pipeline — list, create, toggle, generate, delete application todos."""

import json
import logging

from ..entity_resolution import resolve_job_ref_or_fail
from ..micro_agents import TodoGeneratorAgent
from ..pipeline_base import Pipeline, ToolResult
from ..prompts import TODO_GENERATOR_PROMPT
from ..schemas import TodoMgmtParams

logger = logging.getLogger(__name__)


class TodoMgmtPipeline(Pipeline):
    params_schema = TodoMgmtParams

    def execute(self):
        p = self.params
        logger.info("[TodoMgmtPipeline] action=%s, job_ref=%s, job_id=%s, todo_id=%s",
                    p.action, p.job_ref, p.job_id, p.todo_id)

        if p.action == "list":
            yield from self._list_todos()
        elif p.action == "toggle":
            yield from self._toggle_todo()
        elif p.action == "create":
            yield from self._create_todo()
        elif p.action == "generate":
            yield from self._generate_todos()
        elif p.action == "delete":
            yield from self._delete_todo()
        else:
            yield self.text(f"Unknown todo action: {p.action}")

    def _list_todos(self):
        p = self.params
        job, error = resolve_job_ref_or_fail(p.job_ref, p.job_id, self.ctx.tools)
        if error:
            yield self.text(error)
            return

        tr = ToolResult()
        yield from self.exec_tool("list_job_todos", {"job_id": job["id"]}, tr)

        todos = tr.data.get("todos", [])
        company = job.get("company", "?")
        title = job.get("title", "?")

        if not todos:
            yield self.text(f"No todos yet for **{title}** at **{company}**. Would you like me to generate some prep tasks?")
            return

        lines = [f"**Application todos for {title} at {company}:**\n"]
        for todo in todos:
            check = "✅" if todo.get("completed") else "⬜"
            line = f"- {check} {todo.get('title', '?')}"
            if todo.get("category"):
                line += f" [{todo['category']}]"
            line += f" (ID: {todo['id']})"
            lines.append(line)

        done = sum(1 for t in todos if t.get("completed"))
        lines.append(f"\n{done}/{len(todos)} completed")
        yield self.text("\n".join(lines))

    def _toggle_todo(self):
        p = self.params
        job, error = resolve_job_ref_or_fail(p.job_ref, p.job_id, self.ctx.tools)
        if error:
            yield self.text(error)
            return

        if not p.todo_id:
            yield self.text("I need a todo ID to toggle. Use the ID shown in the todo list.")
            return

        completed = p.todo_data.get("completed", True)

        tr = ToolResult()
        yield from self.exec_tool(
            "edit_job_todo",
            {"job_id": job["id"], "todo_id": p.todo_id, "completed": completed},
            tr,
        )

        if tr.is_error:
            yield self.text(f"\nCouldn't update that todo: {tr.error}")
        else:
            todo = tr.data.get("todo", {})
            status = "done" if todo.get("completed") else "not done"
            yield self.text(f"\nMarked **{todo.get('title', '?')}** as {status}.")

    def _create_todo(self):
        p = self.params
        job, error = resolve_job_ref_or_fail(p.job_ref, p.job_id, self.ctx.tools)
        if error:
            yield self.text(error)
            return

        todo_data = dict(p.todo_data)
        todo_data["job_id"] = job["id"]

        if not todo_data.get("title"):
            yield self.text("I need a title for the todo item. What task should I add?")
            return

        tr = ToolResult()
        yield from self.exec_tool("add_job_todo", todo_data, tr)

        if tr.is_error:
            yield self.text(f"\nCouldn't create that todo: {tr.error}")
        else:
            todo = tr.data.get("todo", {})
            yield self.text(f"\nAdded todo: **{todo.get('title', '?')}**")

    def _generate_todos(self):
        p = self.params
        job, error = resolve_job_ref_or_fail(p.job_ref, p.job_id, self.ctx.tools)
        if error:
            yield self.text(error)
            return

        profile = self.ctx.ensure_profile()
        resume_summary = self.ctx.get_resume_summary()

        system_prompt = TODO_GENERATOR_PROMPT.format(
            job=json.dumps(job, indent=2), profile=profile, resume_summary=resume_summary,
        )

        agent = TodoGeneratorAgent(self.model)
        try:
            result = agent.run(system_prompt, "Generate application preparation tasks for this job.")
            todos = result.todos if hasattr(result, "todos") else []
        except Exception as e:
            logger.warning("Todo generation failed: %s", e)
            yield self.text("I had trouble generating todos. You can add them manually with specific tasks.")
            return

        if not todos:
            yield self.text("I couldn't generate any specific tasks. Could you tell me what kind of preparation you need?")
            return

        created = 0
        for todo in todos:
            todo_data = {
                "job_id": job["id"],
                "title": todo.title,
                "category": todo.category,
                "description": todo.description,
            }
            tr = ToolResult()
            yield from self.exec_tool("add_job_todo", todo_data, tr)
            if not tr.is_error:
                created += 1

        company = job.get("company", "?")
        title = job.get("title", "?")
        yield self.text(f"\nCreated **{created}** prep tasks for your **{title}** at **{company}** application.")

    def _delete_todo(self):
        p = self.params
        job, error = resolve_job_ref_or_fail(p.job_ref, p.job_id, self.ctx.tools)
        if error:
            yield self.text(error)
            return

        if not p.todo_id:
            yield self.text("I need a todo ID to delete. Use the ID shown in the todo list.")
            return

        tr = ToolResult()
        yield from self.exec_tool(
            "remove_job_todo",
            {"job_id": job["id"], "todo_id": p.todo_id},
            tr,
        )

        if tr.is_error:
            yield self.text(f"\nCouldn't delete that todo: {tr.error}")
        else:
            deleted = tr.data.get("deleted", {})
            yield self.text(f"\nRemoved todo: **{deleted.get('title', '?')}**")


def run(model, params, ctx):
    yield from TodoMgmtPipeline(model, params, ctx).execute()
