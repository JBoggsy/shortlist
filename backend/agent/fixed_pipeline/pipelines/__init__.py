"""Pipeline registry — maps request_type to pipeline functions."""

from .compare import run as compare
from .find_jobs import run as find_jobs
from .general import run as general
from .multi_step import run as multi_step
from .prepare import run as prepare
from .profile_mgmt import run as profile_mgmt
from .query_jobs import run as query_jobs
from .research import run as research
from .research_url import run as research_url
from .todo_mgmt import run as todo_mgmt
from .track_crud import run as track_crud

PIPELINE_REGISTRY = {
    "find_jobs": find_jobs,
    "research_url": research_url,
    "track_crud": track_crud,
    "query_jobs": query_jobs,
    "todo_mgmt": todo_mgmt,
    "profile_mgmt": profile_mgmt,
    "prepare": prepare,
    "compare": compare,
    "research": research,
    "general": general,
    "multi_step": multi_step,
}
