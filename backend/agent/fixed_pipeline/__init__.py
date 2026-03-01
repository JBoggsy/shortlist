"""Fixed Pipeline agent design — programmatic pipelines with micro-agents.

Replaces the monolithic ReAct loop with structured routing and deterministic
pipelines. The Routing Agent classifies user intent, then a pipeline dispatcher
executes the appropriate sequence of programmatic steps and scoped LLM calls.

See DESIGN.md in this directory for the full architecture documentation.
"""

from .agent import FixedPipelineAgent

# Reuse default design for onboarding and resume parsing — these are
# inherently conversational (onboarding) or single-shot (resume parsing)
# and don't benefit from pipeline routing.
from backend.agent.default import (
    DefaultOnboardingAgent as FixedPipelineOnboardingAgent,
    DefaultResumeParser as FixedPipelineResumeParser,
)

__all__ = ["FixedPipelineAgent", "FixedPipelineOnboardingAgent", "FixedPipelineResumeParser"]
