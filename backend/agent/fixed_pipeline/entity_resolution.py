"""Entity resolution — resolve natural-language job references to Job records."""

import logging
import re

from backend.agent.tools import AgentTools

logger = logging.getLogger(__name__)


def _score_match(query: str, value: str) -> float:
    """Score how well a query matches a value using tiered matching.

    Returns:
        100 for exact match, 80 for prefix, 60 for word boundary, 40 for substring, 0 for no match.
    """
    if not query or not value:
        return 0

    q = query.lower().strip()
    v = value.lower().strip()

    if q == v:
        return 100
    if v.startswith(q):
        return 80
    # Word boundary: query appears as a whole word in the value
    if re.search(r'\b' + re.escape(q) + r'\b', v):
        return 60
    if q in v:
        return 40
    return 0


def _score_job(query: str, job: dict) -> float:
    """Score a job against a query, checking both company and title.

    Returns the best score, with a +10 bonus if both fields match.
    """
    company_score = _score_match(query, job.get("company", ""))
    title_score = _score_match(query, job.get("title", ""))

    best = max(company_score, title_score)
    if best == 0:
        return 0

    # Bonus if both fields match
    if company_score > 0 and title_score > 0:
        best += 10

    return best


def _select_best(scored: list[tuple[float, dict]], threshold: float = 20.0):
    """Auto-select the best match or return ambiguous list.

    Args:
        scored: List of (score, job) tuples, sorted by score descending.
        threshold: Minimum gap between #1 and #2 to auto-select.

    Returns:
        Single job dict (auto-selected), list of job dicts (ambiguous), or None.
    """
    if not scored:
        return None
    if len(scored) == 1:
        return scored[0][1]

    top_score, top_job = scored[0]

    # Exact match → auto-select
    if top_score >= 100:
        return top_job

    # Clear gap → auto-select
    runner_up_score = scored[1][0]
    if top_score - runner_up_score >= threshold:
        return top_job

    # Ambiguous — return all within threshold of top
    return [job for score, job in scored if top_score - score < threshold]


def resolve_job_ref(ref: str, tools: AgentTools) -> dict | list[dict] | None:
    """Resolve a natural-language job reference to a Job record.

    Strategy:
    1. If ref is a plain integer or "#N", look up by ID.
    2. Otherwise, fetch all jobs, score each against the query, and auto-select
       when the top match is clearly better than the runner-up.

    Args:
        ref: Natural-language reference ("Google", "job #5", "the Stripe SWE job").
        tools: AgentTools instance for executing list_jobs.

    Returns:
        Single job dict, list of job dicts (ambiguous), or None (not found).
    """
    if not ref:
        return None

    ref = ref.strip()

    # Check for numeric ID: "#5", "5", "job 5", "job #5", "id 5"
    id_match = re.match(r"^(?:#|job\s*#?|id\s*#?)?\s*(\d+)\s*$", ref, re.IGNORECASE)
    if id_match:
        job_id = int(id_match.group(1))
        result = tools.execute("list_jobs", {"limit": 100})
        jobs = result.get("jobs", [])
        for job in jobs:
            if job.get("id") == job_id:
                return job
        return None

    # Text-based resolution: fetch all jobs, score, and rank
    result = tools.execute("list_jobs", {"limit": 100})
    all_jobs = result.get("jobs", [])

    if not all_jobs:
        return None

    scored = []
    for job in all_jobs:
        score = _score_job(ref, job)
        if score > 0:
            scored.append((score, job))

    if not scored:
        return None

    # Sort by score descending
    scored.sort(key=lambda x: x[0], reverse=True)

    return _select_best(scored)


def resolve_job_ref_or_fail(ref: str | None, job_id: int | None, tools: AgentTools) -> tuple[dict | None, str | None]:
    """Resolve a job reference, returning (job, error_message).

    Tries job_id first, then ref. Returns an error message if not found
    or ambiguous (caller should yield it as text_delta).
    """
    if job_id:
        result = tools.execute("list_jobs", {"limit": 100})
        for job in result.get("jobs", []):
            if job.get("id") == job_id:
                return job, None
        return None, f"I couldn't find a job with ID {job_id}."

    if not ref:
        return None, "I need to know which job you're referring to. Could you specify the company name or job ID?"

    resolved = resolve_job_ref(ref, tools)
    if resolved is None:
        return None, f"I couldn't find a job matching \"{ref}\". Could you check the name or use a job ID?"
    if isinstance(resolved, list):
        # Ambiguous — list the options
        options = "\n".join(
            f"- **{j.get('title', '?')}** at **{j.get('company', '?')}** (ID: {j['id']})"
            for j in resolved[:5]
        )
        return None, f"I found multiple jobs matching \"{ref}\":\n{options}\n\nWhich one did you mean? You can use the ID to be specific."

    return resolved, None
