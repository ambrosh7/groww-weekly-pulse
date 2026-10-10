"""Phase 7: acceptance regression + deliver retry path."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.config.settings import Settings
from src.deliver import DeliverError, run_deliver
from src.orchestrator.run import run_weekly_pulse
from src.pulse.gates import find_pii_hits

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE = REPO_ROOT / "data" / "raw" / "groww_play_reviews_sample.csv"
NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


class FakeMcp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []

    def health(self) -> dict[str, Any]:
        return {"status": "ok"}

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, arguments))
        if name == "google_docs_append_text":
            return {
                "success": True,
                "document_id": "DOC99",
                "document_url": "https://docs.google.com/document/d/DOC99/edit",
                "request_id": arguments.get("request_id"),
            }
        if name == "gmail_send_email":
            return {
                "success": True,
                "message_id": "m-99",
                "request_id": arguments.get("request_id"),
            }
        raise RuntimeError(name)


def _settings(tmp_path: Path) -> Settings:
    s = Settings(
        product_name="Groww",
        play_package_id="com.nextbillion.groww",
        window_weeks=10,
        max_themes=5,
        raw_dir=tmp_path / "raw",
        processed_dir=tmp_path / "processed",
        output_dir=tmp_path / "output",
        default_raw_file=SAMPLE,
        min_review_words=8,
        drop_emoji_reviews=True,
        require_english=True,
        quotes_per_theme=3,
        email_recipient="ops@example.com",
        google_doc_id="DOC99",
    )
    s.processed_dir.mkdir(parents=True)
    s.output_dir.mkdir(parents=True)
    return s


def test_sample_acceptance_checklist(tmp_path: Path):
    """Problem-statement hard checks on sample golden path (local)."""
    settings = _settings(tmp_path)
    result = run_weekly_pulse(
        settings, raw_path=SAMPLE, now=NOW, publish=False, notify=False
    )
    assert result.theme_count == 3
    assert 8 <= result.window_weeks <= 12
    assert result.word_count <= 250

    payload = json.loads(result.pulse_json_path.read_text(encoding="utf-8"))
    assert len(payload["themes"]) == 3
    assert len(payload["quotes"]) == 3
    assert len(payload["actions"]) == 3
    assert payload["word_count"] <= 250
    assert find_pii_hits(result.pulse_path.read_text(encoding="utf-8")) == []

    themes_path = settings.processed_dir / "themes.json"
    themes = json.loads(themes_path.read_text(encoding="utf-8"))
    assert 1 <= themes["meta"]["theme_count"] <= 5


def test_deliver_from_existing_pulse(tmp_path: Path):
    settings = _settings(tmp_path)
    run_weekly_pulse(settings, raw_path=SAMPLE, now=NOW, publish=False, notify=False)
    fake = FakeMcp()
    out = run_deliver(settings, mcp_client=fake)
    assert out["doc_url"].endswith("DOC99/edit")
    assert out["email"]["message_id"] == "m-99"
    assert [c[0] for c in fake.calls] == [
        "google_docs_append_text",
        "gmail_send_email",
    ]
    payload = json.loads((settings.output_dir / "pulse.json").read_text(encoding="utf-8"))
    assert payload["doc_url"]
    assert payload["email"]["status"] == "sent"


def test_deliver_docs_only(tmp_path: Path):
    settings = _settings(tmp_path)
    run_weekly_pulse(settings, raw_path=SAMPLE, now=NOW, publish=False, notify=False)
    fake = FakeMcp()
    out = run_deliver(settings, mcp_client=fake, skip_email=True)
    assert out["email"] is None
    assert [c[0] for c in fake.calls] == ["google_docs_append_text"]


def test_deliver_missing_pulse_fails(tmp_path: Path):
    settings = _settings(tmp_path)
    with pytest.raises(DeliverError, match="Missing"):
        run_deliver(settings, mcp_client=FakeMcp())
