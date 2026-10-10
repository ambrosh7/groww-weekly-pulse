#!/usr/bin/env python3
"""Write config/settings.yaml for CI from environment variables (no secrets in git)."""

from __future__ import annotations

import os
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "config" / "settings.yaml"


def main() -> None:
    email = os.environ.get("EMAIL_RECIPIENT", "").strip()
    doc_id = os.environ.get("GOOGLE_DOC_ID", "").strip()
    doc_url = os.environ.get("GOOGLE_DOC_URL", "").strip()
    mcp_base = os.environ.get(
        "MCP_BASE_URL",
        "https://gmail-docs-mcp-server-production.up.railway.app",
    ).strip()
    window_weeks = int(os.environ.get("WINDOW_WEEKS", "10"))
    deliver = os.environ.get("DELIVER", "true").lower() in {"1", "true", "yes"}

    if deliver and not email:
        raise SystemExit("EMAIL_RECIPIENT secret/var is required when DELIVER=true")
    if deliver and not (doc_id or doc_url):
        raise SystemExit(
            "GOOGLE_DOC_ID or GOOGLE_DOC_URL is required when DELIVER=true"
        )

    data = {
        "product_name": "Groww",
        "play_package_id": "com.nextbillion.groww",
        "window_weeks": window_weeks,
        "min_review_words": 8,
        "drop_emoji_reviews": True,
        "require_english": True,
        "max_themes": 5,
        "quotes_per_theme": 3,
        "pulse_top_themes": 3,
        "quote_count": 3,
        "action_count": 3,
        "max_pulse_words": 250,
        "email_recipient": email or "you@example.com",
        "doc_title_template": "Groww Weekly Pulse — {week_ending}",
        "mcp_base_url": mcp_base,
        "google_doc_id": doc_id,
        "google_doc_url": doc_url,
        "publish_to_docs": deliver,
        "send_email": deliver,
        "include_full_pulse_in_email": True,
        "allow_soft_fail": False,
        "clustering_approach": "keyword_seed",
        "paths": {
            "raw_dir": "data/raw",
            "processed_dir": "data/processed",
            "output_dir": "data/output",
            "default_raw_file": "data/raw/groww_play_reviews.csv",
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    print(f"Wrote {OUT} (deliver={deliver}, doc_set={bool(doc_id or doc_url)})")


if __name__ == "__main__":
    main()
