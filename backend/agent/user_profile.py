"""User profile management — reads and writes a markdown file that stores
information about the user relevant to their job search.

The file uses YAML frontmatter to store metadata (e.g. onboarding status)."""

import os
import re

from backend.data_dir import get_data_dir

# Canonical placeholder used for every unfilled profile section.
# All template defaults and detection logic reference this single constant.
SECTION_PLACEHOLDER = "_Not yet provided_"

DEFAULT_PROFILE_TEMPLATE = f"""---
onboarded: false
---
# User Profile

## Summary
{SECTION_PLACEHOLDER}

## Education
{SECTION_PLACEHOLDER}

## Work Experience
{SECTION_PLACEHOLDER}

## Skills & Expertise
{SECTION_PLACEHOLDER}

## Fields of Interest
{SECTION_PLACEHOLDER}

## Salary Preferences
{SECTION_PLACEHOLDER}

## Location Preferences
{SECTION_PLACEHOLDER}

## Remote Work Preferences
{SECTION_PLACEHOLDER}

## Job Search Goals
{SECTION_PLACEHOLDER}

## Other Notes
{SECTION_PLACEHOLDER}
"""

_FRONTMATTER_RE = re.compile(r"^---\n(.*?)\n---\n", re.DOTALL)

PROFILE_SECTIONS = [
    "Summary",
    "Education",
    "Work Experience",
    "Skills & Expertise",
    "Fields of Interest",
    "Salary Preferences",
    "Location Preferences",
    "Remote Work Preferences",
    "Job Search Goals",
    "Other Notes",
]


# Legacy placeholder strings from older profile templates.  Kept here so
# ``is_section_unfilled`` recognises profiles created before the canonical
# placeholder was standardised.
_LEGACY_PLACEHOLDERS = frozenset({
    "no summary yet",
    "no summary yet. the ai assistant will fill this in as it learns about you.",
    "none yet",
})


def is_section_unfilled(content: str) -> bool:
    """Return True if *content* is empty or matches the canonical placeholder.

    Strips leading markdown list markers (``- ``), whitespace, and
    underscore emphasis before comparing so that both ``_Not yet provided_``
    and ``- _Not yet provided_`` are detected.  Also recognises legacy
    placeholder strings from older profile templates.
    """
    if not content:
        return True
    stripped = content.strip().lstrip("- ").strip().strip("_").strip()
    normalised = stripped.lower()
    placeholder_core = SECTION_PLACEHOLDER.strip("_").strip().lower()
    if normalised == placeholder_core:
        return True
    return normalised in _LEGACY_PLACEHOLDERS

_SECTION_RE_TEMPLATE = r"^## {name}\n(.*?)(?=^## |\Z)"
_SECTION_HEADER_RE = re.compile(r"^## .+$", re.MULTILINE)


def get_profile_path() -> str:
    """Return the absolute path to the user profile markdown file."""
    return str(get_data_dir() / "user_profile.md")


def _parse_frontmatter(text: str) -> tuple[dict, str]:
    """Split *text* into a frontmatter dict and body string."""
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return {}, text
    fm_str = m.group(1)
    body = text[m.end():]
    meta = {}
    for line in fm_str.splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            val = val.strip()
            if val.lower() in ("true", "false"):
                val = val.lower() == "true"
            meta[key.strip()] = val
    return meta, body


def _serialize_frontmatter(meta: dict, body: str) -> str:
    """Combine *meta* dict and markdown *body* into a full document."""
    lines = []
    for k, v in meta.items():
        if isinstance(v, bool):
            lines.append(f"{k}: {'true' if v else 'false'}")
        else:
            lines.append(f"{k}: {v}")
    fm = "\n".join(lines)
    return f"---\n{fm}\n---\n{body}"


def read_profile() -> str:
    """Read the user profile markdown (body only, no frontmatter).
    Returns the default template body if the file doesn't exist yet."""
    path = get_profile_path()
    if not os.path.exists(path):
        _, body = _parse_frontmatter(DEFAULT_PROFILE_TEMPLATE)
        return body
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    _, body = _parse_frontmatter(content)
    return body


def read_profile_raw() -> str:
    """Read the full file including frontmatter."""
    path = get_profile_path()
    if not os.path.exists(path):
        return DEFAULT_PROFILE_TEMPLATE
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def write_profile(content: str) -> None:
    """Overwrite the profile body, preserving frontmatter."""
    path = get_profile_path()
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            existing = f.read()
        meta, _ = _parse_frontmatter(existing)
    else:
        meta, _ = _parse_frontmatter(DEFAULT_PROFILE_TEMPLATE)
    # If the incoming content has its own frontmatter, strip it and merge
    incoming_meta, body = _parse_frontmatter(content)
    if incoming_meta:
        meta.update(incoming_meta)
    else:
        body = content
    full = _serialize_frontmatter(meta, body)
    with open(path, "w", encoding="utf-8") as f:
        f.write(full)


