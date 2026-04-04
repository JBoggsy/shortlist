"""Tests for data safety: atomic writes and log sanitization."""

import json
import os
import tempfile
import threading
from pathlib import Path
from unittest.mock import patch

import pytest

from backend.safe_write import atomic_write, atomic_write_bytes
from backend.log_sanitizer import sanitize, sanitize_error


# ── atomic_write tests ──────────────────────────────────────────────


class TestAtomicWrite:
    """Tests for the atomic_write context manager."""

    def test_basic_text_write(self, tmp_path):
        target = tmp_path / "test.txt"
        with atomic_write(target) as f:
            f.write("hello world")
        assert target.read_text() == "hello world"

    def test_basic_json_write(self, tmp_path):
        target = tmp_path / "config.json"
        data = {"llm": {"provider": "anthropic", "api_key": "sk-ant-test123"}}
        with atomic_write(target) as f:
            json.dump(data, f, indent=2)
        assert json.loads(target.read_text()) == data

    def test_binary_write(self, tmp_path):
        target = tmp_path / "resume.pdf"
        content = b"\x00\x01\x02 binary content"
        atomic_write_bytes(target, content)
        assert target.read_bytes() == content

    def test_preserves_original_on_error(self, tmp_path):
        """If an exception occurs during write, the original file is untouched."""
        target = tmp_path / "config.json"
        target.write_text('{"original": true}')

        with pytest.raises(ValueError, match="deliberate"):
            with atomic_write(target) as f:
                f.write('{"corrupted": ')
                raise ValueError("deliberate error")

        # Original file should be unchanged
        assert json.loads(target.read_text()) == {"original": True}

    def test_creates_parent_directories(self, tmp_path):
        target = tmp_path / "deep" / "nested" / "dir" / "file.txt"
        with atomic_write(target) as f:
            f.write("nested!")
        assert target.read_text() == "nested!"

    def test_no_temp_file_left_on_error(self, tmp_path):
        target = tmp_path / "test.txt"
        with pytest.raises(RuntimeError):
            with atomic_write(target) as f:
                f.write("partial")
                raise RuntimeError("crash")

        # No temp files should remain
        remaining = list(tmp_path.iterdir())
        assert len(remaining) == 0

    def test_no_temp_file_left_on_success(self, tmp_path):
        target = tmp_path / "test.txt"
        with atomic_write(target) as f:
            f.write("complete")

        # Only the target file should exist (no .tmp files)
        remaining = list(tmp_path.iterdir())
        assert remaining == [target]

    def test_overwrites_existing_file(self, tmp_path):
        target = tmp_path / "config.json"
        target.write_text('{"version": 1}')

        with atomic_write(target) as f:
            json.dump({"version": 2}, f)

        assert json.loads(target.read_text()) == {"version": 2}

    def test_encoding_parameter(self, tmp_path):
        target = tmp_path / "profile.md"
        content = "# Résumé\n\nÉducation: Université de Montréal"
        with atomic_write(target, encoding="utf-8") as f:
            f.write(content)
        assert target.read_text(encoding="utf-8") == content

    def test_concurrent_writes_dont_corrupt(self, tmp_path):
        """Simulate concurrent writes — file should contain one complete write."""
        target = tmp_path / "config.json"
        target.write_text('{"original": true}')
        errors = []

        def writer(value):
            try:
                with atomic_write(target) as f:
                    json.dump({"writer": value}, f, indent=2)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=writer, args=(i,)) for i in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        # File should be valid JSON with one of the writers' values
        result = json.loads(target.read_text())
        assert "writer" in result
        assert result["writer"] in range(10)


# ── log_sanitizer tests ─────────────────────────────────────────────


