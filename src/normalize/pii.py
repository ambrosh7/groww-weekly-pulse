"""PII scrubbing for review text (Phase 1)."""

from __future__ import annotations

import re

# Order matters: apply more specific patterns first.
_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "[email]"),
    # Indian mobiles / common intl forms
    (re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)"), "[phone]"),
    (re.compile(r"(?<!\d)\+?\d[\d\s\-()]{8,}\d(?!\d)"), "[phone]"),
    # UPI VPA
    (re.compile(r"\b[\w.\-]+@(?!gmail\.com|yahoo\.com|outlook\.com|hotmail\.com)[\w.\-]+\b", re.I), "[upi]"),
    # Device / advertising ids
    (re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I), "[device_id]"),
    (re.compile(r"\b(?:android|device|imei|gaid)[\s:_-]*[a-z0-9\-]{8,}\b", re.I), "[device_id]"),
    # Long numeric account / demat / order-like tokens (10+ digits)
    (re.compile(r"(?<!\d)\d{10,}(?!\d)"), "[account]"),
]


def scrub_text(text: str) -> str:
    """Redact common PII patterns from review body."""
    cleaned = text
    for pattern, replacement in _PATTERNS:
        cleaned = pattern.sub(replacement, cleaned)
    # Collapse whitespace left by redactions
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned).strip()
    return cleaned
