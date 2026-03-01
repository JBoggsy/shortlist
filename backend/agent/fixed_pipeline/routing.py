"""Routing Agent — classify user intent and extract structured parameters."""

import logging

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

from .micro_agents import BaseMicroAgent
from .prompts import ROUTING_SYSTEM_PROMPT
from .schemas import RoutingResult

logger = logging.getLogger(__name__)

# Number of recent messages to include for context
HISTORY_WINDOW = 6


def route(model: BaseChatModel, messages: list[dict]) -> RoutingResult:
    """Classify the user's request and extract parameters.

    Args:
        model: LLM model instance.
        messages: Full conversation history (list of {role, content}).

    Returns:
        RoutingResult with request_type, params, entity_refs, acknowledgment.
        Falls back to general pipeline on any failure.
    """
    # Build the user message with recent history for context
    recent = messages[-HISTORY_WINDOW:] if len(messages) > HISTORY_WINDOW else messages
    user_msg = _format_history_for_routing(recent)

    agent = BaseMicroAgent(model)

    try:
        result = agent.invoke(
            ROUTING_SYSTEM_PROMPT,
            user_msg,
            output_schema=RoutingResult,
        )
        if isinstance(result, RoutingResult):
            logger.info("Routed to '%s': %s", result.request_type, result.acknowledgment)
            return result
        # If we got a dict back from JSON fallback, validate it
        if isinstance(result, dict):
            validated = RoutingResult.model_validate(result)
            logger.info("Routed to '%s' (JSON fallback): %s",
                       validated.request_type, validated.acknowledgment)
            return validated
    except Exception as e:
        logger.warning("Routing failed: %s — falling back to general", e)

    # Fallback: general pipeline
    last_user_msg = ""
    for msg in reversed(messages):
        if msg["role"] == "user":
            last_user_msg = msg["content"]
            break

    return RoutingResult(
        request_type="general",
        params={"question": last_user_msg, "needs_profile": True},
        entity_refs=[],
        acknowledgment="",
    )


def _format_history_for_routing(messages: list[dict]) -> str:
    """Format recent messages into a text block for the routing agent."""
    parts = []
    for msg in messages:
        role = msg["role"].upper()
        content = msg["content"]
        # Truncate very long messages for routing context
        if len(content) > 500:
            content = content[:500] + "..."
        parts.append(f"[{role}]: {content}")
    return "\n\n".join(parts)
