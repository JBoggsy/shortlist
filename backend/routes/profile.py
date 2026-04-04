import logging

from flask import Blueprint, request

from backend.agent.user_profile import (
    read_profile,
    read_profile_raw,
    write_profile,
    ensure_profile_exists,
    is_onboarded,
    set_onboarded,
    get_onboarding_state,
    set_onboarding_in_progress,
)

logger = logging.getLogger(__name__)

profile_bp = Blueprint("profile", __name__, url_prefix="/api/profile")


@profile_bp.route("", methods=["GET"])
def get_profile():
    try:
        ensure_profile_exists()
        content = read_profile()
        return {"content": content}
    except OSError:
        logger.exception("Failed to read user profile")
        return {"error": "Failed to read user profile"}, 500


@profile_bp.route("", methods=["PUT"])
def update_profile():
    data = request.get_json()
    if not data or "content" not in data:
        return {"error": "content is required"}, 400
    try:
        write_profile(data["content"])
        return {"content": read_profile()}
    except OSError:
        logger.exception("Failed to write user profile")
        return {"error": "Failed to save user profile"}, 500


@profile_bp.route("/onboarding-status", methods=["GET"])
def onboarding_status():
    try:
        ensure_profile_exists()
        return {"onboarded": is_onboarded(), "onboarding_state": get_onboarding_state()}
    except OSError:
        logger.exception("Failed to read onboarding status")
        return {"error": "Failed to read onboarding status"}, 500


@profile_bp.route("/onboarding-status", methods=["POST"])
def update_onboarding_status():
    try:
        data = request.get_json()
        if data and "onboarded" in data:
            set_onboarded(bool(data["onboarded"]))
        return {"onboarded": is_onboarded(), "onboarding_state": get_onboarding_state()}
    except OSError:
        logger.exception("Failed to update onboarding status")
        return {"error": "Failed to update onboarding status"}, 500
