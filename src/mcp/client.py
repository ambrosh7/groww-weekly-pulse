"""
Thin Streamable HTTP MCP client for gmail-docs-mcp-server (Phases 5–6).

Calls POST {base_url}/mcp with Bearer auth. Google OAuth stays on the server.
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any, Protocol
from urllib.parse import urljoin


DEFAULT_MCP_BASE_URL = "https://gmail-docs-mcp-server-production.up.railway.app"
BEARER_ENV_KEYS = ("MCP_HTTP_BEARER_TOKEN", "GROWW_MCP_BEARER_TOKEN")


class McpError(RuntimeError):
    """MCP transport or tool call failed."""


class McpClient(Protocol):
    """Protocol so tests can inject fakes."""

    def health(self) -> dict[str, Any]: ...

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]: ...


def resolve_bearer_token(explicit: str | None = None) -> str:
    if explicit and explicit.strip():
        return explicit.strip()
    for key in BEARER_ENV_KEYS:
        value = os.environ.get(key, "").strip()
        if value:
            return value
    raise McpError(
        "MCP bearer token missing. Set env MCP_HTTP_BEARER_TOKEN "
        "(or GROWW_MCP_BEARER_TOKEN). Never commit the token."
    )


@dataclass
class McpHttpClient:
    """JSON-RPC client for Streamable HTTP MCP (`enableJsonResponse: true`)."""

    base_url: str = DEFAULT_MCP_BASE_URL
    bearer_token: str = ""
    timeout_s: float = 60.0
    protocol_version: str = "2025-03-26"

    def __post_init__(self) -> None:
        self.base_url = self.base_url.rstrip("/")
        if not self.bearer_token:
            self.bearer_token = resolve_bearer_token()

    @property
    def mcp_url(self) -> str:
        return urljoin(self.base_url + "/", "mcp")

    @property
    def health_url(self) -> str:
        return urljoin(self.base_url + "/", "health")

    def health(self) -> dict[str, Any]:
        req = urllib.request.Request(self.health_url, method="GET")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s, context=_ssl()) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise McpError(f"MCP health check HTTP {exc.code}") from exc
        except urllib.error.URLError as exc:
            raise McpError(f"MCP health check failed: {exc.reason}") from exc
        if not isinstance(payload, dict) or payload.get("status") != "ok":
            raise McpError(f"MCP unhealthy: {payload!r}")
        return payload

    def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """
        Call tools/call. Server uses stateless Streamable HTTP (new server per POST),
        so a single tools/call request is sufficient when JSON responses are enabled.
        """
        body = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments},
        }
        raw = self._post_json(body)
        if "error" in raw and raw["error"]:
            err = raw["error"]
            raise McpError(
                f"MCP JSON-RPC error: {err.get('message', err)} (code={err.get('code')})"
            )
        result = raw.get("result")
        if not isinstance(result, dict):
            raise McpError(f"Unexpected MCP tools/call result: {raw!r}")
        if result.get("isError"):
            raise McpError(_format_tool_error(result))
        return _normalize_tool_result(result)

    def _post_json(self, payload: dict[str, Any]) -> dict[str, Any]:
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.mcp_url,
            data=data,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream",
                "Authorization": f"Bearer {self.bearer_token}",
                "MCP-Protocol-Version": self.protocol_version,
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_s, context=_ssl()) as resp:
                content_type = resp.headers.get("Content-Type", "")
                text = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise McpError(f"MCP HTTP {exc.code}: {detail or exc.reason}") from exc
        except urllib.error.URLError as exc:
            raise McpError(f"MCP request failed: {exc.reason}") from exc

        if "text/event-stream" in content_type:
            return _parse_sse_jsonrpc(text)
        try:
            parsed = json.loads(text)
        except json.JSONDecodeError as exc:
            raise McpError(f"MCP returned non-JSON body: {text[:300]!r}") from exc
        if not isinstance(parsed, dict):
            raise McpError(f"MCP returned non-object JSON: {parsed!r}")
        return parsed


def _ssl() -> ssl.SSLContext:
    return ssl.create_default_context()


def _parse_sse_jsonrpc(text: str) -> dict[str, Any]:
    """Extract the last JSON-RPC message from an SSE stream."""
    last: dict[str, Any] | None = None
    for line in text.splitlines():
        if not line.startswith("data:"):
            continue
        chunk = line[5:].strip()
        if not chunk or chunk == "[DONE]":
            continue
        try:
            obj = json.loads(chunk)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and ("result" in obj or "error" in obj):
            last = obj
    if last is None:
        raise McpError(f"No JSON-RPC result in SSE stream: {text[:400]!r}")
    return last


def _normalize_tool_result(result: dict[str, Any]) -> dict[str, Any]:
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return dict(structured)
    content = result.get("content")
    if isinstance(content, list):
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text") or ""
                try:
                    parsed = json.loads(text)
                except json.JSONDecodeError:
                    return {"message": text, "raw_text": text}
                if isinstance(parsed, dict):
                    return parsed
                return {"data": parsed}
    return dict(result)


def _format_tool_error(result: dict[str, Any]) -> str:
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        err = structured.get("error")
        if isinstance(err, dict):
            return f"{err.get('code', 'TOOL_ERROR')}: {err.get('message', structured)}"
        return json.dumps(structured)
    content = result.get("content")
    if isinstance(content, list) and content:
        first = content[0]
        if isinstance(first, dict):
            return str(first.get("text") or first)
    return "MCP tool returned isError=true"
