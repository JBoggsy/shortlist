"""Sanitize sensitive data from strings before logging or returning to clients.

The primary concern is API keys that LLM libraries embed in exception
messages (e.g. ``AuthenticationError: Invalid API key: sk-ant-abc...``).
"""

import re
from typing import Sequence

# Patterns that match common API key formats.
# Each pattern is replaced with a redaction placeholder.
_KEY_PATTERNS: Sequence[re.Pattern] = [
    # Anthropic keys: sk-ant-api03-...
    re.compile(r"sk-ant-[A-Za-z0-9_-]{10,}"),
    # OpenAI keys: sk-proj-... or sk-...
    re.compile(r"sk-(?:proj-)?[A-Za-z0-9_-]{10,}"),
    # Google / Gemini keys: AIza...
    re.compile(r"AIza[A-Za-z0-9_-]{10,}"),
    # Tavily keys: tvly-...
    re.compile(r"tvly-[A-Za-z0-9_-]{10,}"),
    # RapidAPI keys (hex, typically 50 chars)
    re.compile(r"\b[0-9a-f]{40,}\b"),
    # Generic long bearer-style tokens (fallback)
    re.compile(r"(?:key|token|secret|bearer)[=: ]+['\"]?[A-Za-z0-9_-]{20,}['\"]?", re.IGNORECASE),
]

_REDACTED = "***"


def sanitize(text: str) -> str:
    """Return *text* with API-key-like substrings replaced by ``***``.

    Safe to call on any string — if no patterns match the original text
    is returned unchanged.
    """
    for pattern in _KEY_PATTERNS:
        text = pattern.sub(_REDACTED, text)
    return text


def sanitize_error(exc: BaseException) -> str:
    """Return a sanitized string representation of *exc*.

    Equivalent to ``sanitize(str(exc))`` but reads a bit nicer at call
    sites::

        logger.error("Connection failed: %s", sanitize_error(e))
    """
    return sanitize(str(exc))
