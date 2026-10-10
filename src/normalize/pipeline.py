"""Normalize raw rows: map, scrub, window-filter, dedupe (Phase 1)."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any, Iterable

from src.normalize.language import language_skip_reason
from src.normalize.schema import Review, map_row


class EmptyCorpusError(ValueError):
    """No usable Play reviews remain after normalize/window filter."""


@dataclass
class NormalizeResult:
    reviews: list[Review]
    stats: dict[str, Any]


def word_count(text: str) -> int:
    return len(text.split())


def window_bounds(window_weeks: int, *, now: datetime | None = None) -> tuple[date, date]:
    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    end = now_utc.date()
    start = end - timedelta(weeks=window_weeks)
    return start, end


def normalize_rows(
    rows: Iterable[dict[str, Any]],
    *,
    play_package_id: str,
    window_weeks: int,
    min_review_words: int = 8,
    drop_emoji_reviews: bool = True,
    require_english: bool = True,
    now: datetime | None = None,
) -> NormalizeResult:
    """
    Normalize raw rows.

    min_review_words: keep reviews with word_count > min_review_words
    (default 8 ⇒ more than 8 words).
    drop_emoji_reviews: drop emoji-only / emoji-dominated reviews.
    require_english: drop non-English reviews (non-Latin scripts + langdetect != en).
    """
    start, end = window_bounds(window_weeks, now=now)
    skip_counts: Counter[str] = Counter()
    kept: list[Review] = []
    seen_ids: set[str] = set()

    for row in rows:
        review, reason = map_row(row, play_package_id=play_package_id)
        if reason:
            skip_counts[reason] += 1
            continue

        assert review is not None
        review_date = date.fromisoformat(review.date)
        if review_date > end:
            skip_counts["future_date"] += 1
            continue
        if review_date < start:
            skip_counts["outside_window"] += 1
            continue

        # Language/emoji before word-count so skip stats stay meaningful
        lang_reason = language_skip_reason(
            review.text,
            drop_emoji_reviews=drop_emoji_reviews,
            require_english=require_english,
        )
        if lang_reason:
            skip_counts[lang_reason] += 1
            continue

        if word_count(review.text) <= min_review_words:
            skip_counts["too_few_words"] += 1
            continue

        if review.id in seen_ids:
            skip_counts["duplicate_id"] += 1
            continue
        seen_ids.add(review.id)
        kept.append(review)

    if not kept:
        non_scope = sum(v for k, v in skip_counts.items() if k != "app_store_out_of_scope")
        if skip_counts.get("app_store_out_of_scope", 0) > 0 and non_scope == 0:
            raise EmptyCorpusError(
                "App Store reviews are out of scope for v1. Provide a Google Play export "
                f"for {play_package_id}."
            )
        raise EmptyCorpusError(
            f"No usable Play reviews in the last {window_weeks} weeks "
            f"({start.isoformat()} → {end.isoformat()}). skip_counts={dict(skip_counts)}"
        )

    kept.sort(key=lambda r: (r.date, r.id), reverse=True)
    stats = {
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "window_weeks": window_weeks,
        "min_review_words": min_review_words,
        "drop_emoji_reviews": drop_emoji_reviews,
        "require_english": require_english,
        "kept": len(kept),
        "skipped": dict(skip_counts),
        "data_starved": len(kept) < 10,
    }
    return NormalizeResult(reviews=kept, stats=stats)
