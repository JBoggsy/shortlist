"""Agent design selection.

Reads ``agent.design`` from the application config to determine which concrete
agent implementation to use.  Each design lives in its own sub-package at
``backend/agent/{design_name}/`` and must export three classes:

    {DesignName}Agent
    {DesignName}OnboardingAgent
    {DesignName}ResumeParser

where *DesignName* is the ``snake_case`` design name converted to PascalCase.

This module re-exports the chosen classes as:

    ActiveAgent
    ActiveOnboardingAgent
    ActiveResumeParser

so the rest of the application has a single, stable import path regardless of
which design is active.

If no design is configured, or the configured design cannot be loaded, the
abstract base classes from ``backend.agent.base`` are used as a fallback (they
will raise ``TypeError`` if someone tries to instantiate them, which is the
desired behaviour until a real implementation is available).
"""

import importlib
import logging

from backend.agent.base import Agent, OnboardingAgent, ResumeParser

logger = logging.getLogger(__name__)

DEFAULT_DESIGN = "default"


def _to_pascal(snake: str) -> str:
    """Convert a snake_case string to PascalCase."""
    return "".join(word.capitalize() for word in snake.split("_"))


def _get_design_name() -> str:
    """Read the active agent design name from config."""
    try:
        from backend.config_manager import get_config_value
        return get_config_value("agent.design", DEFAULT_DESIGN) or DEFAULT_DESIGN
    except Exception:
        return DEFAULT_DESIGN


def _load_agent_classes(design_name: str | None = None):
    """Import and return ``(Agent, OnboardingAgent, ResumeParser)`` for *design_name*.

    Falls back to the abstract base classes when the design module or expected
    class names cannot be resolved.
    """
    if not design_name:
        design_name = DEFAULT_DESIGN

    prefix = _to_pascal(design_name)

    try:
        module = importlib.import_module(f"backend.agent.{design_name}")
        agent_cls = getattr(module, f"{prefix}Agent")
        onboarding_cls = getattr(module, f"{prefix}OnboardingAgent")
        parser_cls = getattr(module, f"{prefix}ResumeParser")
        logger.info("Loaded agent design '%s' (%sAgent, %sOnboardingAgent, %sResumeParser)",
                     design_name, prefix, prefix, prefix)
        return agent_cls, onboarding_cls, parser_cls
    except (ImportError, AttributeError) as exc:
        logger.warning("Could not load agent design '%s': %s — falling back to base ABCs.",
                        design_name, exc)
        return Agent, OnboardingAgent, ResumeParser


# ── Resolve active classes at import time ────────────────────────────────
ActiveAgent, ActiveOnboardingAgent, ActiveResumeParser = _load_agent_classes(
    _get_design_name()
)

__all__ = [
    "Agent",
    "OnboardingAgent",
    "ResumeParser",
    "ActiveAgent",
    "ActiveOnboardingAgent",
    "ActiveResumeParser",
]