class TestSanitize:
    """Tests for the sanitize() and sanitize_error() functions."""

    def test_anthropic_key(self):
        msg = "AuthenticationError: Invalid API key: sk-ant-api03-abcdef123456789012345678901234567890"
        result = sanitize(msg)
        assert "sk-ant" not in result
        assert "***" in result

    def test_openai_key(self):
        msg = "Error with key sk-proj-abc123def456ghi789jkl012mno345pqr678"
        result = sanitize(msg)
        assert "sk-proj" not in result
        assert "***" in result

    def test_openai_legacy_key(self):
        msg = "Invalid key: sk-abcdef123456789012345678901234567890abcdef1234"
        result = sanitize(msg)
        assert "sk-abcdef" not in result
        assert "***" in result

    def test_gemini_key(self):
        msg = "Failed auth with AIzaSyAbcdefghijklmnopqrstuvwxyz1234567"
        result = sanitize(msg)
        assert "AIza" not in result
        assert "***" in result

    def test_tavily_key(self):
        msg = "Tavily search failed: tvly-abcdef123456789012345678901234567890"
        result = sanitize(msg)
        assert "tvly-" not in result
        assert "***" in result

    def test_hex_rapidapi_key(self):
        msg = "API error with key a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6"
        result = sanitize(msg)
        assert "a1b2c3d4e5f6" not in result

    def test_bearer_token_pattern(self):
        msg = "Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.test1234567890test"
        result = sanitize(msg)
        assert "eyJhbGciOiJIUzI1NiJ9" not in result

    def test_key_value_pattern(self):
        msg = "Request failed with api_key=sk-ant-api03-supersecretkey123456789"
        result = sanitize(msg)
        assert "supersecretkey" not in result

    def test_no_false_positive_on_normal_text(self):
        msg = "Connection refused at localhost:5000"
        assert sanitize(msg) == msg

    def test_no_false_positive_on_short_strings(self):
        msg = "Invalid provider: ollama"
        assert sanitize(msg) == msg

    def test_multiple_keys_in_one_message(self):
        msg = (
            "Failed with primary key sk-ant-api03-abcdef123456789012345678 "
            "and fallback key sk-proj-xyz123456789012345678901234"
        )
        result = sanitize(msg)
        assert "sk-ant" not in result
        assert "sk-proj" not in result
        assert result.count("***") >= 2

    def test_sanitize_error_from_exception(self):
        try:
            raise ValueError("Bad key: sk-ant-api03-abcdef12345678901234567890")
        except ValueError as e:
            result = sanitize_error(e)
            assert "sk-ant" not in result
            assert "***" in result
            assert "Bad key" in result

    def test_empty_string(self):
        assert sanitize("") == ""

    def test_preserves_useful_error_context(self):
        msg = "AuthenticationError: Invalid API key sk-ant-api03-secret1234567890. Please check your credentials."
        result = sanitize(msg)
        assert "AuthenticationError" in result
        assert "Please check your credentials" in result
        assert "sk-ant" not in result


# ── Integration: config_manager uses atomic writes ───────────────────


class TestConfigManagerSafety:
    """Verify config_manager uses atomic writes and sanitized logging."""

    def test_save_config_is_atomic(self, tmp_path, monkeypatch):
        """save_config should write atomically — no partial files on error."""
        monkeypatch.setattr("backend.config_manager.get_data_dir", lambda: tmp_path)
        from backend.config_manager import save_config, load_config

        config = {"llm": {"provider": "openai", "api_key": "test123", "model": ""}}
        assert save_config(config)
        assert load_config() == config

    def test_save_config_preserves_on_error(self, tmp_path, monkeypatch):
        """If atomic write fails, original config should survive."""
        monkeypatch.setattr("backend.config_manager.get_data_dir", lambda: tmp_path)
        from backend.config_manager import save_config, load_config

        original = {"llm": {"provider": "anthropic"}}
        save_config(original)

        # Force an error during write by making directory read-only
        config_file = tmp_path / "config.json"
        assert config_file.exists()

        # Monkey-patch atomic_write to simulate failure
        from backend import config_manager
        original_atomic_write = config_manager.atomic_write

        def failing_write(*args, **kwargs):
            raise IOError("Disk full")

        monkeypatch.setattr(config_manager, "atomic_write", failing_write)
        result = save_config({"llm": {"provider": "broken"}})
        assert result is False

        # Restore and verify original is intact
        monkeypatch.setattr(config_manager, "atomic_write", original_atomic_write)
        loaded = load_config()
        assert loaded == original

    def test_save_config_no_temp_files_remain(self, tmp_path, monkeypatch):
        """After save, no temp files should linger."""
        monkeypatch.setattr("backend.config_manager.get_data_dir", lambda: tmp_path)
        from backend.config_manager import save_config

        save_config({"test": True})
        files = list(tmp_path.iterdir())
        assert len(files) == 1
        assert files[0].name == "config.json"


