import logging
from datetime import date

from flask import Blueprint, jsonify, request

from backend.database import db
from backend.models.job import Job
from backend.models.application_todo import ApplicationTodo
from backend.validation import validate_job_data, validate_todo_data

logger = logging.getLogger(__name__)

jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")

# Fields that validation may return for a Job record
_JOB_FIELDS = (
    "company", "title", "url", "status", "notes",
    "salary_min", "salary_max", "location", "remote_type",
    "tags", "contact_name", "contact_email", "source",
    "job_fit", "requirements", "nice_to_haves",
)


@jobs_bp.route("", methods=["GET"])
def list_jobs():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return jsonify([job.to_dict() for job in jobs])


@jobs_bp.route("", methods=["POST"])
def create_job():
    data = request.get_json()
    cleaned, errors = validate_job_data(data, require_company_title=True)
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    applied = cleaned.get("applied_date")
    try:
        applied_date = date.fromisoformat(applied) if applied else None
    except (ValueError, TypeError):
        return jsonify({"error": "applied_date must be a valid ISO date (YYYY-MM-DD)"}), 400

    job = Job(
        company=cleaned.get("company"),
        title=cleaned.get("title"),
        url=cleaned.get("url"),
        status=cleaned.get("status") or "saved",
        notes=cleaned.get("notes"),
        salary_min=cleaned.get("salary_min"),
        salary_max=cleaned.get("salary_max"),
        location=cleaned.get("location"),
        remote_type=cleaned.get("remote_type"),
        tags=cleaned.get("tags"),
        contact_name=cleaned.get("contact_name"),
        contact_email=cleaned.get("contact_email"),
        applied_date=applied_date,
        source=cleaned.get("source"),
        job_fit=cleaned.get("job_fit"),
        requirements=cleaned.get("requirements"),
        nice_to_haves=cleaned.get("nice_to_haves"),
    )
    db.session.add(job)
    db.session.commit()
    return jsonify(job.to_dict()), 201


@jobs_bp.route("/<int:job_id>", methods=["GET"])
def get_job(job_id):
    job = db.get_or_404(Job, job_id)
    return jsonify(job.to_dict())


@jobs_bp.route("/<int:job_id>", methods=["PATCH"])
def update_job(job_id):
    job = db.get_or_404(Job, job_id)
    data = request.get_json()
    cleaned, errors = validate_job_data(data, require_company_title=False)
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    for field in _JOB_FIELDS:
        if field in cleaned:
            setattr(job, field, cleaned[field])
    if "applied_date" in cleaned:
        val = cleaned["applied_date"]
        try:
            job.applied_date = date.fromisoformat(val) if val else None
        except (ValueError, TypeError):
            return jsonify({"error": "applied_date must be a valid ISO date (YYYY-MM-DD)"}), 400
    db.session.commit()
    return jsonify(job.to_dict())


@jobs_bp.route("/<int:job_id>", methods=["DELETE"])
def delete_job(job_id):
    job = db.get_or_404(Job, job_id)
    db.session.delete(job)
    db.session.commit()
    return "", 204


# ---------------------------------------------------------------------------
# Application Todos (nested under /api/jobs/<job_id>/todos)
# ---------------------------------------------------------------------------


@jobs_bp.route("/<int:job_id>/todos", methods=["GET"])
def list_todos(job_id):
    db.get_or_404(Job, job_id)
    todos = (ApplicationTodo.query
             .filter_by(job_id=job_id)
             .order_by(ApplicationTodo.sort_order, ApplicationTodo.id)
             .all())
    return jsonify([t.to_dict() for t in todos])


@jobs_bp.route("/<int:job_id>/todos", methods=["POST"])
def create_todo(job_id):
    db.get_or_404(Job, job_id)
    data = request.get_json()
    cleaned, errors = validate_todo_data(data, require_title=True)
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    # Determine next sort_order
    max_order = db.session.query(db.func.max(ApplicationTodo.sort_order)).filter_by(job_id=job_id).scalar()
    next_order = (max_order or 0) + 1

    todo = ApplicationTodo(
        job_id=job_id,
        category=cleaned.get("category") or "other",
        title=cleaned["title"],
        description=cleaned.get("description", ""),
        completed=cleaned.get("completed", False),
        sort_order=cleaned.get("sort_order", next_order),
    )
    db.session.add(todo)
    db.session.commit()
    return jsonify(todo.to_dict()), 201


@jobs_bp.route("/<int:job_id>/todos/<int:todo_id>", methods=["PATCH"])
def update_todo(job_id, todo_id):
    db.get_or_404(Job, job_id)
    todo = db.get_or_404(ApplicationTodo, todo_id)
    if todo.job_id != job_id:
        return jsonify({"error": "Todo does not belong to this job"}), 404

    data = request.get_json()
    cleaned, errors = validate_todo_data(data, require_title=False)
    if errors:
        return jsonify({"error": "; ".join(errors)}), 400

    for field in ("category", "title", "description", "sort_order"):
        if field in cleaned:
            setattr(todo, field, cleaned[field])
    if "completed" in cleaned:
        todo.completed = cleaned["completed"]
    db.session.commit()
    return jsonify(todo.to_dict())


@jobs_bp.route("/<int:job_id>/todos/<int:todo_id>", methods=["DELETE"])
def delete_todo(job_id, todo_id):
    db.get_or_404(Job, job_id)
    todo = db.get_or_404(ApplicationTodo, todo_id)
    if todo.job_id != job_id:
        return jsonify({"error": "Todo does not belong to this job"}), 404
    db.session.delete(todo)
    db.session.commit()
    return "", 204
