"""Redact personal information before it is written to the audit log.

The audit log must prove what an agent did without becoming a second copy of
customers' personal information (PIPEDA principle 4.4, Limiting Collection,
and 4.7, Safeguards). Pattern matching is a baseline, not a guarantee; a
production system would add a dedicated PII detection service.
"""

from __future__ import annotations

import re
from typing import Any

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    ("EMAIL", re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")),
    ("CARD", re.compile(r"\b(?:\d[ -]?){13,16}\b")),
    ("SIN", re.compile(r"\b\d{3}[ -]?\d{3}[ -]?\d{3}\b")),
    ("PHONE", re.compile(r"(?:\+?1[ .-]?)?\(?\d{3}\)?[ .-]?\d{3}[ .-]?\d{4}\b")),
    ("POSTAL_CODE", re.compile(r"\b[A-CEGHJ-NPR-TVXY]\d[A-CEGHJ-NPR-TV-Z] ?\d[A-CEGHJ-NPR-TV-Z]\d\b", re.I)),
]

# Keys whose values are always fully redacted, whatever they contain.
SENSITIVE_KEYS = {"password", "token", "api_key", "secret", "sin", "card_number", "dob", "date_of_birth"}


def redact_text(text: str) -> str:
    for label, pattern in _PATTERNS:
        text = pattern.sub(f"[REDACTED:{label}]", text)
    return text


def redact(value: Any) -> Any:
    """Recursively redact strings inside dicts, lists and tuples."""
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, dict):
        return {
            k: ("[REDACTED]" if str(k).lower() in SENSITIVE_KEYS else redact(v))
            for k, v in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value
