"""
Local + MCP orchestrator — ingest → theme → pulse → Docs append → Gmail send.

Phases 5–6 call gmail-docs-mcp-server tools only (no Google REST in this app).
Failures short-circuit; Docs failure blocks Gmail.
"""

from __future__ import annotations

import logging
import sys
from dataclasses import dataclass, replace
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, TextIO

from src.config.settings import (
    WINDOW_WEEKS_MAX,
    WINDOW_WEEKS_MIN,
    Settings,
    SettingsError,
    load_settings,
    validate_window_weeks,
)
from src.ingest.load import IngestError
from src.ingest.run import run_ingest
from src.mcp.artifacts import patch_pulse_json
from src.mcp.client import McpClient, McpError, McpHttpClient
from src.mcp.docs import DocsPublishError, DocsPublisher
from src.mcp.gmail import GmailNotifyError, GmailNotifier, build_email_body
from src.normalize.pipeline import EmptyCorpusError
from src.pulse.gates import PulseGateError
from src.pulse.run import PulseError, remove_pulse_artifacts, run_pulse
from src.theme.run import ThemeError, run_theme

logger = logging.getLogger(__name__)


class OrchestratorError(RuntimeError):
    """Weekly pulse pipeline failed."""


@dataclass
class WeeklyPulseResult:
    """Pipeline result. doc_url / email fields filled when delivery runs."""

    pulse_path: Path
    pulse_json_path: Path
    reviews_path: Path
    themes_path: Path
    theme_count: int
    review_count: int
    word_count: int
    week_ending: str
    window_weeks: int
    doc_url: str | None = None
    document_id: str | None = None
    message_id: str | None = None
    draft_id: str | None = None  # unused (MCP sends mail; kept for API stability)
    source_fixture: str | None = None
    email_recipient: str | None = None
    stages_completed: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "pulse_path": str(self.pulse_path),
            "pulse_json_path": str(self.pulse_json_path),
            "reviews_path": str(self.reviews_path),
            "themes_path": str(self.themes_path),
            "theme_count": self.theme_count,
            "review_count": self.review_count,
            "word_count": self.word_count,
            "week_ending": self.week_ending,
            "window_weeks": self.window_weeks,
            "doc_url": self.doc_url,
            "document_id": self.document_id,
            "message_id": self.message_id,
            "draft_id": self.draft_id,
            "source_fixture": self.source_fixture,
            "email_recipient": self.email_recipient,
            "stages_completed": list(self.stages_completed),
        }


def _log(msg: str, *, sink: Callable[[str], None] | None = None) -> None:
    logger.info(msg)
    if sink is not None:
        sink(msg)


def _make_mcp_client(settings: Settings, client: McpClient | None) -> McpClient:
    if client is not None:
        return client
    return McpHttpClient(base_url=settings.mcp_base_url)


