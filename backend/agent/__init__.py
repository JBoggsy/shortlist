"""Agent design selection.

Reads ``agent.design`` from the application config to determine which concrete
agent implementation to use.  Each design lives in its own sub-package at
``backend/agent/{design_name}/`` and must export three classes:

    {DesignName}Agent
    {DesignName}OnboardingAgent
    {DesignName}ResumeParser

where *DesignName* is the ``snake_case`` design name converted to PascalCase.

The primary API is :func:`get_agent_classes`, which resolves the active design
**at call time** (not import time) so the user can hot-swap designs from the
Settings UI without restarting the server.

For backwards compatibility the module still exports ``ActiveAgent``,
``ActiveOnboardingAgent``, and ``ActiveResumeParser`` — but new code should
prefer :func:`get_agent_classes`.
"""

import importlib
import logging

from backend.agent.base import Agent, OnboardingAgent, ResumeParser

logger = logging.getLogger(__name__)

DEFAULT_DESIGN = "default"

# Maps design_name -> "freeform" | "orchestrated"
DESIGN_MODES = {
    "default": "freeform",
    "micro_agents_v1": "orchestrated",
}

# Inverse map: mode -> design_name
MODE_TO_DESIGN = {v: k for k, v in DESIGN_MODES.items()}

# Cache of already-loaded design classes keyed by design_name
_design_cache: dict[str, tuple] = {}


def _to_pascal(snake: str) -> str:
    """Convert a snake_case string to PascalCase."""
    return "".join(word.capitalize() for word in snake.split("_"))


def _get_design_name() -> str:
    """Read the active agent design name from config."""
    try:
        from backend.config_manager import get_config_value
        design = get_config_value("agent.design", DEFAULT_DESIGN) or DEFAULT_DESIGN
        # Support mode names ("freeform"/"orchestrated") as well as raw design names
        return MODE_TO_DESIGN.get(design, design)
    except Exception:
        return DEFAULT_DESIGN


def _load_agent_classes(design_name: str | None = None):
    """Import and return ``(Agent, OnboardingAgent, ResumeParser)`` for *design_name*.

    Results are cached so repeated calls for the same design don't re-import.
    Falls back to the abstract base classes when the design module or expected
    class names cannot be resolved.
    """
    if not design_name:
        design_name = DEFAULT_DESIGN

    if design_name in _design_cache:
        return _design_cache[design_name]

    prefix = _to_pascal(design_name)

    try:
        module = importlib.import_module(f"backend.agent.{design_name}")
        agent_cls = getattr(module, f"{prefix}Agent")
        onboarding_cls = getattr(module, f"{prefix}OnboardingAgent")
        parser_cls = getattr(module, f"{prefix}ResumeParser")
        logger.info("Loaded agent design '%s' (%sAgent, %sOnboardingAgent, %sResumeParser)",
                     design_name, prefix, prefix, prefix)
        result = (agent_cls, onboarding_cls, parser_cls)
        _design_cache[design_name] = result
        return result
    except (ImportError, AttributeError) as exc:
        logger.warning("Could not load agent design '%s': %s — falling back to base ABCs.",
                        design_name, exc)
        return Agent, OnboardingAgent, ResumeParser


def get_agent_classes(design_name: str | None = None):
    """Return ``(AgentCls, OnboardingAgentCls, ResumeParserCls)`` for the
    currently configured (or explicitly requested) design.

    Call this at **request time** so that config changes take effect
    without a server restart.
    """
    if design_name is None:
        design_name = _get_design_name()
    else:
        # Translate mode name if provided
        design_name = MODE_TO_DESIGN.get(design_name, design_name)
    return _load_agent_classes(design_name)


# ── Backwards-compatible aliases (resolved at import time) ───────────────
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
    "get_agent_classes",
    "DESIGN_MODES",
    "MODE_TO_DESIGN",
]
