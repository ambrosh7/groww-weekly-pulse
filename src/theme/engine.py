"""
Theme clustering for Groww reviews (Phase 2).

Approach: keyword_seed labeling with a fixed Groww vocabulary, then merge
lowest-ranked themes until theme_count ≤ max_themes (default 5).

rank_score formula (documented):
  negative_rating_weight = average of (6 - rating) across theme reviews  # 1★→5, 5★→1
  rank_score = 0.6 * normalize(count) + 0.4 * normalize(negative_rating_weight)

  normalize(x) = x / max(x across themes)  (0 if max is 0)

Deterministic for a fixed reviews.json (stable sort / tie-break on theme_id).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from src.normalize.schema import Review
from src.theme.rules import GENERAL_THEME, THEME_RULES, ThemeRule


@dataclass
class Theme:
    theme_id: str
    label: str
    review_ids: list[str]
    count: int
    avg_rating: float
    representative_quotes: list[str]
    rank_score: float
    ratings_sum: float = field(default=0.0, repr=False)
    neg_weight_sum: float = field(default=0.0, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "theme_id": self.theme_id,
            "label": self.label,
            "review_ids": self.review_ids,
            "count": self.count,
            "avg_rating": self.avg_rating,
            "representative_quotes": self.representative_quotes,
            "rank_score": self.rank_score,
        }


@dataclass
class ThemeResult:
    themes: list[Theme]
    assignments: dict[str, str]  # review_id -> theme_id
    stats: dict[str, Any]


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def score_review_for_rule(text: str, rule: ThemeRule) -> int:
    """Return keyword hit score (phrase matches weighted higher)."""
    if not rule.keywords:
        return 0
    hay = _normalize_text(text)
    score = 0
    for kw in rule.keywords:
        needle = kw.lower()
        if " " in needle or "&" in needle:
            if needle in hay:
                score += 2
        else:
            # word-boundary-ish match
            if re.search(rf"(?<!\w){re.escape(needle)}(?!\w)", hay):
                score += 1
    return score


def assign_theme(review: Review, rules: tuple[ThemeRule, ...] = THEME_RULES) -> ThemeRule:
    scored: list[tuple[int, str, ThemeRule]] = []
    for rule in rules:
        score = score_review_for_rule(review.text, rule)
        if score > 0:
            scored.append((score, rule.theme_id, rule))
    if not scored:
        return GENERAL_THEME
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored[0][2]


def _quote_candidates(
    reviews: list[Review],
    *,
    limit: int,
) -> list[str]:
    """Pick verbatim review texts: prefer lower rating, then longer, then id."""
    ranked = sorted(
        reviews,
        key=lambda r: (r.rating, -len(r.text), r.id),
    )
    quotes: list[str] = []
    seen: set[str] = set()
    for review in ranked:
        text = review.text.strip()
        if len(text.split()) < 5:
            continue
        key = _normalize_text(text)
        if key in seen:
            continue
        seen.add(key)
        quotes.append(text)
        if len(quotes) >= limit:
            break
    return quotes


def _build_theme(
    theme_id: str,
    label: str,
    reviews: list[Review],
    *,
    quotes_per_theme: int,
) -> Theme:
    count = len(reviews)
    ratings_sum = float(sum(r.rating for r in reviews))
    neg_weight_sum = float(sum(6 - r.rating for r in reviews))
    avg = round(ratings_sum / count, 3) if count else 0.0
    return Theme(
        theme_id=theme_id,
        label=label,
        review_ids=sorted(r.id for r in reviews),
        count=count,
        avg_rating=avg,
        representative_quotes=_quote_candidates(reviews, limit=quotes_per_theme),
        rank_score=0.0,
        ratings_sum=ratings_sum,
        neg_weight_sum=neg_weight_sum,
    )


def _apply_rank_scores(themes: list[Theme]) -> None:
    """
    rank_score = 0.6 * norm(count) + 0.4 * norm(avg_negative_weight)

    where avg_negative_weight = neg_weight_sum / count
    """
    if not themes:
        return
    counts = [t.count for t in themes]
    neg_avgs = [(t.neg_weight_sum / t.count) if t.count else 0.0 for t in themes]
    max_count = max(counts) or 1
    max_neg = max(neg_avgs) or 1.0
    for theme, neg_avg in zip(themes, neg_avgs):
        norm_count = theme.count / max_count
        norm_neg = neg_avg / max_neg
        theme.rank_score = round(0.6 * norm_count + 0.4 * norm_neg, 4)


def _merge_lowest(themes: list[Theme], reviews_by_id: dict[str, Review], quotes_per_theme: int) -> list[Theme]:
    """Merge the lowest-ranked theme into the next-lowest until ≤ budget handled by caller."""
    ordered = sorted(themes, key=lambda t: (t.rank_score, t.theme_id))
    lowest, target = ordered[0], ordered[1]
    merged_ids = lowest.review_ids + target.review_ids
    merged_reviews = [reviews_by_id[i] for i in merged_ids if i in reviews_by_id]
    # Prefer keeping the higher-ranked theme's id/label when merging
    keep = target if (target.rank_score, target.theme_id) >= (lowest.rank_score, lowest.theme_id) else lowest
    drop = lowest if keep is target else target
    label = keep.label if keep.count >= drop.count else f"{keep.label} + {drop.label}"
    merged = _build_theme(keep.theme_id, label, merged_reviews, quotes_per_theme=quotes_per_theme)
    remaining = [t for t in themes if t.theme_id not in {keep.theme_id, drop.theme_id}]
    remaining.append(merged)
    _apply_rank_scores(remaining)
    return remaining


def cluster_reviews(
    reviews: list[Review],
    *,
    max_themes: int = 5,
    quotes_per_theme: int = 3,
) -> ThemeResult:
    if not reviews:
        raise ValueError("Cannot theme an empty review list")
    if max_themes < 1 or max_themes > 5:
        raise ValueError("max_themes must be between 1 and 5")

    buckets: dict[str, list[Review]] = {}
    labels: dict[str, str] = {}
    assignments: dict[str, str] = {}

    for review in reviews:
        rule = assign_theme(review)
        buckets.setdefault(rule.theme_id, []).append(review)
        labels[rule.theme_id] = rule.label
        assignments[review.id] = rule.theme_id

    themes = [
        _build_theme(tid, labels[tid], items, quotes_per_theme=quotes_per_theme)
        for tid, items in buckets.items()
        if items
    ]
    _apply_rank_scores(themes)

    reviews_by_id = {r.id: r for r in reviews}
    # Drop empty (shouldn't happen) then merge until ≤ max_themes
    while len(themes) > max_themes:
        themes = _merge_lowest(themes, reviews_by_id, quotes_per_theme)

    themes.sort(key=lambda t: (-t.rank_score, t.theme_id))

    # Rebuild assignments after merges
    final_assignments: dict[str, str] = {}
    for theme in themes:
        for rid in theme.review_ids:
            final_assignments[rid] = theme.theme_id

    # Verify quotes are verbatim
    corpus_texts = {r.id: r.text for r in reviews}
    for theme in themes:
        for quote in theme.representative_quotes:
            ok = any(quote in text for text in corpus_texts.values())
            if not ok:
                raise RuntimeError(f"Non-verbatim quote in theme {theme.theme_id}: {quote!r}")

    stats = {
        "review_count": len(reviews),
        "theme_count": len(themes),
        "max_themes": max_themes,
        "clustering_approach": "keyword_seed",
        "rank_formula": "0.6*norm(count) + 0.4*norm(avg(6-rating))",
    }
    return ThemeResult(themes=themes, assignments=final_assignments, stats=stats)