def run_weekly_pulse(
    settings: Settings | None = None,
    *,
    window_weeks: int | None = None,
    recipient: str | None = None,
    raw_path: Path | None = None,
    now: datetime | None = None,
    log: Callable[[str], None] | None = None,
    publish: bool | None = None,
    notify: bool | None = None,
    mcp_client: McpClient | None = None,
) -> WeeklyPulseResult:
    """
    Run Stages 1–3 + gates, optionally Docs append (Phase 5) and Gmail send (Phase 6).

    `publish` / `notify` override settings when not None.
    Notify requires a successful Docs publish in the same run.
    """
    cfg = settings if settings is not None else load_settings()

    if window_weeks is not None:
        weeks = validate_window_weeks(window_weeks)
        cfg = replace(cfg, window_weeks=weeks)

    if recipient is not None:
        cfg = replace(cfg, email_recipient=str(recipient))

    do_publish = cfg.publish_to_docs if publish is None else bool(publish)
    do_notify = cfg.send_email if notify is None else bool(notify)

    if do_notify and not do_publish:
        raise OrchestratorError(
            "Gmail notify requires Docs publish in the same run "
            "(enable publish_to_docs / --publish-docs / --deliver)"
        )

    reviews_path = cfg.processed_dir / "reviews.json"
    themes_path = cfg.processed_dir / "themes.json"
    stages: list[str] = []

    _log(
        f"Orchestrator start — window_weeks={cfg.window_weeks} "
        f"raw={raw_path or cfg.default_raw_file} "
        f"publish={do_publish} notify={do_notify}",
        sink=log,
    )

    try:
        ingest_result = run_ingest(cfg, raw_path=raw_path, now=now)
    except (IngestError, EmptyCorpusError, SettingsError, OSError) as exc:
        raise OrchestratorError(f"Ingest failed: {exc}") from exc

    stages.append("ingest")
    _log(
        f"Ingest OK — kept={ingest_result.stats['kept']} → {reviews_path}",
        sink=log,
    )

    try:
        theme_result = run_theme(cfg, reviews_path=reviews_path)
    except (ThemeError, ValueError, RuntimeError, OSError) as exc:
        raise OrchestratorError(f"Theme failed: {exc}") from exc

    stages.append("theme")
    _log(
        f"Theme OK — themes={theme_result.stats['theme_count']} → {themes_path}",
        sink=log,
    )

    try:
        pulse_result = run_pulse(
            cfg,
            reviews_path=reviews_path,
            themes_path=themes_path,
            output_dir=cfg.output_dir,
        )
    except (PulseError, PulseGateError, ThemeError, OSError) as exc:
        remove_pulse_artifacts(cfg.output_dir)
        raise OrchestratorError(f"Pulse failed: {exc}") from exc

    stages.append("pulse")
    _log(f"Pulse OK — {pulse_result.md_path}", sink=log)
    _log(f"Pulse OK — {pulse_result.json_path}", sink=log)

    doc_url: str | None = None
    document_id: str | None = None
    message_id: str | None = None
    week_ending = str(pulse_result.stats["week_ending"])
    pulse_md = pulse_result.md_path.read_text(encoding="utf-8")

    if do_publish:
        try:
            client = _make_mcp_client(cfg, mcp_client)
            client.health()
            publisher = DocsPublisher(client)
            published = publisher.publish(
                pulse_md,
                week_ending=week_ending,
                title_template=cfg.doc_title_template,
                document_id=cfg.google_doc_id or None,
                document_url=cfg.google_doc_url or None,
            )
        except (McpError, DocsPublishError, OSError) as exc:
            raise OrchestratorError(f"Docs publish failed: {exc}") from exc

        doc_url = published.doc_url
        document_id = published.document_id
        patch_pulse_json(
            pulse_result.json_path,
            doc_url=doc_url,
            document_id=document_id,
            docs_request_id=published.request_id,
        )
        stages.append("docs")
        _log(f"Docs OK — appended → {doc_url}", sink=log)

    if do_notify:
        if not doc_url:
            raise OrchestratorError("Gmail notify blocked: Docs publish did not yield doc_url")
        try:
            client = _make_mcp_client(cfg, mcp_client)
            notifier = GmailNotifier(client)
            subject = cfg.doc_title_template.format(week_ending=week_ending)
            body = build_email_body(
                week_ending=week_ending,
                doc_url=doc_url,
                pulse_markdown=pulse_md,
                include_full_pulse=cfg.include_full_pulse_in_email,
            )
            mailed = notifier.notify(
                to=cfg.email_recipient,
                subject=subject,
                body=body,
                week_ending=week_ending,
            )
        except (McpError, GmailNotifyError, OSError) as exc:
            raise OrchestratorError(f"Gmail notify failed: {exc}") from exc

        message_id = mailed.message_id
        patch_pulse_json(
            pulse_result.json_path,
            email={
                "status": mailed.status,
                "recipient": cfg.email_recipient,
                "request_id": mailed.request_id,
                "message_id": mailed.message_id,
                "thread_id": mailed.thread_id,
            },
        )
        stages.append("gmail")
        _log(
            f"Gmail OK — sent to {cfg.email_recipient}"
            + (f" message_id={message_id}" if message_id else ""),
            sink=log,
        )

    result = WeeklyPulseResult(
        pulse_path=pulse_result.md_path,
        pulse_json_path=pulse_result.json_path,
        reviews_path=reviews_path,
        themes_path=themes_path,
        theme_count=int(pulse_result.stats["theme_count"]),
        review_count=int(pulse_result.stats["review_count"]),
        word_count=int(pulse_result.stats["word_count"]),
        week_ending=week_ending,
        window_weeks=cfg.window_weeks,
        doc_url=doc_url,
        document_id=document_id,
        message_id=message_id,
        draft_id=None,
        source_fixture=pulse_result.stats.get("source_fixture"),
        email_recipient=cfg.email_recipient,
        stages_completed=tuple(stages),
    )
    _log(
        f"Orchestrator done — week ending {result.week_ending} · "
        f"{result.theme_count} themes · {result.word_count} words · "
        f"stages={list(result.stages_completed)}",
        sink=log,
    )
    return result


