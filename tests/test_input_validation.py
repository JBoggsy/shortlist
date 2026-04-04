"""Comprehensive tests for input validation.

Tests cover:
- backend/validation.py (unit tests for validation functions)
- backend/routes/jobs.py (integration tests for job CRUD with validation)
- backend/routes/job_documents.py (integration tests for document save with validation)
- backend/routes/jobs.py todo endpoints (integration tests for todo CRUD with validation)
"""

import json

import pytest

from backend.app import create_app
from backend.database import db as _db
from backend.validation import (
    MAX_LEN_LONG,
    MAX_LEN_MEDIUM,
    MAX_LEN_SHORT,
    MAX_LEN_TEXT,
    MAX_SALARY,
    VALID_DOC_TYPES,
    VALID_REMOTE_TYPES,
    VALID_STATUSES,
    VALID_TODO_CATEGORIES,
    validate_document_data,
    validate_job_data,
    validate_todo_data,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def app():
    """Create a Flask app with an in-memory SQLite database."""
    app = create_app()
    app.config["TESTING"] = True
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///:memory:"
    with app.app_context():
        _db.create_all()
        yield app
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def seed_job(client):
    """Helper that creates a job and returns its dict."""
    resp = client.post(
        "/api/jobs",
        json={"company": "Acme", "title": "Engineer"},
    )
    assert resp.status_code == 201
    return resp.get_json()


# ===================================================================
# UNIT TESTS — validate_job_data
# ===================================================================


class TestValidateJobData:
    """Unit tests for validate_job_data()."""

    def test_valid_minimal(self):
        cleaned, errors = validate_job_data({"company": "Acme", "title": "SWE"})
        assert not errors
        assert cleaned["company"] == "Acme"
        assert cleaned["title"] == "SWE"

    def test_valid_full(self):
        data = {
            "company": "Acme",
            "title": "SWE",
            "url": "https://example.com",
            "status": "applied",
            "notes": "Great company",
            "salary_min": 80000,
            "salary_max": 120000,
            "location": "NYC",
            "remote_type": "hybrid",
            "tags": "python, flask",
            "contact_name": "Jane",
            "contact_email": "jane@acme.com",
            "source": "LinkedIn",
            "job_fit": 4,
            "requirements": "5 years experience",
            "nice_to_haves": "Kubernetes",
        }
        cleaned, errors = validate_job_data(data)
        assert not errors
        for key in data:
            assert cleaned[key] == data[key]

    def test_missing_company(self):
        _, errors = validate_job_data({"title": "SWE"})
        assert any("company" in e for e in errors)

    def test_missing_title(self):
        _, errors = validate_job_data({"company": "Acme"})
        assert any("title" in e for e in errors)

    def test_missing_both_required(self):
        _, errors = validate_job_data({})
        assert len(errors) >= 2

    def test_empty_company_string(self):
        _, errors = validate_job_data({"company": "", "title": "SWE"})
        assert any("company" in e for e in errors)

    def test_whitespace_company(self):
        _, errors = validate_job_data({"company": "   ", "title": "SWE"})
        assert any("company" in e for e in errors)

    def test_patch_mode_no_required_fields(self):
        cleaned, errors = validate_job_data(
            {"salary_min": 50000}, require_company_title=False,
        )
        assert not errors
        assert cleaned["salary_min"] == 50000

    # --- Enum validation ---

    def test_invalid_status(self):
        _, errors = validate_job_data(
            {"company": "A", "title": "B", "status": "nope"},
        )
        assert any("status" in e for e in errors)

    def test_valid_statuses(self):
        for status in VALID_STATUSES:
            cleaned, errors = validate_job_data(
                {"company": "A", "title": "B", "status": status},
            )
            assert not errors
            assert cleaned["status"] == status

    def test_invalid_remote_type(self):
        _, errors = validate_job_data(
            {"company": "A", "title": "B", "remote_type": "everywhere"},
        )
        assert any("remote_type" in e for e in errors)

    def test_valid_remote_types(self):
        for rt in VALID_REMOTE_TYPES:
            cleaned, errors = validate_job_data(
                {"company": "A", "title": "B", "remote_type": rt},
            )
            assert not errors
            assert cleaned["remote_type"] == rt

    def test_null_remote_type_is_ok(self):
        cleaned, errors = validate_job_data(
            {"company": "A", "title": "B", "remote_type": None},
        )
        assert not errors
        assert cleaned["remote_type"] is None

    def test_empty_string_remote_type_coerced_to_none(self):
        cleaned, errors = validate_job_data(
            {"company": "A", "title": "B", "remote_type": ""},
        )
        assert not errors
        assert cleaned["remote_type"] is None

    # --- Integer validation ---

    def test_negative_salary(self):
        _, errors = validate_job_data(
            {"company": "A", "title": "B", "salary_min": -1},
        )
        assert any("salary_min" in e for e in errors)

    def test_salary_string_rejected(self):
        _, errors = validate_job_data(
            {"company": "A", "title": "B", "salary_min": "banana"},
        )
        assert any("salary_min" in e for e in errors)

    def test_salary_float_coerced(self):
        cleaned, errors = validate_job_data(
            {"company": "A", "title": "B", "salary_min": 80000.0},
        )
        assert not errors
        assert cleaned["salary_min"] == 80000

    def test_salary_non_integer_float_rejected(self):
        _, errors = validate_job_data(
            {"company": "A", "title": "B", "salary_min": 80000.5},
        )
        assert any("salary_min" in e for e in errors)

    def test_salary_absurdly_large(self):
        _, errors = validate_job_data(
            {"company": "A", "title": "B", "salary_max": MAX_SALARY + 1},
        )
        assert any("salary_max" in e for e in errors)

    def test_salary_min_exceeds_max(self):
        _, errors = validate_job_data(
            {"company": "A", "title": "B", "salary_min": 120000, "salary_max": 80000},
        )
        assert any("salary_min must not exceed salary_max" in e for e in errors)

    def test_job_fit_out_of_range(self):
        _, errors = validate_job_data(
            {"company": "A", "title": "B", "job_fit": 6},
        )
        assert any("job_fit" in e for e in errors)

    def test_job_fit_negative(self):
        _, errors = validate_job_data(
            {"company": "A", "title": "B", "job_fit": -1},
        )
        assert any("job_fit" in e for e in errors)

    def test_job_fit_valid_range(self):
        for fit in range(6):
            cleaned, errors = validate_job_data(
                {"company": "A", "title": "B", "job_fit": fit},
            )
            assert not errors
            assert cleaned["job_fit"] == fit

    def test_job_fit_null_is_ok(self):
        cleaned, errors = validate_job_data(
            {"company": "A", "title": "B", "job_fit": None},
        )
        assert not errors
        assert cleaned.get("job_fit") is None

    def test_boolean_not_accepted_as_int(self):
        _, errors = validate_job_data(
            {"company": "A", "title": "B", "salary_min": True},
        )
        assert any("salary_min" in e for e in errors)

    # --- String length limits ---

    def test_company_too_long(self):
        _, errors = validate_job_data(
            {"company": "A" * (MAX_LEN_SHORT + 1), "title": "B"},
        )
        assert any("company" in e for e in errors)

    def test_url_too_long(self):
        _, errors = validate_job_data(
            {"company": "A", "title": "B", "url": "x" * (MAX_LEN_MEDIUM + 1)},
        )
        assert any("url" in e for e in errors)

    def test_notes_too_long(self):
        _, errors = validate_job_data(
            {"company": "A", "title": "B", "notes": "x" * (MAX_LEN_LONG + 1)},
        )
        assert any("notes" in e for e in errors)

    def test_requirements_within_text_limit(self):
        cleaned, errors = validate_job_data(
            {"company": "A", "title": "B", "requirements": "x" * MAX_LEN_TEXT},
        )
        assert not errors
        assert len(cleaned["requirements"]) == MAX_LEN_TEXT

    def test_requirements_exceeds_text_limit(self):
        _, errors = validate_job_data(
            {"company": "A", "title": "B", "requirements": "x" * (MAX_LEN_TEXT + 1)},
        )
        assert any("requirements" in e for e in errors)

    # --- None input ---

    def test_none_data(self):
        _, errors = validate_job_data(None)
        assert errors

    # --- Multiple errors aggregated ---

    def test_multiple_errors(self):
        _, errors = validate_job_data({
            "company": "",
            "title": "",
            "salary_min": -5,
            "status": "bogus",
            "remote_type": "bogus",
            "job_fit": 99,
        })
        assert len(errors) >= 4


# ===================================================================
# UNIT TESTS — validate_document_data
# ===================================================================


class TestValidateDocumentData:

    def test_valid(self):
        cleaned, errors = validate_document_data({
            "doc_type": "cover_letter",
            "content": "Dear Hiring Manager...",
        })
        assert not errors
        assert cleaned["doc_type"] == "cover_letter"
        assert cleaned["content"] == "Dear Hiring Manager..."

    def test_invalid_doc_type(self):
        _, errors = validate_document_data({
            "doc_type": "essay",
            "content": "...",
        })
        assert any("doc_type" in e for e in errors)

    def test_missing_doc_type(self):
        _, errors = validate_document_data({"content": "..."})
        assert any("doc_type" in e for e in errors)

    def test_missing_content(self):
        _, errors = validate_document_data({"doc_type": "resume"})
        assert any("content" in e for e in errors)

    def test_content_too_long(self):
        _, errors = validate_document_data({
            "doc_type": "resume",
            "content": "x" * (MAX_LEN_TEXT + 1),
        })
        assert any("content" in e for e in errors)

    def test_valid_doc_types(self):
        for dt in VALID_DOC_TYPES:
            cleaned, errors = validate_document_data({
                "doc_type": dt,
                "content": "text",
            })
            assert not errors
            assert cleaned["doc_type"] == dt

    def test_edit_summary_too_long(self):
        _, errors = validate_document_data({
            "doc_type": "resume",
            "content": "text",
            "edit_summary": "x" * (MAX_LEN_LONG + 1),
        })
        assert any("edit_summary" in e for e in errors)

    def test_none_data(self):
        _, errors = validate_document_data(None)
        assert errors


# ===================================================================
# UNIT TESTS — validate_todo_data
# ===================================================================


class TestValidateTodoData:

    def test_valid_minimal(self):
        cleaned, errors = validate_todo_data({"title": "Write cover letter"})
        assert not errors
        assert cleaned["title"] == "Write cover letter"

    def test_missing_title(self):
        _, errors = validate_todo_data({})
        assert any("title" in e for e in errors)

    def test_invalid_category(self):
        _, errors = validate_todo_data({
            "title": "foo",
            "category": "invalid_category",
        })
        assert any("category" in e for e in errors)

    def test_valid_categories(self):
        for cat in VALID_TODO_CATEGORIES:
            cleaned, errors = validate_todo_data({
                "title": "foo",
                "category": cat,
            })
            assert not errors
            assert cleaned["category"] == cat

    def test_patch_mode_no_required_title(self):
        cleaned, errors = validate_todo_data(
            {"completed": True}, require_title=False,
        )
        assert not errors
        assert cleaned["completed"] is True

    def test_none_data(self):
        _, errors = validate_todo_data(None)
        assert errors


# ===================================================================
# INTEGRATION TESTS — Job Routes
# ===================================================================


class TestJobRoutesValidation:
    """Tests that the job API endpoints properly validate input."""

    def test_create_valid_job(self, client):
        resp = client.post(
            "/api/jobs",
            json={"company": "Acme", "title": "SWE"},
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["company"] == "Acme"
        assert data["status"] == "saved"

    def test_create_missing_company(self, client):
        resp = client.post("/api/jobs", json={"title": "SWE"})
        assert resp.status_code == 400
        assert "company" in resp.get_json()["error"]

    def test_create_missing_title(self, client):
        resp = client.post("/api/jobs", json={"company": "Acme"})
        assert resp.status_code == 400
        assert "title" in resp.get_json()["error"]

    def test_create_invalid_status(self, client):
        resp = client.post(
            "/api/jobs",
            json={"company": "A", "title": "B", "status": "bogus"},
        )
        assert resp.status_code == 400
        assert "status" in resp.get_json()["error"]

    def test_create_invalid_remote_type(self, client):
        resp = client.post(
            "/api/jobs",
            json={"company": "A", "title": "B", "remote_type": "everywhere"},
        )
        assert resp.status_code == 400
        assert "remote_type" in resp.get_json()["error"]

    def test_create_negative_salary(self, client):
        resp = client.post(
            "/api/jobs",
            json={"company": "A", "title": "B", "salary_min": -1},
        )
        assert resp.status_code == 400
        assert "salary_min" in resp.get_json()["error"]

    def test_create_string_salary(self, client):
        resp = client.post(
            "/api/jobs",
            json={"company": "A", "title": "B", "salary_min": "banana"},
        )
        assert resp.status_code == 400

    def test_create_job_fit_out_of_range(self, client):
        resp = client.post(
            "/api/jobs",
            json={"company": "A", "title": "B", "job_fit": 10},
        )
        assert resp.status_code == 400
        assert "job_fit" in resp.get_json()["error"]

    def test_create_salary_min_exceeds_max(self, client):
        resp = client.post(
            "/api/jobs",
            json={"company": "A", "title": "B", "salary_min": 200000, "salary_max": 100000},
        )
        assert resp.status_code == 400
        assert "salary_min must not exceed salary_max" in resp.get_json()["error"]

    def test_create_oversized_company(self, client):
        resp = client.post(
            "/api/jobs",
            json={"company": "X" * 300, "title": "B"},
        )
        assert resp.status_code == 400

    def test_create_invalid_applied_date(self, client):
        resp = client.post(
            "/api/jobs",
            json={"company": "A", "title": "B", "applied_date": "not-a-date"},
        )
        assert resp.status_code == 400
        assert "applied_date" in resp.get_json()["error"]

    def test_create_with_all_valid_fields(self, client):
        resp = client.post(
            "/api/jobs",
            json={
                "company": "BigCorp",
                "title": "Staff Engineer",
                "url": "https://jobs.bigcorp.com/123",
                "status": "applied",
                "salary_min": 150000,
                "salary_max": 250000,
                "location": "San Francisco",
                "remote_type": "hybrid",
                "job_fit": 5,
                "tags": "python, leadership",
                "applied_date": "2025-01-15",
            },
        )
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["salary_min"] == 150000
        assert data["status"] == "applied"
        assert data["remote_type"] == "hybrid"
        assert data["job_fit"] == 5

    # --- PATCH ---

    def test_patch_invalid_status(self, client, seed_job):
        resp = client.patch(
            f"/api/jobs/{seed_job['id']}",
            json={"status": "nope"},
        )
        assert resp.status_code == 400

    def test_patch_invalid_salary(self, client, seed_job):
        resp = client.patch(
            f"/api/jobs/{seed_job['id']}",
            json={"salary_min": -100},
        )
        assert resp.status_code == 400

    def test_patch_valid_update(self, client, seed_job):
        resp = client.patch(
            f"/api/jobs/{seed_job['id']}",
            json={"status": "interviewing", "salary_min": 100000},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "interviewing"
        assert data["salary_min"] == 100000

    def test_patch_job_fit_valid(self, client, seed_job):
        resp = client.patch(
            f"/api/jobs/{seed_job['id']}",
            json={"job_fit": 3},
        )
        assert resp.status_code == 200
        assert resp.get_json()["job_fit"] == 3

    def test_patch_job_fit_out_of_range(self, client, seed_job):
        resp = client.patch(
            f"/api/jobs/{seed_job['id']}",
            json={"job_fit": 999},
        )
        assert resp.status_code == 400


# ===================================================================
# INTEGRATION TESTS — Document Routes
# ===================================================================


class TestDocumentRoutesValidation:

    def test_save_valid_document(self, client, seed_job):
        resp = client.post(
            f"/api/jobs/{seed_job['id']}/documents",
            json={"doc_type": "cover_letter", "content": "Dear Hiring Manager..."},
        )
        assert resp.status_code == 201
        assert resp.get_json()["doc_type"] == "cover_letter"

    def test_save_invalid_doc_type(self, client, seed_job):
        resp = client.post(
            f"/api/jobs/{seed_job['id']}/documents",
            json={"doc_type": "essay", "content": "Hello"},
        )
        assert resp.status_code == 400
        assert "doc_type" in resp.get_json()["error"]

    def test_save_missing_content(self, client, seed_job):
        resp = client.post(
            f"/api/jobs/{seed_job['id']}/documents",
            json={"doc_type": "resume"},
        )
        assert resp.status_code == 400
        assert "content" in resp.get_json()["error"]

    def test_get_invalid_doc_type_query_param(self, client, seed_job):
        resp = client.get(
            f"/api/jobs/{seed_job['id']}/documents?type=essay",
        )
        assert resp.status_code == 400
        assert "type" in resp.get_json()["error"]

    def test_get_history_invalid_doc_type(self, client, seed_job):
        resp = client.get(
            f"/api/jobs/{seed_job['id']}/documents/history?type=essay",
        )
        assert resp.status_code == 400

    def test_save_resume(self, client, seed_job):
        resp = client.post(
            f"/api/jobs/{seed_job['id']}/documents",
            json={"doc_type": "resume", "content": "# My Resume\n..."},
        )
        assert resp.status_code == 201
        assert resp.get_json()["doc_type"] == "resume"


# ===================================================================
# INTEGRATION TESTS — Todo Routes
# ===================================================================


class TestTodoRoutesValidation:

    def test_create_valid_todo(self, client, seed_job):
        resp = client.post(
            f"/api/jobs/{seed_job['id']}/todos",
            json={"title": "Write cover letter"},
        )
        assert resp.status_code == 201
        assert resp.get_json()["title"] == "Write cover letter"
        assert resp.get_json()["category"] == "other"

    def test_create_missing_title(self, client, seed_job):
        resp = client.post(
            f"/api/jobs/{seed_job['id']}/todos",
            json={},
        )
        assert resp.status_code == 400
        assert "title" in resp.get_json()["error"]

    def test_create_invalid_category(self, client, seed_job):
        resp = client.post(
            f"/api/jobs/{seed_job['id']}/todos",
            json={"title": "foo", "category": "bogus"},
        )
        assert resp.status_code == 400
        assert "category" in resp.get_json()["error"]

    def test_create_valid_category(self, client, seed_job):
        resp = client.post(
            f"/api/jobs/{seed_job['id']}/todos",
            json={"title": "Prep questions", "category": "question"},
        )
        assert resp.status_code == 201
        assert resp.get_json()["category"] == "question"

    def test_patch_invalid_category(self, client, seed_job):
        # Create a todo first
        create_resp = client.post(
            f"/api/jobs/{seed_job['id']}/todos",
            json={"title": "Test"},
        )
        todo_id = create_resp.get_json()["id"]

        resp = client.patch(
            f"/api/jobs/{seed_job['id']}/todos/{todo_id}",
            json={"category": "invalid"},
        )
        assert resp.status_code == 400

    def test_patch_valid_update(self, client, seed_job):
        create_resp = client.post(
            f"/api/jobs/{seed_job['id']}/todos",
            json={"title": "Test"},
        )
        todo_id = create_resp.get_json()["id"]

        resp = client.patch(
            f"/api/jobs/{seed_job['id']}/todos/{todo_id}",
            json={"completed": True, "category": "document"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["completed"] is True
        assert data["category"] == "document"
