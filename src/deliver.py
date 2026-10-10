"""
Phase 5–6 only: publish existing pulse.md to Docs and send Gmail.

Use after a successful local pulse when you want to retry delivery without
re-running ingest/theme.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from src.config.settings import SettingsError, load_settings
from src.mcp.artifacts import patch_pulse_json
from src.mcp.client import McpError, McpHttpClient
from src.mcp.docs import DocsPublishError, DocsPublisher
from src.mcp.gmail import GmailNotifyError, GmailNotifier, build_email_body


class DeliverError(RuntimeError):
    """Docs/Gmail delivery failed."""


def run_deliver(
    settings=None,
    *,
    pulse_md: Path | None = None,
    pulse_json: Path | None = None,
    skip_email: bool = False,
    mcp_client=None,
) -> dict:
    cfg = settings if settings is not None else load_settings()
    md_path = Path(pulse_md) if pulse_md else cfg.output_dir / "pulse.md"
    json_path = Path(pulse_json) if pulse_json else cfg.output_dir / "pulse.json"

    if not md_path.exists():
        raise DeliverError(f"Missing {md_path}. Run: python -m src run --local-only")
    if not json_path.exists():
        raise DeliverError(f"Missing {json_path}. Run: python -m src pulse")

    payload = json.loads(json_path.read_text(encoding="utf-8"))
    week_ending = str(payload.get("week_ending") or "")
    if not week_ending:
        raise DeliverError("pulse.json missing week_ending")

    pulse_text = md_path.read_text(encoding="utf-8")
    client = mcp_client or McpHttpClient(base_url=cfg.mcp_base_url)

    try:
        client.health()
        published = DocsPublisher(client).publish(
            pulse_text,
            week_ending=week_ending,
            title_template=cfg.doc_title_template,
            document_id=cfg.google_doc_id or None,
            document_url=cfg.google_doc_url or None,
        )
    except (McpError, DocsPublishError) as exc:
        raise DeliverError(f"Docs publish failed: {exc}") from exc

    patch_pulse_json(
        json_path,
        doc_url=published.doc_url,
        document_id=published.document_id,
        docs_request_id=published.request_id,
    )

    result = {
        "week_ending": week_ending,
        "doc_url": published.doc_url,
        "document_id": published.document_id,
        "docs_request_id": published.request_id,
        "email": None,
    }

    if skip_email:
        return result

    try:
        subject = cfg.doc_title_template.format(week_ending=week_ending)
        body = build_email_body(
            week_ending=week_ending,
            doc_url=published.doc_url,
            pulse_markdown=pulse_text,
            include_full_pulse=cfg.include_full_pulse_in_email,
        )
        mailed = GmailNotifier(client).notify(
            to=cfg.email_recipient,
            subject=subject,
            body=body,
            week_ending=week_ending,
        )
    except (McpError, GmailNotifyError) as exc:
        raise DeliverError(f"Gmail notify failed (Doc already appended): {exc}") from exc

    email_meta = {
        "status": mailed.status,
        "recipient": cfg.email_recipient,
        "request_id": mailed.request_id,
        "message_id": mailed.message_id,
        "thread_id": mailed.thread_id,
    }
    patch_pulse_json(json_path, email=email_meta)
    result["email"] = email_meta
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Deliver existing pulse.md via Docs MCP + Gmail MCP",
    )
    parser.add_argument("--config", default=None, help="Path to settings.yaml")
    parser.add_argument("--pulse-md", default=None, help="Override pulse.md path")
    parser.add_argument("--pulse-json", default=None, help="Override pulse.json path")
    parser.add_argument(
        "--docs-only",
        action="store_true",
        help="Append to Google Doc only (skip email)",
    )
    args = parser.parse_args(argv)

    try:
        settings = load_settings(Path(args.config) if args.config else None)
        result = run_deliver(
            settings,
            pulse_md=Path(args.pulse_md) if args.pulse_md else None,
            pulse_json=Path(args.pulse_json) if args.pulse_json else None,
            skip_email=args.docs_only,
        )
    except (SettingsError, DeliverError) as exc:
        print(f"Deliver error: {exc}", file=sys.stderr)
        return 1

    print(f"Deliver OK — week ending {result['week_ending']}")
    print(f"  doc: {result['doc_url']}")
    if result.get("email"):
        em = result["email"]
        print(f"  email: {em['status']} → {em['recipient']}")
        if em.get("message_id"):
            print(f"  message_id: {em['message_id']}")
    elif args.docs_only:
        print("  email: skipped (--docs-only)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
