"""Tests for backend error handling.

Covers the four fixes from the 'Backend Error Handling' must-fix todo:
1. Global Flask error handlers (JSON instead of HTML)
2. Profile route try/except for file I/O failures
3. Chat streaming generator protection (SSE error events)
4. Jobs POST required-field validation
"""

import json
from unittest.mock import patch

import pytest

from backend.app import create_app
from backend.database import db as _db


class TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    LOG_LEVEL = "WARNING"


@pytest.fixture()
def app(tmp_path):
    """Create a Flask test app with an in-memory database."""
    with patch("backend.config.get_data_dir", return_value=tmp_path), \
         patch("backend.app.get_data_dir", return_value=tmp_path), \
         patch("backend.app._init_telemetry"):
        application = create_app(config_class=TestConfig)
    with application.app_context():
        _db.create_all()
        yield application
        _db.session.remove()
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


# ────────────────────────────────────────────────────────────────────
# 1. Global Flask error handlers
# ────────────────────────────────────────────────────────────────────

class TestGlobalErrorHandlers:
    """Global error handlers return JSON, never HTML."""

    def test_404_returns_json(self, client):
        resp = client.get("/api/nonexistent-route")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data is not None
        assert "error" in data

    def test_405_returns_json(self, client):
        # GET /api/jobs exists, but DELETE /api/jobs does not
        resp = client.delete("/api/jobs")
        assert resp.status_code == 405
        data = resp.get_json()
        assert data is not None
        assert "error" in data

    def test_500_returns_json(self, client, app):
        """An unhandled exception in a route returns JSON 500."""
        @app.route("/api/_test_500")
        def blow_up():
            raise RuntimeError("kaboom")

        resp = client.get("/api/_test_500")
        assert resp.status_code == 500
        data = resp.get_json()
        assert data is not None
        assert data["error"] == "Internal server error"


# ────────────────────────────────────────────────────────────────────
# 2. Profile route error handling
# ────────────────────────────────────────────────────────────────────

