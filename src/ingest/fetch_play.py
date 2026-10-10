"""
Download public Google Play reviews for Groww (no store login).

Uses the public Play Store review feed via google-play-scraper.
Does not access Play Console or any authenticated surface.
"""

from __future__ import annotations

import csv
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from google_play_scraper import Sort, reviews as fetch_reviews_page

from src.config.settings import Settings


class FetchError(RuntimeError):
    """Failed to download public Play reviews."""


def fetch_groww_reviews(
    settings: Settings,
    *,
    lang: str = "en",
    country: str = "in",
    max_reviews: int = 15000,
    sleep_s: float = 0.25,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """
    Fetch newest public reviews until we cover window_weeks or hit max_reviews.

    High-traffic apps (like Groww) can need many pages to reach an 8–12 week cutoff.
    """
    now_utc = now.astimezone(timezone.utc) if now else datetime.now(timezone.utc)
    cutoff = now_utc - timedelta(weeks=settings.window_weeks)

    collected: list[dict[str, Any]] = []
    token = None
    app_id = settings.play_package_id
    reached_cutoff = False

    while len(collected) < max_reviews:
        batch_size = min(200, max_reviews - len(collected))
        try:
            batch, token = fetch_reviews_page(
                app_id,
                lang=lang,
                country=country,
                sort=Sort.NEWEST,
                count=batch_size,
                continuation_token=token,
            )
        except Exception as exc:  # noqa: BLE001
            if collected:
                break
            raise FetchError(f"Play review fetch failed for {app_id}: {exc}") from exc

        if not batch:
            break

        for item in batch:
            collected.append(
                _to_raw_row(item, package_name=app_id, locale=f"{lang}_{country.upper()}")
            )
            at = item.get("at")
            if isinstance(at, datetime):
                at_utc = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
                if at_utc.astimezone(timezone.utc) < cutoff:
                    reached_cutoff = True

        if reached_cutoff or token is None:
            break
        if len(collected) % 1000 < batch_size:
            print(f"  … fetched {len(collected)} reviews (cutoff {cutoff.date().isoformat()})")
        time.sleep(sleep_s)

    if not collected:
        raise FetchError(f"No public reviews returned for {app_id} ({lang}/{country})")

    if not reached_cutoff:
        print(
            f"  warning: hit max_reviews={max_reviews} before covering "
            f"{settings.window_weeks} weeks (cutoff {cutoff.date().isoformat()}). "
            "Re-run with a higher --max-reviews if needed."
        )

    return collected


def _to_raw_row(item: dict[str, Any], *, package_name: str, locale: str) -> dict[str, Any]:
    at = item.get("at")
    if isinstance(at, datetime):
        date_str = at.astimezone(timezone.utc).date().isoformat()
    else:
        date_str = ""

    return {
        "review_id": item.get("reviewId") or item.get("review_id") or "",
        "package_name": package_name,
        "store": "play",
        "rating": item.get("score"),
        "title": item.get("title") or "",
        # Never persist reviewer identity in raw export used by the pipeline
        "text": item.get("content") or "",
        "date": date_str,
        "locale": locale,
        "thumbs_up": item.get("thumbsUpCount"),
        "reply": (item.get("replyContent") or ""),
    }


def save_raw_csv(rows: list[dict[str, Any]], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "review_id",
        "package_name",
        "store",
        "rating",
        "title",
        "text",
        "date",
        "locale",
        "thumbs_up",
        "reply",
    ]
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)
    return path


def save_raw_json(rows: list[dict[str, Any]], path: Path) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "package_name": rows[0]["package_name"] if rows else "",
        "store": "play",
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "count": len(rows),
        "reviews": rows,
    }
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path
