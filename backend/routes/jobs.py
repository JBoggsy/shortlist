import logging
from datetime import date

from flask import Blueprint, jsonify, request

from backend.database import db
from backend.models.job import Job
from backend.models.application_todo import ApplicationTodo

logger = logging.getLogger(__name__)

jobs_bp = Blueprint("jobs", __name__, url_prefix="/api/jobs")


@jobs_bp.route("", methods=["GET"])
def list_jobs():
    jobs = Job.query.order_by(Job.created_at.desc()).all()
    return jsonify([job.to_dict() for job in jobs])


@jobs_bp.route("", methods=["POST"])
def create_job():
    data = request.get_json()
    applied = data.get("applied_date")
    job = Job(
        company=data["company"],
        title=data["title"],
        url=data.get("url"),
        status=data.get("status", "saved"),
        notes=data.get("notes"),
        salary_min=data.get("salary_min"),
        salary_max=data.get("salary_max"),
        location=data.get("location"),
        remote_type=data.get("remote_type"),
        tags=data.get("tags"),
        contact_name=data.get("contact_name"),
        contact_email=data.get("contact_email"),
        applied_date=date.fromisoformat(applied) if applied else None,
        source=data.get("source"),
        job_fit=data.get("job_fit"),
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
    for field in ("company", "title", "url", "status", "notes",
                   "salary_min", "salary_max", "location", "remote_type",
                   "tags", "contact_name", "contact_email", "source",
                   "job_fit"):
        if field in data:
            setattr(job, field, data[field])
    if "applied_date" in data:
        val = data["applied_date"]
        job.applied_date = date.fromisoformat(val) if val else None
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
    if not data or not data.get("title"):
        return jsonify({"error": "title is required"}), 400

    # Determine next sort_order
    max_order = db.session.query(db.func.max(ApplicationTodo.sort_order)).filter_by(job_id=job_id).scalar()
    next_order = (max_order or 0) + 1

    todo = ApplicationTodo(
        job_id=job_id,
        category=data.get("category", "other"),
        title=data["title"],
        description=data.get("description", ""),
        completed=data.get("completed", False),
        sort_order=data.get("sort_order", next_order),
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
    for field in ("category", "title", "description", "sort_order"):
        if field in data:
            setattr(todo, field, data[field])
    if "completed" in data:
        todo.completed = bool(data["completed"])
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


@jobs_bp.route("/<int:job_id>/todos/extract", methods=["POST"])
def extract_todos(job_id):
    """Scrape the job posting URL and extract application todos via LLM."""
    job = db.get_or_404(Job, job_id)
    if not job.url:
        return jsonify({"error": "Job has no URL to scrape"}), 400

    from backend.config_manager import get_search_llm_config, get_integration_config
    from backend.job_enrichment import scrape_url
    from backend.llm.langchain_factory import create_langchain_model
    from backend.todo_extractor import extract_application_todos

    # Get LLM model (use search/cheaper model)
    search_config = get_search_llm_config()
    integration_config = get_integration_config()

    llm_model = None
    if search_config.get("api_key") or search_config.get("provider") == "ollama":
        llm_model = create_langchain_model(
            search_config["provider"],
            search_config.get("api_key", ""),
            search_config.get("model", ""),
        )

    if not llm_model:
        return jsonify({"error": "No LLM configured"}), 503

    # Scrape the job URL
    scraped_text = scrape_url(job.url, integration_config.get("search_api_key", ""))
    if not scraped_text:
        return jsonify({"error": "Failed to scrape job posting URL"}), 502

    # Extract todos
    extracted = extract_application_todos(scraped_text, llm_model)
    if not extracted:
        return jsonify({"todos": [], "message": "No specific application steps found in the posting"}), 200

    # Determine starting sort_order
    max_order = db.session.query(db.func.max(ApplicationTodo.sort_order)).filter_by(job_id=job_id).scalar()
    base_order = (max_order or 0) + 1

    # Save to database
    new_todos = []
    for i, item in enumerate(extracted):
        todo = ApplicationTodo(
            job_id=job_id,
            category=item["category"],
            title=item["title"],
            description=item.get("description", ""),
            sort_order=base_order + i,
        )
        db.session.add(todo)
        new_todos.append(todo)

    db.session.commit()
    logger.info("extract_todos: extracted %d todos for job %d", len(new_todos), job_id)
    return jsonify({"todos": [t.to_dict() for t in new_todos]}), 201
