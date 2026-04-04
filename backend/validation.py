"""Centralized input validation for HTTP API routes.

Provides reusable validation functions and constants shared across route
handlers and agent tools.  Each ``validate_*`` function accepts raw
request data and returns ``(cleaned_data, errors)`` where *errors* is a
list of human-readable strings (empty on success).
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Valid enum values
# ---------------------------------------------------------------------------

VALID_STATUSES = {"saved", "applied", "interviewing", "offer", "rejected"}
VALID_REMOTE_TYPES = {"onsite", "hybrid", "remote"}
VALID_DOC_TYPES = {"cover_letter", "resume"}
VALID_TODO_CATEGORIES = {"document", "question", "assessment", "reference", "other"}

# ---------------------------------------------------------------------------
# String length limits (bytes are close enough to chars for our purposes)
# ---------------------------------------------------------------------------

MAX_LEN_SHORT = 200       # company, title, location, contact_name, contact_email, source
MAX_LEN_MEDIUM = 500      # url, tags
MAX_LEN_LONG = 5_000      # notes, fit_reason, edit_summary
MAX_LEN_TEXT = 100_000     # requirements, nice_to_haves, description, document content

# Maximum reasonable salary value (~$100 billion — accommodates any currency)
MAX_SALARY = 100_000_000_000

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _validate_string(value, field_name: str, max_length: int, errors: list) -> str | None:
    """Validate a string field: must be str (or None), within length limit."""
    if value is None:
        return None
    if not isinstance(value, str):
        errors.append(f"{field_name} must be a string")
        return None
    if len(value) > max_length:
        errors.append(f"{field_name} must be at most {max_length} characters")
        return None
    return value


def _validate_enum(value, field_name: str, valid_values: set, errors: list) -> str | None:
    """Validate that a value is one of the allowed enum strings (or None)."""
    if value is None or value == "":
        return None
    if not isinstance(value, str):
        errors.append(f"{field_name} must be a string")
        return None
    if value not in valid_values:
        errors.append(
            f"Invalid {field_name} '{value}'. "
            f"Must be one of: {', '.join(sorted(valid_values))}"
        )
        return None
    return value


def _validate_int(value, field_name: str, min_val: int | None, max_val: int | None, errors: list) -> int | None:
    """Validate an integer field: coerce from float/str if reasonable."""
    if value is None or value == "":
        return None

    # Coerce numeric types
    if isinstance(value, float):
        if not value.is_integer():
            errors.append(f"{field_name} must be a whole number")
            return None
        value = int(value)
    elif isinstance(value, str):
        try:
            value = int(value)
        except (ValueError, OverflowError):
            errors.append(f"{field_name} must be an integer")
            return None
    elif isinstance(value, bool):
        # bool is a subclass of int in Python — reject it
        errors.append(f"{field_name} must be an integer")
        return None

    if not isinstance(value, int):
        errors.append(f"{field_name} must be an integer")
        return None

    if min_val is not None and value < min_val:
        errors.append(f"{field_name} must be at least {min_val}")
        return None
    if max_val is not None and value > max_val:
        errors.append(f"{field_name} must be at most {max_val}")
        return None

    return value


# ---------------------------------------------------------------------------
# Job validation
# ---------------------------------------------------------------------------

# Map field names → (max_length,) for short/medium/long string fields on Job
_JOB_STRING_LIMITS: dict[str, int] = {
    "company": MAX_LEN_SHORT,
    "title": MAX_LEN_SHORT,
    "url": MAX_LEN_MEDIUM,
    "notes": MAX_LEN_LONG,
    "location": MAX_LEN_SHORT,
    "tags": MAX_LEN_MEDIUM,
    "contact_name": MAX_LEN_SHORT,
    "contact_email": MAX_LEN_SHORT,
    "source": MAX_LEN_SHORT,
    "requirements": MAX_LEN_TEXT,
    "nice_to_haves": MAX_LEN_TEXT,
}


def validate_job_data(
    data: dict,
    *,
    require_company_title: bool = True,
) -> tuple[dict, list[str]]:
    """Validate and clean job data from an HTTP request.

    Parameters
    ----------
    data : dict
        Raw request JSON.
    require_company_title : bool
        If True (default), ``company`` and ``title`` are mandatory.
        Set to False for PATCH updates.

    Returns
    -------
    (cleaned, errors) where *cleaned* contains only validated fields
    present in *data*, and *errors* is empty on success.
    """
    errors: list[str] = []
    cleaned: dict = {}

    if data is None:
        return cleaned, ["Request body is required"]

    # --- Required fields ------------------------------------------------
    if require_company_title:
        company = data.get("company")
        title = data.get("title")
        if not company or not isinstance(company, str) or not company.strip():
            errors.append("company is required")
        if not title or not isinstance(title, str) or not title.strip():
            errors.append("title is required")

    # --- String fields --------------------------------------------------
    for field, max_len in _JOB_STRING_LIMITS.items():
        if field in data:
            cleaned[field] = _validate_string(data[field], field, max_len, errors)

    # --- Enum fields ----------------------------------------------------
    if "status" in data:
        cleaned["status"] = _validate_enum(data["status"], "status", VALID_STATUSES, errors)

    if "remote_type" in data:
        cleaned["remote_type"] = _validate_enum(data["remote_type"], "remote_type", VALID_REMOTE_TYPES, errors)

    # --- Integer fields -------------------------------------------------
    if "salary_min" in data:
        cleaned["salary_min"] = _validate_int(data["salary_min"], "salary_min", 0, MAX_SALARY, errors)

    if "salary_max" in data:
        cleaned["salary_max"] = _validate_int(data["salary_max"], "salary_max", 0, MAX_SALARY, errors)

    if "job_fit" in data:
        cleaned["job_fit"] = _validate_int(data["job_fit"], "job_fit", 0, 5, errors)

    # --- Cross-field: salary_min <= salary_max --------------------------
    s_min = cleaned.get("salary_min")
    s_max = cleaned.get("salary_max")
    if s_min is not None and s_max is not None and s_min > s_max:
        errors.append("salary_min must not exceed salary_max")

    # --- applied_date (pass through; fromisoformat handles validation) --
    if "applied_date" in data:
        cleaned["applied_date"] = data["applied_date"]

    return cleaned, errors


# ---------------------------------------------------------------------------
# Document validation
# ---------------------------------------------------------------------------


def validate_document_data(data: dict) -> tuple[dict, list[str]]:
    """Validate document save data.

    Returns
    -------
    (cleaned, errors)
    """
    errors: list[str] = []
    cleaned: dict = {}

    if data is None:
        return cleaned, ["Request body is required"]

    # doc_type (required, constrained)
    doc_type = data.get("doc_type")
    if not doc_type:
        errors.append("doc_type is required")
    else:
        val = _validate_enum(doc_type, "doc_type", VALID_DOC_TYPES, errors)
        if val:
            cleaned["doc_type"] = val

    # content (required, length-limited)
    content = data.get("content")
    if not content:
        errors.append("content is required")
    else:
        val = _validate_string(content, "content", MAX_LEN_TEXT, errors)
        if val:
            cleaned["content"] = val

    # edit_summary (optional)
    if "edit_summary" in data:
        cleaned["edit_summary"] = _validate_string(
            data["edit_summary"], "edit_summary", MAX_LEN_LONG, errors,
        )

    return cleaned, errors


# ---------------------------------------------------------------------------
# Todo validation
# ---------------------------------------------------------------------------


def validate_todo_data(
    data: dict,
    *,
    require_title: bool = True,
) -> tuple[dict, list[str]]:
    """Validate application todo data.

    Returns
    -------
    (cleaned, errors)
    """
    errors: list[str] = []
    cleaned: dict = {}

    if data is None:
        return cleaned, ["Request body is required"]

    # title
    if require_title:
        title = data.get("title")
        if not title or not isinstance(title, str) or not title.strip():
            errors.append("title is required")

    if "title" in data:
        cleaned["title"] = _validate_string(data["title"], "title", MAX_LEN_MEDIUM, errors)

    # category
    if "category" in data:
        cleaned["category"] = _validate_enum(
            data["category"], "category", VALID_TODO_CATEGORIES, errors,
        )

    # description
    if "description" in data:
        cleaned["description"] = _validate_string(
            data["description"], "description", MAX_LEN_LONG, errors,
        )

    # completed (bool)
    if "completed" in data:
        cleaned["completed"] = bool(data["completed"])

    # sort_order (int)
    if "sort_order" in data:
        cleaned["sort_order"] = _validate_int(
            data["sort_order"], "sort_order", 0, 10_000, errors,
        )

    return cleaned, errors
