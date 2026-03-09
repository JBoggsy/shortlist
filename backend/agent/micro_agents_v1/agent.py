"""MicroAgentsV1Agent — workflow-orchestrated agent with DSPy micro-agents.

User requests are decomposed into discrete outcomes, each mapped to a
hand-crafted workflow and executed in dependency order.  Complex reasoning
steps within workflows are handled by small DSPy modules ("micro-agents").

Pipeline stages:
    1. Outcome Planner  — decompose user request into outcomes + dependency DAG
    2. Workflow Mapper   — match each outcome to a workflow, extract parameters
    3. Workflow Executor — run workflows in topological order, stream progress
    4. Result Collator   — synthesise a unified final response
"""

from __future__ import annotations

import logging
from collections.abc import Generator

from backend.agent.base import Agent
from backend.agent.tools import AgentTools
from backend.agent.user_profile import read_profile
from backend.llm.llm_factory import LLMConfig

from .stages.outcome_planner import Outcome, OutcomePlanner
from .stages.result_collator import ResultCollator
from .stages.workflow_executor import WorkflowExecutor
from .stages.workflow_mapper import WorkflowAssignment, WorkflowMapper
from .workflows.registry import WorkflowResult, available_workflow_names

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Top-level agent
# ---------------------------------------------------------------------------

class MicroAgentsV1Agent(Agent):
    """Workflow-orchestrated agent with DSPy micro-agents.

    Composes four pipeline stages: OutcomePlanner → WorkflowMapper →
    WorkflowExecutor → ResultCollator.  The whole agent is intended to
    become a DSPy module once the stages are implemented.
    """

    def __init__(
        self,
        llm_config: LLMConfig,
        search_api_key: str = "",
        adzuna_app_id: str = "",
        adzuna_app_key: str = "",
        adzuna_country: str = "us",
        jsearch_api_key: str = "",
        conversation_id: int | None = None,
    ):
        self.llm_config = llm_config
        self.conversation_id = conversation_id

        # Queued events from tool callbacks (e.g. search_result_added)
        self._pending_events: list[dict] = []

        # Shared tool interface
        self.tools = AgentTools(
            search_api_key=search_api_key,
            adzuna_app_id=adzuna_app_id,
            adzuna_app_key=adzuna_app_key,
            adzuna_country=adzuna_country,
            jsearch_api_key=jsearch_api_key,
            conversation_id=conversation_id,
            event_callback=self._on_tool_event,
        )

        # Pipeline stages
        self.outcome_planner = OutcomePlanner(llm_config)
        self.workflow_mapper = WorkflowMapper(llm_config)
        self.workflow_executor = WorkflowExecutor(self.tools, llm_config)
        self.result_collator = ResultCollator(llm_config)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _on_tool_event(self, event: dict):
        """Callback for tool-emitted SSE events (e.g. search_result_added)."""
        self._pending_events.append(event)

    @staticmethod
    def _available_workflow_names() -> list[str]:
        """Return the names of all registered workflows."""
        return available_workflow_names()

    # ------------------------------------------------------------------
    # Main entry point
    # ------------------------------------------------------------------

    def run(self, messages: list[dict]) -> Generator[dict, None, None]:
        user_message = messages[-1]["content"] if messages else ""
        user_profile = read_profile()
        full_text = ""

        try:
            # --- Stage 1: Outcome Planning ---
            yield {"event": "text_delta", "data": {"content": "Thinking...\n\n"}}
            full_text += "Thinking...\n\n"

            outcomes = self.outcome_planner.plan(
                user_message=user_message,
                conversation_history=messages,
                user_profile=user_profile,
            )

            logger.debug(
                "Planned outcomes: %s",
                [(o.id, o.description, o.depends_on) for o in outcomes],
            )

            # --- Stage 2: Workflow Mapping ---
            assignments = self.workflow_mapper.map(
                outcomes=outcomes,
                user_message=user_message,
                available_workflows=self._available_workflow_names(),
            )

            logger.debug(
                "Workflow assignments: %s",
                [
                    (a.outcome.id, a.workflow_name, a.params, a.deferred_params)
                    for a in assignments
                ],
            )

            # --- Stage 3: Workflow Execution ---
            results = yield from self.workflow_executor.execute(assignments)

            # Flush any tool-emitted events that queued during execution
            # (e.g. search_result_added events for the UI results panel)
            for event in self._pending_events:
                yield event
            self._pending_events.clear()

            # --- Stage 4: Result Collation ---
            for event in self.result_collator.collate(results, user_message):
                if event["event"] == "text_delta":
                    full_text += event["data"]["content"]
                yield event

        except Exception as exc:
            logger.exception("MicroAgentsV1Agent error")
            yield {"event": "error", "data": {"message": str(exc)}}
            return

        yield {"event": "done", "data": {"content": full_text}}