# ── Integration: user_profile uses atomic writes ─────────────────────


class TestUserProfileSafety:
    """Verify user_profile.py uses atomic writes."""

    def test_write_profile_is_atomic(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.agent.user_profile.get_data_dir", lambda: tmp_path)
        from backend.agent.user_profile import write_profile, read_profile, ensure_profile_exists

        ensure_profile_exists()
        write_profile("# My Profile\n\nTest content")
        content = read_profile()
        assert "Test content" in content

    def test_write_profile_no_temp_files(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.agent.user_profile.get_data_dir", lambda: tmp_path)
        from backend.agent.user_profile import write_profile, ensure_profile_exists

        ensure_profile_exists()
        write_profile("Updated content")

        files = list(tmp_path.iterdir())
        assert all(not f.name.startswith(".") for f in files), \
            f"Temp files remain: {[f.name for f in files]}"

    def test_set_onboarded_is_atomic(self, tmp_path, monkeypatch):
        monkeypatch.setattr("backend.agent.user_profile.get_data_dir", lambda: tmp_path)
        from backend.agent.user_profile import set_onboarded, is_onboarded, ensure_profile_exists

        ensure_profile_exists()
        set_onboarded(True)
        assert is_onboarded()


# ── Integration: API responses don't leak errors ─────────────────────


class _TestConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TESTING = True
    LOG_LEVEL = "WARNING"


class TestAPIResponseSafety:
    """Verify API endpoints return generic errors, not raw exceptions."""

    @pytest.fixture
    def app(self, tmp_path):
        from backend.app import create_app
        from backend.database import db as _db

        with patch("backend.config.get_data_dir", return_value=tmp_path), \
             patch("backend.app.get_data_dir", return_value=tmp_path), \
             patch("backend.app._init_telemetry"), \
             patch("backend.app._apply_migrations"):
            application = create_app(config_class=_TestConfig)
        with application.app_context():
            _db.create_all()
            yield application
            _db.session.remove()
            _db.drop_all()

    @pytest.fixture
    def client(self, app):
        return app.test_client()

    def test_update_config_error_is_generic(self, client, monkeypatch):
        """POST /api/config should not leak internal errors."""
        import backend.routes.config as rc
        original_load = rc.load_config
        monkeypatch.setattr(rc, "load_config", lambda: (_ for _ in ()).throw(
            RuntimeError("secret key sk-ant-api03-leaked12345678901234567890 exposed")
        ))

        resp = client.post("/api/config", json={"llm": {"provider": "test"}})
        data = resp.get_json()
        assert resp.status_code == 500
        assert "sk-ant" not in json.dumps(data)
        assert data["error"] == "Failed to update configuration"

    def test_test_connection_error_is_sanitized(self, client, monkeypatch):
        """POST /api/config/test outer error should not leak keys."""
        import backend.routes.config as rc
        monkeypatch.setattr(rc, "get_llm_config", lambda: (_ for _ in ()).throw(
            RuntimeError("key sk-proj-supersecret12345678901234567890 in error")
        ))

        resp = client.post("/api/config/test", json={})
        data = resp.get_json()
        assert resp.status_code == 500
        assert "sk-proj" not in json.dumps(data)

    def test_list_models_error_is_generic(self, client, monkeypatch):
        """POST /api/config/models should not leak keys in error response."""
        # The inner exception path
        from backend.llm import model_listing
        monkeypatch.setattr(model_listing, "list_models", lambda *a, **kw: (_ for _ in ()).throw(
            RuntimeError("key AIzaSySecret1234567890abcdefghij leaked")
        ))

        resp = client.post("/api/config/models", json={"provider": "gemini", "api_key": "test"})
        data = resp.get_json()
        assert "AIza" not in json.dumps(data)
