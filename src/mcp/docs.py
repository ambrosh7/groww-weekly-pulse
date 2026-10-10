"""DocsPublisher adapter — MCP tool `google_docs_append_text` (Phase 5)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from src.mcp.client import McpClient, McpError

TOOL_NAME = "google_docs_append_text"
_DOC_URL_RE = re.compile(
    r"https://docs\.google\.com/document/d/([a-zA-Z0-9_-]+)",
    re.I,
)


class DocsPublishError(McpError):
    """Google Docs publish via MCP failed."""


@dataclass
class PublishResult:
    document_id: str
    doc_url: str
    request_id: str | None
    raw: dict[str, Any]


def extract_document_id(*, document_id: str | None, document_url: str | None) -> str:
    if document_id and document_id.strip():
        return document_id.strip()
    if document_url and document_url.strip():
        match = _DOC_URL_RE.search(document_url.strip())
        if not match:
            raise DocsPublishError(
                f"document_url must match docs.google.com/document/d/<ID>/...; "
                f"got {document_url!r}"
            )
        return match.group(1)
    raise DocsPublishError("Provide google_doc_id or google_doc_url in settings")


def build_document_url(document_id: str) -> str:
    return f"https://docs.google.com/document/d/{document_id}/edit"


def docs_request_id(week_ending: str) -> str:
    return f"groww-pulse-docs-{week_ending}"


@dataclass
class DocsPublisher:
    client: McpClient

    def publish(
        self,
        pulse_markdown: str,
        *,
        week_ending: str,
        title_template: str = "Groww Weekly Pulse — {week_ending}",
        document_id: str | None = None,
        document_url: str | None = None,
        request_id: str | None = None,
        prepend_newline: bool = True,
    ) -> PublishResult:
        if not pulse_markdown or not pulse_markdown.strip():
            raise DocsPublishError("pulse markdown is empty; refusing to publish")

        doc_id = extract_document_id(document_id=document_id, document_url=document_url)
        heading = title_template.format(week_ending=week_ending)
        rid = request_id or docs_request_id(week_ending)

        arguments: dict[str, Any] = {
            "document_id": doc_id,
            "text": pulse_markdown.strip() + "\n",
            "prepend_newline": prepend_newline,
            "heading": heading,
            "request_id": rid,
        }

        try:
            raw = self.client.call_tool(TOOL_NAME, arguments)
        except McpError as exc:
            raise DocsPublishError(str(exc)) from exc

        if raw.get("success") is False:
            raise DocsPublishError(f"Docs append unsuccessful: {raw}")

        out_id = str(raw.get("document_id") or doc_id)
        out_url = str(raw.get("document_url") or build_document_url(out_id))
        return PublishResult(
            document_id=out_id,
            doc_url=out_url,
            request_id=str(raw.get("request_id") or rid),
            raw=raw,
        )
