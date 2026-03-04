"""Profile management pipeline — read or update the user profile."""

import logging

from ..micro_agents import ProfileUpdateAgent
from ..pipeline_base import Pipeline, ToolResult
from ..prompts import PROFILE_UPDATE_PROMPT
from ..schemas import ProfileMgmtParams

logger = logging.getLogger(__name__)


class ProfileMgmtPipeline(Pipeline):
    params_schema = ProfileMgmtParams

    def execute(self):
        p = self.params
        logger.info("[ProfileMgmtPipeline] action=%s, section=%s", p.action, p.section)

        if p.action == "read":
            yield from self._read_profile()
        elif p.action == "update":
            yield from self._update_profile()
        else:
            yield self.text(f"Unknown profile action: {p.action}")

    def _read_profile(self):
        tr = ToolResult()
        yield from self.exec_tool("read_user_profile", {}, tr)

        content = tr.data.get("content", "")
        if content:
            yield self.text(f"Here's your current profile:\n\n{content}")
        else:
            yield self.text("Your profile is empty. Would you like to set it up?")

    def _update_profile(self):
        p = self.params

        if p.section and p.content:
            # Simple direct update
            tr = ToolResult()
            yield from self.exec_tool(
                "update_user_profile",
                {"section": p.section, "content": p.content},
                tr,
            )
            if tr.is_error:
                yield self.text(f"\nCouldn't update your profile: {tr.error}")
            else:
                yield self.text(f"\nUpdated your **{p.section}** section.")
            return

        # Complex / natural-language update — use micro-agent
        update_text = p.natural_update or p.content or ""
        if not update_text:
            yield self.text("What would you like to update in your profile?")
            return

        profile = self.ctx.ensure_profile()
        system_prompt = PROFILE_UPDATE_PROMPT.format(
            profile=profile, request=update_text,
        )

        agent = ProfileUpdateAgent(self.model)
        try:
            result = agent.run(system_prompt, update_text)
            updates = result.updates if hasattr(result, "updates") else []
        except Exception as e:
            logger.warning("Profile update agent failed: %s", e)
            yield self.text("I had trouble interpreting that update. Could you be more specific about which section to update?")
            return

        if not updates:
            yield self.text("I couldn't determine what to update. Could you specify which section of your profile to change?")
            return

        # Apply each section update
        updated_sections = []
        for update in updates:
            tr = ToolResult()
            yield from self.exec_tool(
                "update_user_profile",
                {"section": update.section, "content": update.content},
                tr,
            )
            if not tr.is_error:
                updated_sections.append(update.section)

        if updated_sections:
            sections_str = ", ".join(f"**{s}**" for s in updated_sections)
            yield self.text(f"\nUpdated your profile: {sections_str}.")
        else:
            yield self.text("\nI wasn't able to update any sections. Please try again with more details.")


def run(model, params, ctx):
    yield from ProfileMgmtPipeline(model, params, ctx).execute()
