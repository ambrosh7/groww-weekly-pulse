#!/usr/bin/env python3
"""Sync pipeline artifacts into frontend/public/data for the Vercel dashboard.

Reads:
  - data/output/pulse.json
  - data/processed/reviews.json (optional)
  - data/processed/themes.json (optional, for theme labels)

Writes:
  - frontend/public/data/pulse.json
  - frontend/public/data/reviews.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PULSE = ROOT / "data" / "output" / "pulse.json"
DEFAULT_REVIEWS = ROOT / "data" / "processed" / "reviews.json"
DEFAULT_THEMES = ROOT / "data" / "processed" / "themes.json"
OUT_DIR = ROOT / "frontend" / "public" / "data"


def _load_json(path: Path) -> dict | list:
    return json.loads(path.read_text(encoding="utf-8"))


def _theme_lookup(themes_path: Path) -> dict[str, tuple[str, str]]:
    """Map review_id → (theme_id, theme_label)."""
    if not themes_path.is_file():
        return {}
    payload = _load_json(themes_path)
    themes = payload.get("themes") if isinstance(payload, dict) else payload
    lookup: dict[str, tuple[str, str]] = {}
    for theme in themes or []:
        tid = str(theme.get("theme_id") or "other")
        label = str(theme.get("label") or tid)
        for rid in theme.get("review_ids") or []:
            lookup[str(rid)] = (tid, label)
    return lookup


def build_reviews_fixture(
    reviews_path: Path,
    themes_path: Path,
) -> list[dict]:
    if not reviews_path.is_file():
        return []

    payload = _load_json(reviews_path)
    rows = payload.get("reviews") if isinstance(payload, dict) else payload
    lookup = _theme_lookup(themes_path)
    out: list[dict] = []
    for row in rows or []:
        rid = str(row.get("id") or row.get("review_id") or "")
        theme_id, theme_label = lookup.get(rid, ("other", "Other"))
        out.append(
            {
                "review_id": rid,
                "rating": int(row.get("rating") or 0),
                "text": str(row.get("text") or ""),
                "date": str(row.get("date") or ""),
                "locale": str(row.get("locale") or ""),
                "theme_id": theme_id,
                "theme_label": theme_label,
            }
        )
    return out


def sync(
    *,
    pulse_path: Path,
    reviews_path: Path,
    themes_path: Path,
    out_dir: Path,
) -> tuple[Path, Path | None]:
    if not pulse_path.is_file():
        raise FileNotFoundError(f"Missing pulse artifact: {pulse_path}")

    out_dir.mkdir(parents=True, exist_ok=True)
    pulse_out = out_dir / "pulse.json"
    pulse_out.write_text(
        json.dumps(_load_json(pulse_path), indent=2) + "\n",
        encoding="utf-8",
    )

    reviews = build_reviews_fixture(reviews_path, themes_path)
    reviews_out: Path | None = None
    if reviews:
        reviews_out = out_dir / "reviews.json"
        reviews_out.write_text(
            json.dumps(reviews, indent=2) + "\n",
            encoding="utf-8",
        )
    return pulse_out, reviews_out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pulse", type=Path, default=DEFAULT_PULSE)
    parser.add_argument("--reviews", type=Path, default=DEFAULT_REVIEWS)
    parser.add_argument("--themes", type=Path, default=DEFAULT_THEMES)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args(argv)

    try:
        pulse_out, reviews_out = sync(
            pulse_path=args.pulse,
            reviews_path=args.reviews,
            themes_path=args.themes,
            out_dir=args.out_dir,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    print(f"Synced {pulse_out}")
    if reviews_out:
        print(f"Synced {reviews_out}")
    else:
        print("No processed reviews found — left existing reviews.json untouched")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
