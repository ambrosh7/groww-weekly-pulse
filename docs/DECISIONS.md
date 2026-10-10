# Open Decisions — Phase 0

Recorded during foundations setup. Update when choices change.

| Decision | Choice | Notes |
| --- | --- | --- |
| Runtime language | **Python 3.11+** | Fits CSV/JSON pipeline, YAML config, pytest |
| Orchestration style | **CLI-first** | `python -m src …`; agent can wrap the same entrypoint later |
| Clustering (Phase 2) | **Keyword seed** (`clustering_approach: keyword_seed`) | Deterministic offline labeling with Groww vocabulary; merge to ≤5 by rank_score |
| Pulse insights/actions (Phase 3) | **Rule-based** (no LLM in v1) | Deterministic CI on sample fixture; quotes remain verbatim copy-paste |
| Pulse word count | Whitespace `str.split()` | Documented tokenizer for H8 / E3.11 |
| Local orchestrator (Phase 4) | `run_weekly_pulse` + `python -m src run` | Also `python -m src.orchestrator`; Docs/Gmail still deferred |
| Concurrent weekly runs | Document: do not run concurrent | Last-writer-wins is unsafe (E4.4); no lock file in v1 |
| Min review length | **word_count > 8** (`min_review_words: 8`) | Drop short/low-signal reviews before theming |
| Language / emoji | **English only** + drop emoji reviews | `require_english`, `drop_emoji_reviews`; langdetect + script heuristics |
| Review stores in v1 | **Google Play only** | App Store deferred (see problem statement) |
| Docs/Gmail auth | **MCP server env** | No OAuth secrets in app config |
| Sample data | Committed fixture `data/raw/groww_play_reviews_sample.csv` | Synthetic, anonymized, Play-shaped; ~10 weeks ending 2026-10-10 |
| Live Play download | `google-play-scraper` → `fetch-reviews` | Public listing feed only (lang=en, country=in); no Play Console auth; reviewer names not stored |
| Weekly Doc strategy | **Append to one existing Doc** | MCP tool `google_docs_append_text` cannot create Docs ([gmail-docs-mcp-server](https://github.com/ambrosh7/gmail-docs-mcp-server)); config holds `google_doc_id` / URL |
| Gmail delivery | **Send real email** (`gmail_send_email`) | Server has `gmail.send` only — no draft create; problem-statement “draft” → v1 sent notify |
| MCP host | Railway HTTP `gmail-docs-mcp-server-production.up.railway.app` | Health `/health`; bearer token in MCP/client secrets, not app repo |
| MCP client in app | Thin `McpHttpClient` → `POST /mcp` `tools/call` | Adapters: `DocsPublisher`, `GmailNotifier`; token from `MCP_HTTP_BEARER_TOKEN` |
| Delivery defaults | `publish_to_docs` / `send_email` **false** | Opt in via config or `--deliver` so local runs never surprise-send |
| Phase 7 handoff | Ops checklist + failure modes + `python -m src deliver` | Retry Docs/Gmail without re-ingest; monthly GHA schedule |
| Scheduler cadence | **Monthly** (`0 3 1 * *`) | GitHub Actions free tier; lookback still `window_weeks` |

## Deferred (not v1)

- Apple App Store ingest
- Custom Google REST/OAuth clients as primary Docs/Gmail path
