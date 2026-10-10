"""Tests for scripts/sync_frontend_data.py."""

from __future__ import annotations

import json
from pathlib import Path

from scripts.sync_frontend_data import build_reviews_fixture, sync


def test_sync_writes_pulse_and_reviews(tmp_path: Path) -> None:
    pulse = {
        "week_ending": "2026-10-10",
        "themes": [{"theme_id": "kyc", "label": "KYC / verification", "count": 1}],
        "quotes": [],
        "actions": [],
    }
    reviews = {
        "reviews": [
            {
                "id": "r1",
                "rating": 1,
                "text": "KYC stuck",
                "date": "2026-10-01",
                "locale": "en_IN",
            }
        ]
    }
    themes = {
        "themes": [
            {
                "theme_id": "kyc",
                "label": "KYC / verification",
                "review_ids": ["r1"],
            }
        ]
    }

    pulse_path = tmp_path / "pulse.json"
    reviews_path = tmp_path / "reviews.json"
    themes_path = tmp_path / "themes.json"
    out_dir = tmp_path / "out"
    pulse_path.write_text(json.dumps(pulse), encoding="utf-8")
    reviews_path.write_text(json.dumps(reviews), encoding="utf-8")
    themes_path.write_text(json.dumps(themes), encoding="utf-8")

    pulse_out, reviews_out = sync(
        pulse_path=pulse_path,
        reviews_path=reviews_path,
        themes_path=themes_path,
        out_dir=out_dir,
    )

    assert pulse_out.is_file()
    assert reviews_out is not None and reviews_out.is_file()
    synced_reviews = json.loads(reviews_out.read_text(encoding="utf-8"))
    assert synced_reviews[0]["theme_id"] == "kyc"
    assert synced_reviews[0]["theme_label"] == "KYC / verification"


def test_build_reviews_fixture_marks_unmapped_as_other(tmp_path: Path) -> None:
    reviews_path = tmp_path / "reviews.json"
    themes_path = tmp_path / "themes.json"
    reviews_path.write_text(
        json.dumps(
            {
                "reviews": [
                    {
                        "id": "x",
                        "rating": 5,
                        "text": "Great app",
                        "date": "2026-09-01",
                        "locale": "en_IN",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )
    themes_path.write_text(json.dumps({"themes": []}), encoding="utf-8")
    rows = build_reviews_fixture(reviews_path, themes_path)
    assert rows[0]["theme_id"] == "other"
