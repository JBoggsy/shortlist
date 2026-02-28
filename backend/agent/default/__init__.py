"""Default agent design — monolithic ReAct loop.

Each agent runs a straightforward ReAct (Reason + Act) loop: the LLM reasons
about what to do, optionally calls tools, observes the results, and repeats
until it has a final answer.
"""

from .agent import DefaultAgent
from .onboarding_agent import DefaultOnboardingAgent
from .resume_parser import DefaultResumeParser

__all__ = ["DefaultAgent", "DefaultOnboardingAgent", "DefaultResumeParser"]
