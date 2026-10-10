"""Validation gates for weekly pulse artifacts (Phase 3) — fail closed."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Sequence

from src.normalize.pii import scrub_text

# Same classes of PII as Phase 1 scrubber; gate fails if any hit remains unredacted.
_PII_CHECKS: list[tuple[str, re.Pattern[str]]] = [
    ("email", re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")),
    ("phone", re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{9}(?!\d)")),
    (
        "device_id",
        re.compile(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            re.I,
        ),
    ),
    (
        "device_id",
        re.compile(r"\b(?:android|device|imei|gaid)[\s:_-]*[a-z0-9\-]{8,}\b", re.I),
    ),
]


class PulseGateError(ValueError):
    """Pulse failed a validation gate."""


@dataclass(frozen=True)
class PulseQuote:
    text: str
    theme_id: str
    theme_label: str
    rating: int
    review_id: str


@dataclass(frozen=True)
class PulseTheme:
    theme_id: str
    label: str
    count: int
    avg_rating: float
    rank_score: float
    insight: str


@dataclass(frozen=True)
class PulseAction:
    text: str
    theme_id: str
    theme_label: str


@dataclass
class PulseDraft:
    week_ending: str
    window_weeks: int
    window_start: str
    window_end: str
    review_count: int
    min_review_words: int
    drop_emoji_reviews: bool
    require_english: bool
    product_name: str
    themes: list[PulseTheme]
    quotes: list[PulseQuote]
    actions: list[PulseAction]
    markdown: str
    word_count: int
    source_fixture: str | None = None
    soft_fail_note: str | None = None


def count_words(text: str) -> int:
    """Whitespace tokenizer (documented for H8 / E3.11)."""
    return len(text.split())


def find_pii_hits(text: str) -> list[str]:
    """Return human-readable PII hit labels found in text."""
    hits: list[str] = []
    for label, pattern in _PII_CHECKS:
        if pattern.search(text):
            hits.append(label)
    return sorted(set(hits))


def quote_is_verbatim(quote: str, review_texts: Sequence[str]) -> bool:
    if not quote:
        return False
    return any(quote in body for body in review_texts)


def validate_pulse(
    draft: PulseDraft,
    *,
    review_texts: Sequence[str],
    reviews_meta: dict[str, Any],
    expected_theme_count: int = 3,
    expected_quote_count: int = 3,
    expected_action_count: int = 3,
    max_words: int = 250,
    allow_soft_fail: bool = False,
) -> None:
    """
    Fail closed on shape, verbatim quotes, theme linkage, word count, privacy,
    and corpus-policy header echo.
    """
    theme_n = len(draft.themes)
    quote_n = len(draft.quotes)
    action_n = len(draft.actions)

    if theme_n < 1:
        raise PulseGateError("Pulse has no themes")
    if not allow_soft_fail and theme_n != expected_theme_count:
        raise PulseGateError(
            f"Expected exactly {expected_theme_count} themes, got {theme_n}"
        )
    if allow_soft_fail and theme_n > expected_theme_count:
        raise PulseGateError(
            f"Soft-fail allows fewer themes, not more than {expected_theme_count}"
        )
    if quote_n != expected_quote_count:
        raise PulseGateError(
            f"Expected exactly {expected_quote_count} quotes, got {quote_n} "
            "(cannot invent wording)"
        )
    if action_n != expected_action_count:
        raise PulseGateError(
            f"Expected exactly {expected_action_count} actions, got {action_n}"
        )

    if not draft.week_ending or draft.review_count < 1:
        raise PulseGateError("Pulse header missing week_ending or review_count")

    top_ids = {t.theme_id for t in draft.themes}
    top_labels = {t.label for t in draft.themes}

    for quote in draft.quotes:
        if quote.theme_id not in top_ids:
            raise PulseGateError(
                f"Quote theme_id {quote.theme_id!r} is not among top themes"
            )
        if quote.theme_label not in top_labels:
            raise PulseGateError(
                f"Quote theme_label {quote.theme_label!r} is not among top themes"
            )
        if not quote_is_verbatim(quote.text, review_texts):
            raise PulseGateError(
                f"Invented or paraphrased quote rejected: {quote.text!r}"
            )
        # Prefer not to ship quotes that still contain raw PII
        if find_pii_hits(quote.text):
            raise PulseGateError(f"Quote contains PII patterns: {quote.text!r}")

    for action in draft.actions:
        if action.theme_id not in top_ids:
            raise PulseGateError(
                f"Action theme_id {action.theme_id!r} is not among top themes"
            )
        lower = action.text.lower()
        if "improve ux" in lower and "theme" not in lower:
            raise PulseGateError(f"Generic action rejected: {action.text!r}")

    # Dedup quotes
    normalized = [re.sub(r"\s+", " ", q.text.lower()).strip() for q in draft.quotes]
    if len(set(normalized)) != len(normalized):
        raise PulseGateError("Duplicate quotes selected")

    wc = count_words(draft.markdown)
    if wc != draft.word_count:
        raise PulseGateError(
            f"word_count field {draft.word_count} != counted {wc}"
        )
    if wc > max_words:
        raise PulseGateError(f"Word count {wc} exceeds max {max_words}")

    pii = find_pii_hits(draft.markdown)
    if pii:
        raise PulseGateError(f"PII patterns in pulse body: {', '.join(pii)}")

    # Corpus policy echo from reviews.json meta
    for key in ("min_review_words", "drop_emoji_reviews", "require_english"):
        if key in reviews_meta and getattr(draft, key) != reviews_meta[key]:
            raise PulseGateError(
                f"Header policy {key}={getattr(draft, key)!r} "
                f"does not match reviews.json meta {reviews_meta[key]!r}"
            )
    meta_kept = reviews_meta.get("kept")
    if meta_kept is not None and int(meta_kept) != draft.review_count:
        raise PulseGateError(
            f"review_count {draft.review_count} != reviews.json meta.kept {meta_kept}"
        )
    for key in ("window_start", "window_end", "window_weeks"):
        if key in reviews_meta and str(reviews_meta[key]) != str(getattr(draft, key)):
            raise PulseGateError(
                f"Header {key}={getattr(draft, key)!r} "
                f"does not match reviews.json meta {reviews_meta[key]!r}"
            )

    # Scrub sanity: redacting pulse should not change it if already clean of raw PII
    if scrub_text(draft.markdown) != draft.markdown and find_pii_hits(draft.markdown):
        raise PulseGateError("Pulse body failed privacy scrub consistency check")
