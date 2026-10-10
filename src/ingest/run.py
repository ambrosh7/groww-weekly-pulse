"""Phase 1 entry: load raw → normalize → write data/processed/reviews.json."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from src.config.settings import Settings
from src.ingest.load import IngestError, discover_raw_files, load_raw_file, load_raw_paths
from src.normalize.pipeline import EmptyCorpusError, NormalizeResult, normalize_rows


def run_ingest(
    settings: Settings,
    *,
    raw_path: Path | None = None,
    now: datetime | None = None,
) -> NormalizeResult:
    if raw_path is not None:
        paths = [Path(raw_path)]
    else:
        paths = discover_raw_files(settings.raw_dir)
        if not paths:
            raise IngestError(
                f"No CSV/JSON exports in {settings.raw_dir}. "
                "Run: python -m src fetch-reviews"
            )
        # Prefer the live download if present
        preferred = settings.raw_dir / "groww_play_reviews.csv"
        if preferred.exists():
            paths = [preferred]

    rows = load_raw_paths(paths)
    result = normalize_rows(
        rows,
        play_package_id=settings.play_package_id,
        window_weeks=settings.window_weeks,
        min_review_words=settings.min_review_words,
        drop_emoji_reviews=settings.drop_emoji_reviews,
        require_english=settings.require_english,
        now=now,
    )
    write_reviews_json(result, settings.processed_dir / "reviews.json")
    return result


def write_reviews_json(result: NormalizeResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "meta": result.stats,
        "reviews": [r.to_dict() for r in result.reviews],
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


__all__ = [
    "run_ingest",
    "write_reviews_json",
    "IngestError",
    "EmptyCorpusError",
    "load_raw_file",
]
