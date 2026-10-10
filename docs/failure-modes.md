# Known failure modes

Fail-closed behaviour for operators and CI.

| Mode | Symptom | What to do |
| --- | --- | --- |
| Empty review window | `EmptyCorpusError` / ingest exits non-zero | Widen `window_weeks`, refresh raw export, or check date filter |
| MCP down / unhealthy | `/health` not `ok`, or HTTP errors on `/mcp` | Check Railway deploy; retry later; leave local `pulse.*` intact |
| Missing bearer token | `MCP bearer token missing` | `export MCP_HTTP_BEARER_TOKEN=…` |
| Docs append fail | `Docs publish failed: …` | Confirm Doc shared with MCP Google account; valid `google_doc_id`; **Gmail is skipped** |
| Gmail send fail | `Gmail notify failed: …` | Check recipient, MCP Gmail scope/auth; Doc already appended — fix mail and `python -m src deliver` |
| Gate fail (invented quote / PII / word count) | Pulse error; incomplete `pulse.*` removed | Fix upstream themes/reviews; re-run `pulse` or `run` |
| Theme crash mid-run | Orchestrator error after ingest | Prior pulse left untouched; fix theme input and re-run |
| Idempotency conflict | MCP `IDEMPOTENCY_CONFLICT` | Same `request_id` with different payload; wait TTL or change week_ending / key |
| Invalid `--weeks` | Rejected before ingest | Use 8–12 only |
| Soft-fail disabled + &lt;3 themes | Pulse gate blocks | Enrich corpus or temporarily set `allow_soft_fail` (not for sample acceptance) |

## Success criteria (v1)

- Play reviews in configured 8–12 week window  
- ≤5 themes clustered; pulse shows top 3  
- Exactly 3 quotes + 3 actions; word count ≤ 250  
- Docs via `google_docs_append_text`; email via `gmail_send_email` (real send)  
- No reviewer PII in artifacts or email body  
