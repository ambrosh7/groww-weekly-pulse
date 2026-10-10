"""
Pulse writer — top 3 themes, 3 verbatim quotes, 3 actions, ≤250 words (Phase 3).

Uses rule-based insights/actions (deterministic CI). Quotes are always copy-paste
verbatim from scrubbed review text.
"""

from __future__ import annotations

import re
from typing import Any, Sequence

from src.normalize.schema import Review
from src.pulse.actions import action_for_theme
from src.pulse.gates import (
    PulseAction,
    PulseDraft,
    PulseGateError,
    PulseQuote,
    PulseTheme,
    count_words,
)

# Known sample marker — exact body from groww_play_reviews_sample.csv
_SAMPLE_MARKER = (
    "KYC keeps failing at the selfie step and support just asks to try again tomorrow."
)
_SAMPLE_FIXTURE_NAME = "groww_play_reviews_sample.csv"

_MAX_QUOTE_CHARS = 220

def detect_source_fixture(reviews: Sequence[Review]) -> str | None:
    texts = {r.text.strip() for r in reviews}
    if _SAMPLE_MARKER in texts:
        return _SAMPLE_FIXTURE_NAME
    return None


def select_top_themes(
    themes: Sequence[dict[str, Any]],
    *,
    n: int = 3,
) -> list[dict[str, Any]]:
    """Select top N by rank_score; tie-break theme_id. Prefer non-general on equal score."""
    ordered = sorted(
        themes,
        key=lambda t: (
            -float(t.get("rank_score") or 0.0),
            0 if str(t.get("theme_id")) == "general" else -1,
            str(t.get("theme_id") or ""),
        ),
    )
    return list(ordered[:n])


def _normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def _maybe_truncate_quote(text: str) -> str:
    """Keep full text unless over ~220 chars; ellipsis only if prefix still verbatim."""
    text = text.strip()
    if len(text) <= _MAX_QUOTE_CHARS:
        return text
    # Truncate at word boundary, keep ellipsis suffix only when prefix ⊂ original
    cut = text[: _MAX_QUOTE_CHARS - 1].rsplit(" ", 1)[0]
    if not cut or cut not in text:
        return text  # fall back to full (caller may pick another)
    return cut + "…"


def _rank_quote_reviews(reviews: Sequence[Review]) -> list[Review]:
    return sorted(reviews, key=lambda r: (r.rating, -len(r.text), r.id))


def select_quotes(
    top_themes: Sequence[dict[str, Any]],
    reviews_by_id: dict[str, Review],
    *,
    quote_count: int = 3,
) -> list[PulseQuote]:
    """
    Prefer one quote per top theme (coverage first), then fill from remaining
    top-theme reviews. Ranking: lower rating, longer text, stable id.
    """
    selected: list[PulseQuote] = []
    seen: set[str] = set()

    def try_add(theme: dict[str, Any], review: Review) -> bool:
        nonlocal selected
        text = _maybe_truncate_quote(review.text)
        if "…" in text and text.rstrip("…") not in review.text:
            text = review.text.strip()
        key = _normalize_key(text)
        if not text or key in seen:
            return False
        if len(text.split()) < 5:
            return False
        seen.add(key)
        selected.append(
            PulseQuote(
                text=text,
                theme_id=str(theme["theme_id"]),
                theme_label=str(theme["label"]),
                rating=int(review.rating),
                review_id=review.id,
            )
        )
        return True

    # Pass 1: one per theme
    for theme in top_themes:
        if len(selected) >= quote_count:
            break
        ids = list(theme.get("review_ids") or [])
        theme_reviews = [reviews_by_id[i] for i in ids if i in reviews_by_id]
        # Prefer representative_quotes order when present (already Phase-2 ranked)
        candidates: list[Review] = []
        quote_texts = list(theme.get("representative_quotes") or [])
        by_text = {_normalize_key(r.text): r for r in theme_reviews}
        for qt in quote_texts:
            match = by_text.get(_normalize_key(qt))
            if match:
                candidates.append(match)
        for review in _rank_quote_reviews(theme_reviews):
            if review not in candidates:
                candidates.append(review)
        for review in candidates:
            if try_add(theme, review):
                break

    # Pass 2: fill shortfall from any top theme
    if len(selected) < quote_count:
        pool: list[tuple[dict[str, Any], Review]] = []
        for theme in top_themes:
            for rid in theme.get("review_ids") or []:
                if rid in reviews_by_id:
                    pool.append((theme, reviews_by_id[rid]))
        pool.sort(key=lambda item: (item[1].rating, -len(item[1].text), item[1].id))
        for theme, review in pool:
            if len(selected) >= quote_count:
                break
            try_add(theme, review)

    if len(selected) < quote_count:
        raise PulseGateError(
            f"Only {len(selected)} usable verbatim quotes (need {quote_count}); "
            "cannot invent wording"
        )
    return selected[:quote_count]