def read_profile_section(section_name: str) -> str | None:
    """Return the content of a specific ## section from the profile body, or None if not found."""
    body = read_profile()
    pattern = re.compile(
        _SECTION_RE_TEMPLATE.format(name=re.escape(section_name)),
        re.MULTILINE | re.DOTALL,
    )
    m = pattern.search(body)
    return m.group(1).strip() if m else None


def _deduplicate_sections(body: str) -> str:
    """Remove duplicate ``## Section`` headers from the profile body.

    When the same ``## Header`` appears more than once, the first occurrence
    with non-placeholder content is kept.  If every occurrence is a placeholder,
    the first one is kept.

    Everything before the first ``## `` header (the preamble, e.g.
    ``# User Profile``) is always preserved.
    """
    matches = list(_SECTION_HEADER_RE.finditer(body))
    if not matches:
        return body

    preamble = body[: matches[0].start()]

    # Build (header, start, end, content_text) for each section block.
    parts: list[tuple[str, int, int, str]] = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        header = m.group(0).strip()
        section_content = body[m.end() : end].strip()
        parts.append((header, start, end, section_content))

    # Keep the best version of each section (first non-placeholder wins).
    best: dict[str, int] = {}   # header -> index into *parts*
    order: list[str] = []       # first-seen order
    for idx, (header, _start, _end, section_content) in enumerate(parts):
        if header not in best:
            best[header] = idx
            order.append(header)
        else:
            existing_idx = best[header]
            existing_content = parts[existing_idx][3]
            if is_section_unfilled(existing_content) and not is_section_unfilled(
                section_content
            ):
                best[header] = idx

    result = preamble
    for header in order:
        idx = best[header]
        _, start, end, _ = parts[idx]
        result += body[start:end]
    return result


def write_profile_section(section_name: str, content: str) -> None:
    """Replace a single ## section in the profile body, preserving all other sections.

    If the *content* happens to contain additional ``## Section`` headers
    (e.g. because the LLM bundled several updates into one call), the
    resulting body is deduplicated so that each section header appears
    exactly once.
    """
    body = read_profile()
    new_section_text = f"## {section_name}\n{content.strip()}\n\n"
    pattern = re.compile(
        _SECTION_RE_TEMPLATE.format(name=re.escape(section_name)),
        re.MULTILINE | re.DOTALL,
    )
    if pattern.search(body):
        new_body = pattern.sub(new_section_text, body)
    else:
        # Section missing — append it
        new_body = body.rstrip("\n") + f"\n\n## {section_name}\n{content.strip()}\n"
    new_body = _deduplicate_sections(new_body)
    write_profile(new_body)


def ensure_profile_exists() -> None:
    """Create the profile file with the default template if it doesn't exist."""
    path = get_profile_path()
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            f.write(DEFAULT_PROFILE_TEMPLATE)


def get_onboarding_state() -> str:
    """Return the onboarding state: 'not_started', 'in_progress', or 'completed'."""
    path = get_profile_path()
    if not os.path.exists(path):
        return "not_started"
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    meta, _ = _parse_frontmatter(content)
    val = meta.get("onboarded", False)
    if val is True:
        return "completed"
    if val == "in_progress":
        return "in_progress"
    return "not_started"


def is_onboarded() -> bool:
    """Return True if the user has completed onboarding."""
    return get_onboarding_state() == "completed"


def is_onboarding_in_progress() -> bool:
    """Return True if onboarding was started but not completed."""
    return get_onboarding_state() == "in_progress"


def set_onboarding_in_progress() -> None:
    """Mark onboarding as started but not yet completed."""
    _set_onboarded_value("in_progress")


def set_onboarded(value: bool = True) -> None:
    """Set the onboarded flag in the profile frontmatter."""
    _set_onboarded_value(value)


def _set_onboarded_value(value) -> None:
    """Set the onboarded field to an arbitrary value (bool or string)."""
    ensure_profile_exists()
    path = get_profile_path()
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    meta, body = _parse_frontmatter(content)
    meta["onboarded"] = value
    full = _serialize_frontmatter(meta, body)
    with open(path, "w", encoding="utf-8") as f:
        f.write(full)
