"""Phase 3 entry: load reviews.json + themes.json → validate → write pulse.*."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from src.config.settings import Settings
from src.normalize.schema import Review
from src.pulse.gates import PulseDraft, PulseGateError, validate_pulse
from src.pulse.writer import write_pulse
from src.theme.run import ThemeError, load_reviews_json


class PulseError(ValueError):
    """Pulse generation failed."""


@dataclass
class PulseRunResult:
    draft: PulseDraft
    md_path: Path
    json_path: Path
    stats: dict[str, Any]


def load_themes_json(path: Path) -> dict[str, Any]:
    path = Path(path)
    if not path.exists():
        raise PulseError(f"themes.json not found: {path}. Run: python -m src theme")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PulseError(f"Corrupt themes.json: {exc}") from exc
    if not isinstance(payload, dict) or not payload.get("themes"):
        raise PulseError("themes.json has no themes")
    return payload


def load_reviews_payload(path: Path) -> tuple[list[Review], dict[str, Any]]:
    path = Path(path)
    if not path.exists():
        raise PulseError(f"reviews.json not found: {path}. Run: python -m src ingest")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise PulseError(f"Corrupt reviews.json: {exc}") from exc
    if not isinstance(payload, dict):
        raise PulseError("reviews.json must be an object with meta + reviews")
    meta = payload.get("meta") or {}
    reviews = load_reviews_json(path)
    return reviews, dict(meta)


def draft_to_json(draft: PulseDraft) -> dict[str, Any]:
    return {
        "week_ending": draft.week_ending,
        "window_weeks": draft.window_weeks,
        "window_start": draft.window_start,
        "window_end": draft.window_end,
        "review_count": draft.review_count,
        "min_review_words": draft.min_review_words,
        "drop_emoji_reviews": draft.drop_emoji_reviews,
        "require_english": draft.require_english,
        "product_name": draft.product_name,
        "themes": [asdict(t) for t in draft.themes],
        "quotes": [asdict(q) for q in draft.quotes],
        "actions": [asdict(a) for a in draft.actions],
        "word_count": draft.word_count,
        "doc_url": None,
        "source_fixture": draft.source_fixture,
        "soft_fail_note": draft.soft_fail_note,
    }


def _atomic_write(path: Path, text: str) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, path)


def write_pulse_artifacts(draft: PulseDraft, output_dir: Path) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    md_path = output_dir / "pulse.md"
    json_path = output_dir / "pulse.json"
    _atomic_write(md_path, draft.markdown)
    _atomic_write(json_path, json.dumps(draft_to_json(draft), ensure_ascii=False, indent=2) + "\n")
    return md_path, json_path


def remove_pulse_artifacts(output_dir: Path) -> None:
    """Delete incomplete / failed pulse pair (E4.7)."""
    for name in ("pulse.md", "pulse.json"):
        path = Path(output_dir) / name
        if path.exists():
            path.unlink()


def run_pulse(
    settings: Settings,
    *,
    reviews_path: Path | None = None,
    themes_path: Path | None = None,
    output_dir: Path | None = None,
) -> PulseRunResult:
    reviews_file = Path(reviews_path) if reviews_path else settings.processed_dir / "reviews.json"
    themes_file = Path(themes_path) if themes_path else settings.processed_dir / "themes.json"
    out_dir = Path(output_dir) if output_dir else settings.output_dir

    try:
        reviews, meta = load_reviews_payload(reviews_file)
    except ThemeError as exc:
        raise PulseError(str(exc)) from exc

    themes_payload = load_themes_json(themes_file)

    try:
        draft = write_pulse(
            themes_payload=themes_payload,
            reviews=reviews,
            reviews_meta=meta,
            product_name=settings.product_name,
            top_n=settings.pulse_top_themes,
            quote_count=settings.quote_count,
            action_count=settings.action_count,
            allow_soft_fail=settings.allow_soft_fail,
        )
        validate_pulse(
            draft,
            review_texts=[r.text for r in reviews],
            reviews_meta=meta,
            expected_theme_count=settings.pulse_top_themes,
            expected_quote_count=settings.quote_count,
            expected_action_count=settings.action_count,
            max_words=settings.max_pulse_words,
            allow_soft_fail=settings.allow_soft_fail,
        )
    except PulseGateError:
        remove_pulse_artifacts(out_dir)
        raise

    md_path, json_path = write_pulse_artifacts(draft, out_dir)
    stats = {
        "week_ending": draft.week_ending,
        "review_count": draft.review_count,
        "theme_count": len(draft.themes),
        "quote_count": len(draft.quotes),
        "action_count": len(draft.actions),
        "word_count": draft.word_count,
        "source_fixture": draft.source_fixture,
    }
    return PulseRunResult(draft=draft, md_path=md_path, json_path=json_path, stats=stats)
