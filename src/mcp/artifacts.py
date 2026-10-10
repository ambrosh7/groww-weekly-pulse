"""Patch pulse.json after Docs / Gmail delivery (Phases 5–6)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def patch_pulse_json(
    path: Path,
    *,
    doc_url: str | None = None,
    document_id: str | None = None,
    docs_request_id: str | None = None,
    email: dict[str, Any] | None = None,
) -> dict[str, Any]:
    path = Path(path)
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("pulse.json must be an object")

    if doc_url is not None:
        payload["doc_url"] = doc_url
    if document_id is not None:
        payload["document_id"] = document_id
    if docs_request_id is not None:
        payload["docs_request_id"] = docs_request_id
    if email is not None:
        payload["email"] = email

    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