def build_orchestrator_parser():
    """Argparse for `python -m src.orchestrator` and `python -m src run`."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Run Groww weekly pulse (ingest → theme → pulse → optional Docs/Gmail)",
    )
    parser.add_argument(
        "-i",
        "--input",
        help="Raw Play CSV/JSON (default: prefer groww_play_reviews.csv in data/raw)",
    )
    parser.add_argument(
        "--weeks",
        type=int,
        default=None,
        help=f"Review lookback weeks ({WINDOW_WEEKS_MIN}–{WINDOW_WEEKS_MAX}; "
        "overrides config)",
    )
    parser.add_argument(
        "--recipient",
        default=None,
        help="Email recipient for Gmail notify (overrides config)",
    )
    parser.add_argument(
        "--config",
        default=None,
        help="Path to settings YAML (default: settings.yaml or settings.example.yaml)",
    )
    parser.add_argument(
        "--deliver",
        action="store_true",
        help="Enable Docs append + Gmail send (requires MCP_HTTP_BEARER_TOKEN + doc id)",
    )
    parser.add_argument(
        "--publish-docs",
        action="store_true",
        help="Append pulse to configured Google Doc via MCP",
    )
    parser.add_argument(
        "--send-email",
        action="store_true",
        help="Send pulse email via MCP (requires Docs publish in same run)",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="Force skip Docs/Gmail even if enabled in settings",
    )
    return parser


def cmd_run(
    args,
    *,
    stdout: TextIO | None = None,
    stderr: TextIO | None = None,
) -> int:
    """CLI handler shared by `src run` and `src.orchestrator`."""
    out = stdout or sys.stdout
    err = stderr or sys.stderr

    try:
        settings = load_settings(Path(args.config) if getattr(args, "config", None) else None)
    except SettingsError as exc:
        print(f"Config error: {exc}", file=err)
        return 1

    if getattr(args, "weeks", None) is not None:
        try:
            validate_window_weeks(args.weeks)
        except SettingsError as exc:
            print(f"Config error: {exc}", file=err)
            return 1

    publish: bool | None = None
    notify: bool | None = None
    if getattr(args, "local_only", False):
        publish, notify = False, False
    elif getattr(args, "deliver", False):
        publish, notify = True, True
    else:
        if getattr(args, "publish_docs", False):
            publish = True
        if getattr(args, "send_email", False):
            notify = True
            if publish is None:
                publish = True  # notify implies publish

    def _sink(msg: str) -> None:
        print(msg, file=out)

    try:
        result = run_weekly_pulse(
            settings,
            window_weeks=args.weeks,
            recipient=args.recipient,
            raw_path=Path(args.input) if args.input else None,
            log=_sink,
            publish=publish,
            notify=notify,
        )
    except OrchestratorError as exc:
        print(f"Orchestrator error: {exc}", file=err)
        return 1

    print(
        f"Weekly pulse OK — week ending {result.week_ending} · "
        f"{result.review_count} reviews · {result.theme_count} themes · "
        f"{result.word_count} words",
        file=out,
    )
    if result.source_fixture:
        print(f"  source_fixture: {result.source_fixture}", file=out)
    print(f"  stages:  {', '.join(result.stages_completed)}", file=out)
    print(f"  reviews: {result.reviews_path}", file=out)
    print(f"  themes:  {result.themes_path}", file=out)
    print(f"  pulse:   {result.pulse_path}", file=out)
    print(f"  pulse:   {result.pulse_json_path}", file=out)
    if result.doc_url:
        print(f"  doc:     {result.doc_url}", file=out)
    if result.message_id:
        print(f"  email:   sent message_id={result.message_id}", file=out)
    elif "gmail" in result.stages_completed:
        print(f"  email:   sent to {result.email_recipient}", file=out)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = build_orchestrator_parser()
    args = parser.parse_args(argv)
    return cmd_run(args)
