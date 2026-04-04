"""User profile management — reads and writes a markdown file that stores
information about the user relevant to their job search.

The file uses YAML frontmatter to store metadata (e.g. onboarding status)."""

import os
import re

from backend.data_dir import get_data_dir
from backend.safe_write import atomic_write

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

# Pattern to split on any ## heading line
_ANY_SECTION_RE = re.compile(r"^## (.+)$", re.MULTILINE)


def _parse_body_sections(body: str) -> tuple[str, dict[str, str], list[str]]:
    """Parse a profile *body* into (preamble, sections_dict, section_order).

    *preamble* is everything before the first ``## `` heading (e.g. the
    ``# User Profile`` line).  *sections_dict* maps each heading name to its
    body text (stripped).  *section_order* preserves the order headings appear.
    """
    matches = list(_ANY_SECTION_RE.finditer(body))
    if not matches:
        return body, {}, []

    preamble = body[: matches[0].start()]
    sections: dict[str, str] = {}
    order: list[str] = []

    for i, m in enumerate(matches):
        name = m.group(1).strip()
        start = m.end()  # position right after the heading line
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        content = body[start:end].strip()
        # If the same heading appears more than once keep the version that
        # has real content (not the placeholder).
        if name in sections:
            if is_section_unfilled(sections[name]) and not is_section_unfilled(content):
                sections[name] = content
            # else keep the earlier (presumably filled) version
        else:
            sections[name] = content
            order.append(name)

    return preamble, sections, order


def _assemble_body(preamble: str, sections: dict[str, str], order: list[str]) -> str:
    """Reassemble a profile body from *preamble* and ordered *sections*."""
    parts = [preamble.rstrip("\n")]
    for name in order:
        content = sections.get(name, SECTION_PLACEHOLDER)
        parts.append(f"## {name}\n{content}\n")
    return "\n".join(parts) + "\n"


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
    with atomic_write(path, encoding="utf-8") as f:
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


def write_profile_section(section_name: str, content: str) -> None:
    """Replace one or more ``##`` sections in the profile body.

    If *content* contains embedded ``## Header`` lines (e.g. the LLM included
    multiple sections in one tool call), each embedded section is parsed and
    the corresponding section in the profile is updated.  This prevents
    duplicate headings that previously occurred when the replacement text was
    naively inserted into a single section slot.
    """
    body = read_profile()
    preamble, sections, order = _parse_body_sections(body)

    # Build a synthetic block so _parse_body_sections can split it
    incoming_block = f"## {section_name}\n{content.strip()}\n"
    _, incoming_sections, incoming_order = _parse_body_sections(incoming_block)

    # Merge incoming sections into the existing profile
    for name in incoming_order:
        if name in sections:
            sections[name] = incoming_sections[name]
        else:
            sections[name] = incoming_sections[name]
            order.append(name)

    new_body = _assemble_body(preamble, sections, order)
    write_profile(new_body)


def ensure_profile_exists() -> None:
    """Create the profile file with the default template if it doesn't exist."""
    path = get_profile_path()
    if not os.path.exists(path):
        with atomic_write(path, encoding="utf-8") as f:
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
    with atomic_write(path, encoding="utf-8") as f:
        f.write(full)
