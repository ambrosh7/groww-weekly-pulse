# Groww Weekly Review Pulse

Turn **Google Play** reviews for [Groww](https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN) into a scannable pulse, then deliver it via **Google Docs** (append) and **Gmail** (real send) through MCP.

## Scope (v1)

| In scope | Out of scope |
| --- | --- |
| Public **Play Store** review exports | **Apple App Store** reviews (deferred) |
| Aggregate → theme (≤5) → one-page pulse | Scraping behind store logins / ToS-violating automation |
| Google Docs + Gmail via **MCP** | Custom Google OAuth + REST as the primary path |
| Anonymous quotes, no PII in artifacts | Reviewer identities, device IDs, emails in outputs |
| MCP Doc **append** + Gmail **send** | Doc create / Gmail draft (not on MCP server) |

See [`docs/problemStatement.md`](docs/problemStatement.md) and [`docs/architecture.md`](docs/architecture.md).

## Phase status

| Phase | Status |
| --- | --- |
| 0 — Foundations | **Done** |
| 1 — Ingest & normalize | **Done** |
| 2 — Theming | **Done** |
| 3 — Pulse writer & gates | **Done** |
| 4 — Local orchestrator | **Done** |
| 5 — Docs MCP publish | **Done** (`google_docs_append_text`) |
| 6 — Gmail MCP notify | **Done** (`gmail_send_email` — real send) |
| 7 — Hardening & handoff | **Done** |

Decisions: [`docs/DECISIONS.md`](docs/DECISIONS.md) · Ops: [`docs/ops-checklist.md`](docs/ops-checklist.md) · Failures: [`docs/failure-modes.md`](docs/failure-modes.md)

## Setup

```bash
cd "/Users/apple/Desktop/AI Agents"   # or your clone path
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp config/settings.example.yaml config/settings.yaml
# edit settings.yaml: email_recipient, google_doc_id / google_doc_url
python -m src validate-config
```

## Quick start

```bash
# Offline sample (no Google)
python -m src run -i data/raw/groww_play_reviews_sample.csv --local-only

# Live Play download → local pulse
python -m src fetch-reviews --lang en --country in --max-reviews 15000
python -m src run --local-only

# Full delivery: pulse + Docs append + Gmail send
export MCP_HTTP_BEARER_TOKEN=your-railway-bearer-token
python -m src run -i data/raw/groww_play_reviews_sample.csv --deliver

# Retry Docs/Gmail only (pulse already on disk)
python -m src deliver
python -m src deliver --docs-only   # skip email
```

Ingest keeps reviews that are **>8 words**, **English**, and **not emoji-dominated**.

| File | Purpose |
| --- | --- |
| `data/raw/groww_play_reviews.csv` | Raw public export (gitignored) |
| `data/processed/reviews.json` | Windowed, PII-scrubbed corpus |
| `data/processed/themes.json` | ≤5 ranked themes + verbatim quotes |
| `data/output/pulse.md` / `pulse.json` | Validated 3/3/3 pulse (≤250 words) |

### Docs + Gmail via MCP

Server: [gmail-docs-mcp-server](https://github.com/ambrosh7/gmail-docs-mcp-server) · prod `https://gmail-docs-mcp-server-production.up.railway.app/health` → `{"status":"ok"}`.

1. Create one empty Google Doc (MCP **cannot** create Docs); share with the MCP Google account.
2. Set `google_doc_id` or `google_doc_url` + `email_recipient` in `config/settings.yaml`.
3. `export MCP_HTTP_BEARER_TOKEN=…`
4. `python -m src run --deliver` or `python -m src deliver`

Idempotency: `groww-pulse-docs-{week_ending}` / `groww-pulse-mail-{week_ending}`.

### Monthly schedule (GitHub Actions — free)

[`.github/workflows/monthly-pulse.yml`](.github/workflows/monthly-pulse.yml) — cron `0 3 1 * *` (1st of month 03:00 UTC ≈ 08:30 IST).

Secrets: `MCP_HTTP_BEARER_TOKEN`, `EMAIL_RECIPIENT`, `GOOGLE_DOC_ID`.

## Operator checklist

See [`docs/ops-checklist.md`](docs/ops-checklist.md). Short form:

1. Refresh Play export / `fetch-reviews`  
2. Confirm `window_weeks`, Doc id, recipient  
3. `python -m src run --deliver`  
4. Open Doc URL from `pulse.json`  
5. Confirm email arrived  
6. Spot-check: no invented quotes, no PII, ≤250 words  

## Failure modes

See [`docs/failure-modes.md`](docs/failure-modes.md). Docs failure **blocks** Gmail. Gate failures remove incomplete `pulse.*`.

## Layout

```text
config/           # settings.example.yaml · settings.yaml (local, gitignored)
data/raw/         # Play exports + sample CSV
data/processed/   # reviews.json, themes.json
data/output/      # pulse.md, pulse.json
src/              # ingest → theme → pulse → mcp → orchestrator → deliver
.github/workflows # monthly-pulse.yml
docs/             # problem, architecture, plan, ops, failures, eval
```

## Config notes

- `window_weeks` must be **8–12**.
- Google OAuth stays in the **MCP server** env (Railway), not this repo.
- Bearer token: env `MCP_HTTP_BEARER_TOKEN` only (see `.env.example`).

## Tests

```bash
pytest -q
```

## Docs index

- [Problem statement](docs/problemStatement.md)
- [Architecture](docs/architecture.md)
- [Implementation plan](docs/implementation-plan.md)
- [Ops checklist](docs/ops-checklist.md)
- [Failure modes](docs/failure-modes.md)
- [Edge cases](docs/edge-case.md)
- [Eval](docs/eval.md)
- [Decisions](docs/DECISIONS.md)