class TestProfileErrorHandling:
    """Profile routes return JSON errors on file I/O failures."""

    def test_get_profile_io_error(self, client):
        with patch("backend.routes.profile.ensure_profile_exists", side_effect=OSError("disk full")):
            resp = client.get("/api/profile")
        assert resp.status_code == 500
        data = resp.get_json()
        assert "error" in data
        assert "profile" in data["error"].lower()

    def test_update_profile_io_error(self, client):
        with patch("backend.routes.profile.write_profile", side_effect=OSError("permission denied")):
            resp = client.put(
                "/api/profile",
                json={"content": "test content"},
            )
        assert resp.status_code == 500
        data = resp.get_json()
        assert "error" in data

    def test_update_profile_missing_content(self, client):
        resp = client.put("/api/profile", json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "content" in data["error"]

    def test_onboarding_status_io_error(self, client):
        with patch("backend.routes.profile.ensure_profile_exists", side_effect=OSError("fail")):
            resp = client.get("/api/profile/onboarding-status")
        assert resp.status_code == 500
        data = resp.get_json()
        assert "error" in data

    def test_update_onboarding_status_io_error(self, client):
        with patch("backend.routes.profile.set_onboarded", side_effect=OSError("fail")):
            resp = client.post(
                "/api/profile/onboarding-status",
                json={"onboarded": True},
            )
        assert resp.status_code == 500
        data = resp.get_json()
        assert "error" in data


# ────────────────────────────────────────────────────────────────────
# 3. Chat streaming generator protection
# ────────────────────────────────────────────────────────────────────

def _parse_sse(response_data: bytes) -> list[dict]:
    """Parse SSE response bytes into a list of {event, data} dicts."""
    events = []
    text = response_data.decode("utf-8")
    current_event = None
    current_data = None
    for line in text.split("\n"):
        if line.startswith("event: "):
            current_event = line[7:]
        elif line.startswith("data: "):
            current_data = line[6:]
        elif line == "" and current_event is not None:
            events.append({"event": current_event, "data": json.loads(current_data)})
            current_event = None
            current_data = None
    return events


class TestChatStreamingProtection:
    """Generators emit an SSE error event if the agent throws mid-stream."""

    def _create_conversation(self, client):
        resp = client.post("/api/chat/conversations", json={"title": "Test"})
        return resp.get_json()["id"]

    def test_agent_error_yields_sse_error(self, client):
        convo_id = self._create_conversation(client)

        def failing_agent_run(self_agent, messages):
            yield {"event": "text_delta", "data": {"content": "partial "}}
            raise RuntimeError("LLM connection lost")

        with patch("backend.routes.chat.get_active_mode_llm_config", return_value={
            "provider": "openai", "api_key": "test-key", "model": "gpt-4",
        }), patch("backend.routes.chat.get_integration_config", return_value={
            "search_api_key": "", "rapidapi_key": "",
        }), patch("backend.routes.chat.create_llm_config") as mock_llm, \
             patch("backend.routes.chat.get_agent_classes") as mock_classes:

            mock_agent = type("MockAgent", (), {"run": failing_agent_run})()
            mock_classes.return_value = (lambda *a, **kw: mock_agent, None, None)

            resp = client.post(
                f"/api/chat/conversations/{convo_id}/messages",
                json={"content": "hello"},
            )
            assert resp.status_code == 200
            events = _parse_sse(resp.data)

            # Should have received partial text, then an error event
            event_types = [e["event"] for e in events]
            assert "text_delta" in event_types
            assert "error" in event_types
            error_event = next(e for e in events if e["event"] == "error")
            assert "message" in error_event["data"]


# ────────────────────────────────────────────────────────────────────
# 4. Jobs POST validation
# ────────────────────────────────────────────────────────────────────

class TestJobsPostValidation:
    """POST /api/jobs validates required fields and returns JSON 400."""

    def test_missing_body(self, client):
        resp = client.post(
            "/api/jobs",
            data="not json",
            content_type="application/json",
        )
        # Flask may return 400 for malformed JSON, or our handler catches None
        assert resp.status_code == 400

    def test_empty_body(self, client):
        resp = client.post("/api/jobs", json={})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "company" in data["error"]

    def test_missing_company(self, client):
        resp = client.post("/api/jobs", json={"title": "Engineer"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "company" in data["error"]

    def test_missing_title(self, client):
        resp = client.post("/api/jobs", json={"company": "Acme"})
        assert resp.status_code == 400
        data = resp.get_json()
        assert "title" in data["error"]

    def test_empty_string_company(self, client):
        resp = client.post("/api/jobs", json={"company": "", "title": "Engineer"})
        assert resp.status_code == 400

    def test_whitespace_only_company(self, client):
        resp = client.post("/api/jobs", json={"company": "   ", "title": "Engineer"})
        assert resp.status_code == 400

    def test_invalid_applied_date_post(self, client):
        resp = client.post("/api/jobs", json={
            "company": "Acme",
            "title": "Engineer",
            "applied_date": "not-a-date",
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert "applied_date" in data["error"]

    def test_invalid_applied_date_patch(self, client):
        # First, create a valid job
        create_resp = client.post("/api/jobs", json={
            "company": "Acme",
            "title": "Engineer",
        })
        assert create_resp.status_code == 201
        job_id = create_resp.get_json()["id"]

        resp = client.patch(f"/api/jobs/{job_id}", json={
            "applied_date": "2025-13-45",
        })
        assert resp.status_code == 400
        data = resp.get_json()
        assert "applied_date" in data["error"]

    def test_valid_job_creation(self, client):
        resp = client.post("/api/jobs", json={
            "company": "Acme Corp",
            "title": "Software Engineer",
            "applied_date": "2025-03-15",
        })
        assert resp.status_code == 201
        data = resp.get_json()
        assert data["company"] == "Acme Corp"
        assert data["title"] == "Software Engineer"
        assert data["applied_date"] == "2025-03-15"

    def test_valid_job_with_null_applied_date(self, client):
        resp = client.post("/api/jobs", json={
            "company": "Acme Corp",
            "title": "Engineer",
        })
        assert resp.status_code == 201
        assert resp.get_json()["applied_date"] is None

    def test_get_nonexistent_job_returns_json_404(self, client):
        """db.get_or_404 should return JSON 404, not HTML."""
        resp = client.get("/api/jobs/99999")
        assert resp.status_code == 404
        data = resp.get_json()
        assert data is not None
        assert "error" in data
