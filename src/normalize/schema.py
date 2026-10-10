"""Internal review schema and field mapping (Phase 1)."""

from __future__ import annotations

import hashlib
import html
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from typing import Any

from src.normalize.pii import scrub_text

PLAY_ALIASES = {"play", "google_play", "googleplay", "gp", "android"}
APP_STORE_ALIASES = {"app_store", "appstore", "ios", "apple", "itunes"}


@dataclass(frozen=True)
class Review:
    id: str
    store: str
    rating: int
    title: str
    text: str
    date: str  # YYYY-MM-DD
    locale: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def stable_id(*, store: str, date_str: str, text: str, export_id: str | None = None) -> str:
    if export_id:
        return hashlib.sha256(f"{store}:{export_id}".encode("utf-8")).hexdigest()[:16]
    payload = f"{store}|{date_str}|{text.strip()}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def _get(row: dict[str, Any], *keys: str) -> Any:
    lower = {str(k).strip().lower(): v for k, v in row.items()}
    for key in keys:
        if key.lower() in lower and lower[key.lower()] not in (None, ""):
            return lower[key.lower()]
    return None


def parse_store(value: Any) -> str | None:
    if value is None or value == "":
        return "play"  # v1 default for Play exports
    token = str(value).strip().lower().replace(" ", "_")
    if token in PLAY_ALIASES:
        return "play"
    if token in APP_STORE_ALIASES:
        return "app_store"
    return None


def parse_rating(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        rating = int(float(value))
    except (TypeError, ValueError):
        return None
    if rating < 1 or rating > 5:
        return None
    return rating


def parse_date(value: Any) -> date | None:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).date()
    if isinstance(value, date):
        return value
    if isinstance(value, (int, float)):
        ts = float(value)
        if ts > 1e12:
            ts /= 1000.0
        try:
            return datetime.fromtimestamp(ts, tz=timezone.utc).date()
        except (OverflowError, OSError, ValueError):
            return None

    text = str(value).strip()
    # ISO datetime
    try:
        if text.endswith("Z"):
            text_iso = text[:-1] + "+00:00"
        else:
            text_iso = text
        return datetime.fromisoformat(text_iso).astimezone(timezone.utc).date()
    except ValueError:
        pass

    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return datetime.strptime(text[:10] if len(text) >= 10 and fmt == "%Y-%m-%d" else text, fmt).date()
        except ValueError:
            continue
    # date-only prefix
    m = re.match(r"(\d{4}-\d{2}-\d{2})", text)
    if m:
        try:
            return date.fromisoformat(m.group(1))
        except ValueError:
            return None
    return None


def map_row(
    row: dict[str, Any],
    *,
    play_package_id: str,
) -> tuple[Review | None, str | None]:
    """
    Map a raw row to Review.
    Returns (review, skip_reason). skip_reason is None on success.
    """
    package = _get(row, "package_name", "package", "app_id", "appid")
    if package is not None and str(package).strip() and str(package).strip() != play_package_id:
        return None, "wrong_package"

    store = parse_store(_get(row, "store", "source", "platform"))
    if store is None:
        return None, "unknown_store"
    if store == "app_store":
        return None, "app_store_out_of_scope"

    rating = parse_rating(_get(row, "rating", "score", "star", "stars"))
    if rating is None:
        return None, "invalid_rating"

    raw_text = _get(row, "text", "body", "content", "review", "review_text", "comment")
    if raw_text is None:
        return None, "empty_text"
    text = html.unescape(str(raw_text)).strip()
    if not text:
        return None, "empty_text"

    parsed_date = parse_date(_get(row, "date", "at", "review_date", "created_at", "time"))
    if parsed_date is None:
        return None, "invalid_date"

    title_val = _get(row, "title", "review_title", "heading")
    title = html.unescape(str(title_val)).strip() if title_val is not None else ""

    locale_val = _get(row, "locale", "lang", "language", "country")
    locale = str(locale_val).strip() if locale_val is not None else ""

    export_id = _get(row, "review_id", "reviewid", "id", "reviewId")
    date_str = parsed_date.isoformat()
    scrubbed = scrub_text(text)
    residual = (
        scrubbed.replace("[email]", "")
        .replace("[phone]", "")
        .replace("[upi]", "")
        .replace("[device_id]", "")
        .replace("[account]", "")
        .strip()
    )
    if not residual:
        return None, "pii_only_text"

    review_id = stable_id(
        store=store,
        date_str=date_str,
        text=scrubbed,
        export_id=str(export_id) if export_id is not None else None,
    )

    return (
        Review(
            id=review_id,
            store=store,
            rating=rating,
            title=scrub_text(title) if title else "",
            text=scrubbed,
            date=date_str,
            locale=locale,
        ),
        None,
    )
