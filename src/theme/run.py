"""Phase 2 entry: load reviews.json → theme → write themes.json."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from src.config.settings import Settings
from src.normalize.schema import Review
from src.theme.engine import ThemeResult, cluster_reviews


class ThemeError(ValueError):
    """Theming failed."""


def load_reviews_json(path: Path) -> list[Review]:
    path = Path(path)
    if not path.exists():
        raise ThemeError(f"reviews.json not found: {path}. Run: python -m src ingest")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ThemeError(f"Corrupt reviews.json: {exc}") from exc

    rows = payload.get("reviews") if isinstance(payload, dict) else payload
    if not isinstance(rows, list) or not rows:
        raise ThemeError("reviews.json has no reviews")

    reviews: list[Review] = []
    for row in rows:
        reviews.append(
            Review(
                id=str(row["id"]),
                store=str(row.get("store", "play")),
                rating=int(row["rating"]),
                title=str(row.get("title") or ""),
                text=str(row["text"]),
                date=str(row["date"]),
                locale=str(row.get("locale") or ""),
            )
        )
    return reviews


def run_theme(
    settings: Settings,
    *,
    reviews_path: Path | None = None,
) -> ThemeResult:
    path = Path(reviews_path) if reviews_path else settings.processed_dir / "reviews.json"
    reviews = load_reviews_json(path)
    result = cluster_reviews(
        reviews,
        max_themes=settings.max_themes,
        quotes_per_theme=settings.quotes_per_theme,
    )
    write_themes_json(result, settings.processed_dir / "themes.json")
    return result


def write_themes_json(result: ThemeResult, path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {
        "meta": result.stats,
        "themes": [t.to_dict() for t in result.themes],
        "assignments": result.assignments,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