def _clip_words(text: str, max_chars: int) -> str:
    text = text.strip(" .,;:")
    if len(text) <= max_chars:
        return text
    clipped = text[:max_chars].rsplit(" ", 1)[0].rstrip(" .,;:")
    return clipped + "…" if clipped else text[:max_chars]


def _dominant_pain(_theme_id: str, quotes: Sequence[str]) -> str:
    """One short insight clause mined from the theme's selected/candidate quotes."""
    if quotes:
        first = quotes[0].strip().rstrip(".")
        return _clip_words(first, 90)
    return "recurring product friction"


def build_insight(theme: dict[str, Any], theme_quotes: Sequence[str]) -> str:
    pain = _dominant_pain(str(theme["theme_id"]), theme_quotes)
    low_star = ""
    avg = float(theme.get("avg_rating") or 0)
    if avg and avg <= 2.5:
        low_star = " Low-star share is elevated."
    return f"Dominant pain: {pain}.{low_star}".strip()


def build_actions(top_themes: Sequence[dict[str, Any]]) -> list[PulseAction]:
    actions: list[PulseAction] = []
    for theme in top_themes:
        tid = str(theme["theme_id"])
        label = str(theme["label"])
        actions.append(
            PulseAction(
                text=action_for_theme(tid, label),
                theme_id=tid,
                theme_label=label,
            )
        )
    return actions


def render_markdown(
    *,
    product_name: str,
    week_ending: str,
    window_weeks: int,
    window_start: str,
    window_end: str,
    kept_count: int,
    min_review_words: int,
    themes: Sequence[PulseTheme],
    quotes: Sequence[PulseQuote],
    actions: Sequence[PulseAction],
    soft_fail_note: str | None = None,
) -> str:
    lines: list[str] = [
        f"# {product_name} Weekly Pulse — week ending {week_ending}",
        "",
        (
            f"Window: last {window_weeks} weeks ({window_start} → {window_end}) · "
            f"Play reviews analyzed: {kept_count}"
        ),
        (
            f"Filters: >{min_review_words} words · English only · emoji reviews excluded"
        ),
        "",
    ]
    if soft_fail_note:
        lines.extend([soft_fail_note, ""])

    lines.append("## Top themes")
    for i, theme in enumerate(themes, start=1):
        lines.append(
            f"{i}. {theme.label} — n={theme.count}, avg ★={theme.avg_rating}. "
            f"{theme.insight}"
        )
    lines.append("")
    lines.append("## What users said")
    for quote in quotes:
        lines.append(f'- "{quote.text}" ({quote.theme_label})')
    lines.append("")
    lines.append("## Action ideas")
    for i, action in enumerate(actions, start=1):
        lines.append(f"{i}. {action.text} — grounded in {action.theme_label}")
    lines.append("")
    return "\n".join(lines).strip() + "\n"


