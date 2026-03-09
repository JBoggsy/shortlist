"""Micro agents v1 onboarding agent — DSPy-based interactive interview.

Uses a ``dspy.ReAct`` module to conduct a multi-turn onboarding interview
that fills in the user's job-search profile.  Each call to ``run()``
processes one conversational turn: the module reads the profile/resume,
decides what to ask or update, and produces a response.

The ReAct module (with ``OnboardingTurnSig``) is the optimisable unit —
it can be tuned with BootstrapFewShot, MIPROv2, etc. to improve question
quality, profile-update accuracy, and completion detection.
"""

from __future__ import annotations

import logging
import queue
import re
from collections.abc import Generator

import dspy

from backend.agent.base import OnboardingAgent
from backend.agent.tools import AgentTools
from backend.agent.user_profile import (
    PROFILE_SECTIONS,
    is_section_unfilled,
    read_profile,
    set_onboarded,
)
from backend.llm.llm_factory import LLMConfig
from backend.resume_parser import get_resume_text, get_saved_resume

from .workflows._dspy_utils import build_dspy_tools, build_lm, run_dspy_module_streaming

logger = logging.getLogger(__name__)

MAX_ITERATIONS = 15

# Only these tools are exposed during onboarding.
_ONBOARDING_TOOL_NAMES = frozenset({
    "read_user_profile",
    "update_user_profile",
    "read_resume",
})


# ---------------------------------------------------------------------------
# DSPy signature
# ---------------------------------------------------------------------------


class OnboardingTurnSig(dspy.Signature):
    """Conduct one turn of the onboarding interview to build the user's
    job-search profile.

    You are **Shortlist**, an AI job-search assistant running the onboarding
    interview.  Your goal is to learn about the user's background and
    preferences so you can fill every section of their profile.

    Guidelines:
    - Read the current profile and resume first so you don't re-ask
      what's already known.
    - Ask about 2-3 related topics per message to keep it flowing.
    - After each user response, immediately update the relevant profile
      sections via the update_user_profile tool using the `section`
      parameter.
    - Be conversational and encouraging — this is the user's first
      interaction with the app.
    - If the user wants to skip a section, respect that and move on.
    - When all sections listed in sections_remaining have been
      reasonably covered (or explicitly skipped), set is_complete to
      True and write a friendly wrap-up message.
    """

    conversation_history: str = dspy.InputField(
        desc="Full conversation so far (previous messages formatted as 'Role: content')"
    )
    current_profile: str = dspy.InputField(
        desc="Current user profile markdown content"
    )
    resume_text: str = dspy.InputField(
        desc="User's resume text if available, otherwise 'No resume uploaded'"
    )
    sections_remaining: str = dspy.InputField(
        desc="Comma-separated list of profile sections still needing information"
    )
    sections_filled: str = dspy.InputField(
        desc="Comma-separated list of profile sections already filled in"
    )
    response: str = dspy.OutputField(
        desc="Your conversational response to the user"
    )
    is_complete: bool = dspy.OutputField(
        desc="True only when ALL profile sections have been covered or skipped"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_conversation(messages: list[dict]) -> str:
    """Format messages into a readable transcript."""
    lines = []
    for msg in messages:
        role = msg.get("role", "unknown").capitalize()
        content = msg.get("content", "")
        if content:
            lines.append(f"{role}: {content}")
    return "\n\n".join(lines) if lines else "(no messages yet)"


def _section_status(profile_body: str) -> tuple[list[str], list[str]]:
    """Return (filled, remaining) section names by checking placeholder text."""
    filled: list[str] = []
    remaining: list[str] = []
    for section_name in PROFILE_SECTIONS:
        # Find the section content between ## headers
        pattern = re.compile(
            rf"^## {re.escape(section_name)}\n(.*?)(?=^## |\Z)",
            re.MULTILINE | re.DOTALL,
        )
        m = pattern.search(profile_body)
        if m:
            content = m.group(1).strip()
            if is_section_unfilled(content):
                remaining.append(section_name)
            else:
                filled.append(section_name)
        else:
            remaining.append(section_name)
    return filled, remaining


def _get_resume_text() -> str:
    """Read resume text, returning a fallback string if unavailable."""
    info = get_saved_resume()
    if not info:
        return "No resume uploaded"
    text = get_resume_text()
    return text if text else "No resume uploaded"


def _filter_onboarding_tools(
    agent_tools: AgentTools,
    event_queue: queue.Queue | None = None,
) -> list[dspy.Tool]:
    """Build DSPy tools restricted to the onboarding subset."""
    all_tools = build_dspy_tools(agent_tools, event_queue=event_queue)
    return [t for t in all_tools if t.name in _ONBOARDING_TOOL_NAMES]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class MicroAgentsV1OnboardingAgent(OnboardingAgent):
    """Onboarding interview agent — DSPy ReAct module per turn."""

    def __init__(self, llm_config: LLMConfig):
        dspy.Module.__init__(self)
        self.llm_config = llm_config
        self._pending_events: list[dict] = []

        # Event queue shared with tool shims — tool_start / tool_result
        # events are pushed here and drained by run_dspy_module_streaming().
        self._event_queue: queue.Queue = queue.Queue()

        self.tools = AgentTools(
            event_callback=self._on_tool_event,
        )

        # Build the DSPy ReAct module with onboarding tools only
        self._dspy_tools = _filter_onboarding_tools(
            self.tools, event_queue=self._event_queue,
        )
        self._react = dspy.ReAct(
            signature=OnboardingTurnSig,
            tools=self._dspy_tools,
            max_iters=MAX_ITERATIONS,
        )

    def _on_tool_event(self, event: dict):
        """Callback for tool-emitted SSE events."""
        self._pending_events.append(event)

    def run(self, messages: list[dict]) -> Generator[dict, None, None]:
        """Process one conversational turn.

        Tool calls are streamed in real-time via
        :func:`run_dspy_module_streaming` so the user sees
        ``tool_start`` / ``tool_result`` events as they happen.
        """
        full_text = ""

        try:
            # Gather inputs for the DSPy module
            conversation_history = _format_conversation(messages)
            current_profile = read_profile()
            resume_text = _get_resume_text()
            filled, remaining = _section_status(current_profile)

            sections_filled = ", ".join(filled) if filled else "None"
            sections_remaining = ", ".join(remaining) if remaining else "None"

            # Run the DSPy ReAct module in a background thread,
            # streaming tool_start / tool_result events in real-time.
            lm = build_lm(self.llm_config)

            def _run_react():
                with dspy.context(lm=lm):
                    return self._react(
                        conversation_history=conversation_history,
                        current_profile=current_profile,
                        resume_text=resume_text,
                        sections_remaining=sections_remaining,
                        sections_filled=sections_filled,
                    )

            prediction = yield from run_dspy_module_streaming(
                _run_react, self._event_queue,
            )

            response_text = prediction.response
            is_complete = prediction.is_complete

            # Flush any remaining tool-emitted events (e.g. search_result_added)
            for event in self._pending_events:
                yield event
            self._pending_events.clear()

            # Emit the response text
            if response_text:
                yield {"event": "text_delta", "data": {"content": response_text}}
                full_text += response_text

            # Handle completion
            if is_complete:
                set_onboarded(True)
                yield {"event": "onboarding_complete", "data": {}}

        except Exception as exc:
            logger.exception("MicroAgentsV1OnboardingAgent error")
            yield {"event": "error", "data": {"message": str(exc)}}
            return
        finally:
            self._pending_events.clear()

        yield {"event": "done", "data": {"content": full_text}}
