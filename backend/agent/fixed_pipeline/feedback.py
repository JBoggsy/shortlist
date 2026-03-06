"""Feedback collection and scoring for DSPy module optimization.

Records training examples from pipeline runs (inputs/outputs of micro-agents)
and scores them based on user actions (add-to-tracker, job_fit edits).
"""

import json
import logging
from datetime import datetime, timezone

from backend.database import db
from backend.models.dspy_example import DspyExample
from backend.models.search_result import SearchResult

logger = logging.getLogger(__name__)


# ── Recording functions (called from pipelines) ─────────────────────────

def record_evaluator_example(
    conversation_id: int,
    job_context: str,
    job_results: str,
    evaluation_result,
) -> None:
    """Record an evaluator micro-agent call as a training example."""
    try:
        inputs = {"job_context": job_context, "job_results": job_results}
        output = evaluation_result.model_dump() if hasattr(evaluation_result, "model_dump") else str(evaluation_result)
        metadata = {"conversation_id": conversation_id}

        example = DspyExample(
            module_name="evaluator",
            inputs_json=json.dumps(inputs),
            output_json=json.dumps(output),
            metadata_json=json.dumps(metadata),
        )
        db.session.add(example)
        db.session.commit()
        logger.info("Recorded evaluator example for conversation %d", conversation_id)
    except Exception as e:
        logger.warning("Failed to record evaluator example: %s", e)
        db.session.rollback()


def record_query_generator_example(
    conversation_id: int,
    search_criteria: str,
    user_profile: str,
    query_result,
) -> None:
    """Record a query generator micro-agent call as a training example."""
    try:
        inputs = {"search_criteria": search_criteria, "user_profile": user_profile}
        output = query_result.model_dump() if hasattr(query_result, "model_dump") else str(query_result)
        metadata = {"conversation_id": conversation_id}

        example = DspyExample(
            module_name="query_generator",
            inputs_json=json.dumps(inputs),
            output_json=json.dumps(output),
            metadata_json=json.dumps(metadata),
        )
        db.session.add(example)
        db.session.commit()
        logger.info("Recorded query_generator example for conversation %d", conversation_id)
    except Exception as e:
        logger.warning("Failed to record query_generator example: %s", e)
        db.session.rollback()


# ── Scoring functions (called from routes) ──────────────────────────────

def score_from_tracker_add(search_result_id: int) -> None:
    """Score evaluator and query_generator examples when a search result is added to tracker.

    Evaluator scoring: for results with job_fit >= 4, what fraction were added?
    For results with job_fit <= 2, what fraction were NOT added? Average these.

    QueryGenerator scoring: tracker_adds / total_search_results for the conversation.
    """
    try:
        result = db.session.get(SearchResult, search_result_id)
        if not result:
            return

        conversation_id = result.conversation_id

        # Get all search results for this conversation
        all_results = SearchResult.query.filter_by(conversation_id=conversation_id).all()
        if not all_results:
            return

        # Compute evaluator score
        evaluator_score = _compute_evaluator_score(all_results)

        # Compute query generator score
        tracker_adds = sum(1 for r in all_results if r.added_to_tracker)
        total = len(all_results)
        query_gen_score = tracker_adds / total if total > 0 else 0.0

        now = datetime.now(timezone.utc)

        # Update evaluator examples for this conversation
        _update_examples_for_conversation("evaluator", conversation_id, evaluator_score, now)

        # Update query_generator examples for this conversation
        _update_examples_for_conversation("query_generator", conversation_id, query_gen_score, now)

    except Exception as e:
        logger.warning("Failed to score from tracker add: %s", e)
        db.session.rollback()


def score_from_job_edit(job_id: int, edited_fields: dict) -> None:
    """Score evaluator example when user edits a tracker job's job_fit.

    If the user changed the fit rating, the evaluator's prediction was off.
    Score is penalized proportionally to how far off the rating was.
    """
    if "job_fit" not in edited_fields:
        return

    try:
        # Find the search result that was promoted to this job
        result = SearchResult.query.filter_by(tracker_job_id=job_id).first()
        if not result:
            return

        conversation_id = result.conversation_id
        original_fit = result.job_fit or 3
        new_fit = edited_fields["job_fit"]

        if new_fit is None:
            return

        # Score: 1.0 if no change, decreasing with distance
        distance = abs(new_fit - original_fit)
        edit_penalty = max(0.0, 1.0 - (distance / 5.0))

        # Blend with existing evaluator score from tracker adds
        all_results = SearchResult.query.filter_by(conversation_id=conversation_id).all()
        tracker_score = _compute_evaluator_score(all_results)

        # Weighted blend: tracker behavior (70%) + edit penalty (30%)
        blended_score = 0.7 * tracker_score + 0.3 * edit_penalty

        now = datetime.now(timezone.utc)
        _update_examples_for_conversation("evaluator", conversation_id, blended_score, now)

    except Exception as e:
        logger.warning("Failed to score from job edit: %s", e)
        db.session.rollback()


# ── Metric functions (used by BootstrapFewShot) ─────────────────────────

def evaluator_metric(example, pred, trace=None):
    """Metric for evaluator optimization. Returns the stored score (0.0-1.0)."""
    return example.score


def query_gen_metric(example, pred, trace=None):
    """Metric for query generator optimization. Returns the stored score (0.0-1.0)."""
    return example.score


# ── Internal helpers ────────────────────────────────────────────────────

def _compute_evaluator_score(all_results: list) -> float:
    """Compute evaluator accuracy based on user add-to-tracker behavior."""
    high_rated = [r for r in all_results if (r.job_fit or 0) >= 4]
    low_rated = [r for r in all_results if (r.job_fit or 0) <= 2]

    high_accuracy = (
        sum(1 for r in high_rated if r.added_to_tracker) / len(high_rated)
        if high_rated else 0.5
    )
    low_accuracy = (
        sum(1 for r in low_rated if not r.added_to_tracker) / len(low_rated)
        if low_rated else 0.5
    )

    return (high_accuracy + low_accuracy) / 2.0


def _update_examples_for_conversation(
    module_name: str, conversation_id: int, score: float, now: datetime
) -> None:
    """Find and update all DspyExample rows for a module+conversation."""
    examples = DspyExample.query.filter_by(module_name=module_name).all()
    updated = 0
    for ex in examples:
        try:
            meta = json.loads(ex.metadata_json) if ex.metadata_json else {}
        except (json.JSONDecodeError, TypeError):
            continue
        if meta.get("conversation_id") == conversation_id:
            ex.score = score
            ex.scored_at = now
            updated += 1

    if updated:
        db.session.commit()
        logger.info("Updated %d %s example(s) for conversation %d with score=%.3f",
                     updated, module_name, conversation_id, score)