def write_pulse(
    *,
    themes_payload: dict[str, Any],
    reviews: Sequence[Review],
    reviews_meta: dict[str, Any],
    product_name: str = "Groww",
    top_n: int = 3,
    quote_count: int = 3,
    action_count: int = 3,
    allow_soft_fail: bool = False,
) -> PulseDraft:
    theme_rows = list(themes_payload.get("themes") or [])
    if not theme_rows:
        raise PulseGateError("themes.json has no themes")

    top = select_top_themes(theme_rows, n=top_n)
    soft_note = None
    if len(top) < top_n:
        if not allow_soft_fail:
            raise PulseGateError(
                f"Only {len(top)} themes available (need {top_n}); "
                "set allow_soft_fail to degrade"
            )
        soft_note = f"_Soft-fail: only {len(top)} themes available (need {top_n})._"

    reviews_by_id = {r.id: r for r in reviews}
    quotes = select_quotes(top, reviews_by_id, quote_count=quote_count)

    # Insights use quotes belonging to each theme when available
    quotes_by_theme: dict[str, list[str]] = {}
    for q in quotes:
        quotes_by_theme.setdefault(q.theme_id, []).append(q.text)
    for theme in top:
        tid = str(theme["theme_id"])
        if tid not in quotes_by_theme:
            quotes_by_theme[tid] = list(theme.get("representative_quotes") or [])

    pulse_themes = [
        PulseTheme(
            theme_id=str(t["theme_id"]),
            label=str(t["label"]),
            count=int(t["count"]),
            avg_rating=float(t["avg_rating"]),
            rank_score=float(t.get("rank_score") or 0.0),
            insight=build_insight(t, quotes_by_theme.get(str(t["theme_id"]), [])),
        )
        for t in top
    ]

    actions = build_actions(top)
    if len(actions) != action_count and not (
        allow_soft_fail and len(actions) == len(top)
    ):
        # With soft-fail and fewer themes we still need 3 actions for strict sample;
        # pad only when soft-fail by repeating last theme action is NOT allowed —
        # require exact action_count always per plan ("do not enable soft-fail for sample").
        if len(actions) != action_count:
            raise PulseGateError(
                f"Expected {action_count} actions, built {len(actions)}"
            )

    week_ending = str(reviews_meta.get("window_end") or "")
    window_start = str(reviews_meta.get("window_start") or "")
    window_end = str(reviews_meta.get("window_end") or "")
    window_weeks = int(reviews_meta.get("window_weeks") or 0)
    kept = int(reviews_meta.get("kept") or len(reviews))
    min_words = int(reviews_meta.get("min_review_words") or 8)
    drop_emoji = bool(reviews_meta.get("drop_emoji_reviews", True))
    require_en = bool(reviews_meta.get("require_english", True))

    # Auto-trim insights if over budget (E3.9); quotes/actions stay intact.
    max_words = 250
    for _ in range(3):
        markdown = render_markdown(
            product_name=product_name,
            week_ending=week_ending,
            window_weeks=window_weeks,
            window_start=window_start,
            window_end=window_end,
            kept_count=kept,
            min_review_words=min_words,
            themes=pulse_themes,
            quotes=quotes,
            actions=actions,
            soft_fail_note=soft_note,
        )
        if count_words(markdown) <= max_words:
            break
        pulse_themes = [
            PulseTheme(
                theme_id=t.theme_id,
                label=t.label,
                count=t.count,
                avg_rating=t.avg_rating,
                rank_score=t.rank_score,
                insight=_shorten_insight(t.insight),
            )
            for t in pulse_themes
        ]

    return PulseDraft(
        week_ending=week_ending,
        window_weeks=window_weeks,
        window_start=window_start,
        window_end=window_end,
        review_count=kept,
        min_review_words=min_words,
        drop_emoji_reviews=drop_emoji,
        require_english=require_en,
        product_name=product_name,
        themes=pulse_themes,
        quotes=quotes,
        actions=actions,
        markdown=markdown,
        word_count=count_words(markdown),
        source_fixture=detect_source_fixture(reviews),
        soft_fail_note=soft_note,
    )


def _shorten_insight(insight: str) -> str:
    insight = insight.strip()
    if len(insight) <= 60:
        return insight
    # Drop trailing low-star clause first
    if " Low-star share" in insight:
        return insight.split(" Low-star share", 1)[0].strip()
    words = insight.split()
    if len(words) > 12:
        return " ".join(words[:12]).rstrip(".,") + "."
    return insight
