"""Phase 1: ingest mapping, window filter, PII scrub."""

from datetime import date, datetime, timezone
from pathlib import Path

import pytest

from src.ingest.load import IngestError, load_raw_file
from src.normalize.pii import scrub_text
from src.normalize.pipeline import EmptyCorpusError, normalize_rows, window_bounds
from src.normalize.schema import map_row, stable_id

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE = REPO_ROOT / "data" / "raw" / "groww_play_reviews_sample.csv"
PACKAGE = "com.nextbillion.groww"
NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


def test_scrub_email_phone_device():
    text = "Mail me at user@example.com or call 9876543210 device android:abc12345deadbeef"
    cleaned = scrub_text(text)
    assert "user@example.com" not in cleaned
    assert "9876543210" not in cleaned
    assert "[email]" in cleaned
    assert "[phone]" in cleaned


def test_map_row_happy_path():
    review, reason = map_row(
        {
            "review_id": "abc",
            "package_name": PACKAGE,
            "store": "play",
            "rating": "4",
            "title": "",
            "text": "KYC is slow",
            "date": "2026-09-01",
            "locale": "en_IN",
        },
        play_package_id=PACKAGE,
    )
    assert reason is None
    assert review is not None
    assert review.store == "play"
    assert review.rating == 4
    assert review.text == "KYC is slow"


def test_skip_app_store_and_empty_text():
    _, reason = map_row(
        {"store": "app_store", "rating": 1, "text": "hi", "date": "2026-09-01"},
        play_package_id=PACKAGE,
    )
    assert reason == "app_store_out_of_scope"

    _, reason2 = map_row(
        {"store": "play", "rating": 1, "text": "  ", "date": "2026-09-01"},
        play_package_id=PACKAGE,
    )
    assert reason2 == "empty_text"


def test_skip_invalid_rating():
    _, reason = map_row(
        {"store": "play", "rating": 6, "text": "ok", "date": "2026-09-01"},
        play_package_id=PACKAGE,
    )
    assert reason == "invalid_rating"


def test_window_filter_and_empty_corpus():
    rows = [
        {
            "store": "play",
            "rating": 2,
            "text": "old review that has more than eight words in the body",
            "date": "2025-01-01",
        }
    ]
    with pytest.raises(EmptyCorpusError):
        normalize_rows(rows, play_package_id=PACKAGE, window_weeks=10, now=NOW)


def test_app_store_only_message():
    rows = [
        {
            "store": "ios",
            "rating": 2,
            "text": "this app store review has more than eight words total",
            "date": "2026-09-01",
        },
        {
            "store": "app_store",
            "rating": 1,
            "text": "another ios review with more than eight words here",
            "date": "2026-09-02",
        },
    ]
    with pytest.raises(EmptyCorpusError, match="App Store"):
        normalize_rows(rows, play_package_id=PACKAGE, window_weeks=10, now=NOW)


def test_too_few_words_skipped():
    rows = [
        {
            "store": "play",
            "rating": 2,
            "text": "too short",
            "date": "2026-09-01",
        },
        {
            "store": "play",
            "rating": 1,
            "text": "this review clearly has more than eight words in it",
            "date": "2026-09-02",
        },
    ]
    result = normalize_rows(
        rows, play_package_id=PACKAGE, window_weeks=10, min_review_words=8, now=NOW
    )
    assert result.stats["kept"] == 1
    assert result.stats["skipped"]["too_few_words"] == 1


def test_normalize_sample_csv():
    rows = load_raw_file(SAMPLE)
    result = normalize_rows(
        rows, play_package_id=PACKAGE, window_weeks=10, min_review_words=8, now=NOW
    )
    assert result.stats["kept"] > 0
    start, end = window_bounds(10, now=NOW)
    assert end == date(2026, 10, 10)
    assert start == date(2026, 8, 1)
    for review in result.reviews:
        d = date.fromisoformat(review.date)
        assert start <= d <= end
        assert review.store == "play"


def test_stable_ids_are_stable():
    a = stable_id(store="play", date_str="2026-09-01", text="hello", export_id="r1")
    b = stable_id(store="play", date_str="2026-09-01", text="hello", export_id="r1")
    assert a == b


def test_pii_only_text_skipped():
    _, reason = map_row(
        {
            "store": "play",
            "rating": 1,
            "text": "user@example.com",
            "date": "2026-09-01",
        },
        play_package_id=PACKAGE,
    )
    assert reason == "pii_only_text"


def test_unsupported_extension(tmp_path: Path):
    bad = tmp_path / "reviews.xlsx"
    bad.write_bytes(b"not-a-csv")
    with pytest.raises(IngestError, match="Unsupported"):
        load_raw_file(bad)


def test_future_dates_dropped():
    rows = [
        {
            "store": "play",
            "rating": 3,
            "text": "this future dated review has more than eight words",
            "date": "2026-12-01",
        },
        {
            "store": "play",
            "rating": 2,
            "text": "this in-window review has more than eight words too",
            "date": "2026-09-01",
        },
    ]
    result = normalize_rows(
        rows, play_package_id=PACKAGE, window_weeks=10, min_review_words=8, now=NOW
    )
    assert result.stats["kept"] == 1
    assert "in-window" in result.reviews[0].text
