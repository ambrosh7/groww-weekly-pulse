"""Phases 5–6: Docs append + Gmail send via MCP adapters (mocked HTTP)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pytest

from src.config.settings import Settings
from src.mcp.artifacts import patch_pulse_json
from src.mcp.client import McpError, _normalize_tool_result, _parse_sse_jsonrpc
from src.mcp.docs import DocsPublisher, extract_document_id
from src.mcp.gmail import GmailNotifier, build_email_body
from src.orchestrator.run import OrchestratorError, run_weekly_pulse

REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE = REPO_ROOT / "data" / "raw" / "groww_play_reviews_sample.csv"
NOW = datetime(2026, 10, 10, 12, 0, tzinfo=timezone.utc)


class FakeMcp:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.fail_tool: str | None = None

    def health(self) -> dict[str, Any]:
        return {"status": "ok"}

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        self.calls.append((name, arguments))
        if self.fail_tool == name:
            raise McpError(f"simulated failure for {name}")
        if name == "google_docs_append_text":
            doc_id = arguments.get("document_id") or "DOC123"
            return {
                "success": True,
                "message": "Content appended successfully.",
                "document_id": doc_id,
                "document_url": f"https://docs.google.com/document/d/{doc_id}/edit",
                "insertion_index": 1,
                "request_id": arguments.get("request_id"),
            }
        if name == "gmail_send_email":
            return {
                "success": True,
                "message": "Email sent successfully.",
                "message_id": "msg-1",
                "thread_id": "thr-1",
                "request_id": arguments.get("request_id"),
            }
        raise McpError(f"unknown tool {name}")


def _settings(tmp_path: Path, **overrides: Any) -> Settings:
    base = dict(
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
        pulse_top_themes=3,
        quote_count=3,
        action_count=3,
        max_pulse_words=250,
        allow_soft_fail=False,
        email_recipient="ops@example.com",
        google_doc_id="DOC123",
        publish_to_docs=False,
        send_email=False,
        mcp_base_url="https://example.test",
    )
    base.update(overrides)
    settings = Settings(**base)
    settings.processed_dir.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    return settings


def test_extract_document_id_from_url():
    assert (
        extract_document_id(
            document_id=None,
            document_url="https://docs.google.com/document/d/abcXYZ/edit",
        )
        == "abcXYZ"
    )


def test_docs_publisher_calls_append_tool():
    fake = FakeMcp()
    pub = DocsPublisher(fake)
    result = pub.publish(
        "# Pulse\n\nHello\n",
        week_ending="2026-10-09",
        document_id="DOC123",
    )
    assert result.document_id == "DOC123"
    assert "DOC123" in result.doc_url
    assert result.request_id == "groww-pulse-docs-2026-10-09"
    name, args = fake.calls[0]
    assert name == "google_docs_append_text"
    assert args["prepend_newline"] is True
    assert args["heading"] == "Groww Weekly Pulse — 2026-10-09"
    assert "Hello" in args["text"]


def test_gmail_notifier_and_body():
    fake = FakeMcp()
    body = build_email_body(
        week_ending="2026-10-09",
        doc_url="https://docs.google.com/document/d/DOC123/edit",
        pulse_markdown="# Pulse\n",
    )
    assert "DOC123" in body
    assert "Pulse" in body
    mailed = GmailNotifier(fake).notify(
        to="ops@example.com",
        subject="Groww Weekly Pulse — week ending 2026-10-09",
        body=body,
        week_ending="2026-10-09",
    )
    assert mailed.status == "sent"
    assert mailed.message_id == "msg-1"
    assert fake.calls[0][0] == "gmail_send_email"
    assert fake.calls[0][1]["request_id"] == "groww-pulse-mail-2026-10-09"


def test_orchestrator_deliver_docs_then_gmail(tmp_path: Path):
    settings = _settings(tmp_path)
    fake = FakeMcp()
    result = run_weekly_pulse(
        settings,
        raw_path=SAMPLE,
        now=NOW,
        publish=True,
        notify=True,
        mcp_client=fake,
    )
    assert result.stages_completed == ("ingest", "theme", "pulse", "docs", "gmail")
    assert result.doc_url and "DOC123" in result.doc_url
    assert result.message_id == "msg-1"
    payload = json.loads(result.pulse_json_path.read_text(encoding="utf-8"))
    assert payload["doc_url"] == result.doc_url
    assert payload["document_id"] == "DOC123"
    assert payload["email"]["status"] == "sent"
    tools = [c[0] for c in fake.calls]
    assert tools == ["google_docs_append_text", "gmail_send_email"]


def test_docs_failure_blocks_gmail(tmp_path: Path):
    settings = _settings(tmp_path)
    fake = FakeMcp()
    fake.fail_tool = "google_docs_append_text"
    with pytest.raises(OrchestratorError, match="Docs publish failed"):
        run_weekly_pulse(
            settings,
            raw_path=SAMPLE,
            now=NOW,
            publish=True,
            notify=True,
            mcp_client=fake,
        )
    assert all(name != "gmail_send_email" for name, _ in fake.calls)


def test_notify_without_publish_rejected(tmp_path: Path):
    settings = _settings(tmp_path)
    with pytest.raises(OrchestratorError, match="requires Docs publish"):
        run_weekly_pulse(
            settings,
            raw_path=SAMPLE,
            now=NOW,
            publish=False,
            notify=True,
            mcp_client=FakeMcp(),
        )


def test_local_only_skips_mcp(tmp_path: Path):
    settings = _settings(tmp_path, publish_to_docs=True, send_email=True)
    fake = FakeMcp()
    result = run_weekly_pulse(
        settings,
        raw_path=SAMPLE,
        now=NOW,
        publish=False,
        notify=False,
        mcp_client=fake,
    )
    assert result.stages_completed == ("ingest", "theme", "pulse")
    assert fake.calls == []


def test_patch_pulse_json(tmp_path: Path):
    path = tmp_path / "pulse.json"
    path.write_text('{"week_ending": "2026-10-09", "doc_url": null}\n', encoding="utf-8")
    patch_pulse_json(path, doc_url="https://docs.google.com/document/d/X/edit", document_id="X")
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["doc_url"].endswith("/X/edit")
    assert data["document_id"] == "X"


def test_parse_sse_and_normalize():
    sse = (
        "event: message\n"
        'data: {"jsonrpc":"2.0","id":1,"result":{"structuredContent":{"ok":true},"content":[]}}\n\n'
    )
    parsed = _parse_sse_jsonrpc(sse)
    assert parsed["result"]["structuredContent"]["ok"] is True
    norm = _normalize_tool_result(
        {
            "content": [{"type": "text", "text": '{"success": true, "document_id": "D"}'}],
        }
    )
    assert norm["document_id"] == "D"
