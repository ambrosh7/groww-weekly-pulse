# Deployment Plan — Groww Weekly Review Pulse

Deploy the **latest Stitch dashboard** on **Vercel** and the **pipeline + MCP delivery stack** on **Railway** (with GitHub Actions as the recommended scheduler). This plan covers the full system end-to-end.

Related: [`architecture.md`](./architecture.md) · [`ops-checklist.md`](./ops-checklist.md) · [`failure-modes.md`](./failure-modes.md) · [`DECISIONS.md`](./DECISIONS.md)

---

## 1. What we are deploying

| Piece | Role | Host | Source |
| --- | --- | --- | --- |
| **Frontend** | Light/dark executive dashboard (Overview · Themes · Quotes · Actions · Reviews · Delivery) | **Vercel** | `frontend/` (Vite SPA) |
| **Pulse pipeline (backend CLI)** | Ingest → theme → pulse → optional Docs/Gmail | **Railway worker** *or* **GitHub Actions** | `src/` (`python -m src …`) |
| **MCP server** | Google Docs append + Gmail send (OAuth lives here) | **Railway** | [`gmail-docs-mcp-server`](https://github.com/ambrosh7/gmail-docs-mcp-server) |
| **Artifacts** | `pulse.json` / `pulse.md` / processed reviews | Generated at run time | `data/output/`, `data/processed/` |

```text
                    ┌─────────────────────────────┐
                    │ GitHub: groww-weekly-pulse  │
                    └──────────────┬──────────────┘
           ┌───────────────────────┼───────────────────────┐
           ▼                       ▼                       ▼
   ┌───────────────┐     ┌─────────────────┐     ┌────────────────────┐
   │ Vercel        │     │ GitHub Actions  │     │ Railway            │
   │ Vite frontend │     │ monthly pulse   │────▶│ gmail-docs-mcp     │
   │ (static SPA)  │     │ (recommended)   │     │ (Docs + Gmail)     │
   └───────▲───────┘     │                 │     └────────────────────┘
           │             │  optional alt:  │
           │             │  Railway cron   │
           │             └────────┬────────┘
           │                      │ writes pulse.json
           └──── sync / commit ───┘  (see §6)
```

**Important:** This repo’s Python app is a **CLI orchestrator**, not a long-lived HTTP API. Vercel must **not** treat the root as a Python function project (that caused `No python entrypoint found`).

---

## 2. Target environments

| Env | Frontend URL | MCP / pipeline | Purpose |
| --- | --- | --- | --- |
| **Local** | `http://localhost:5173` | Local MCP (`127.0.0.1:3000`) or Railway prod MCP | Dev / dry-run |
| **Preview** | Vercel preview per PR | Railway prod MCP (read-only UI) or staging MCP | Design + UX review |
| **Production** | Vercel production domain | Railway MCP prod + scheduled pulse | Live console + monthly delivery |

---

## 3. Prerequisites

### Accounts & repos

- [ ] GitHub repo: `https://github.com/ambrosh7/groww-weekly-pulse` (`main` up to date with frontend)
- [ ] Vercel project linked to that repo
- [ ] Railway project for **MCP** ([`gmail-docs-mcp-server`](https://github.com/ambrosh7/gmail-docs-mcp-server)) — already used in prod as `gmail-docs-mcp-server-production.up.railway.app`
- [ ] (Optional) Second Railway service for the pulse CLI if not using GitHub Actions
- [ ] Google account connected to MCP (OAuth on Railway only)
- [ ] One existing Google Doc shared with the MCP Google account (MCP **cannot** create Docs)

### Local verification before first deploy

```bash
# Frontend
cd frontend && npm install && npm run build && npm run preview

# Backend dry-run (no Google)
cd ..
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp config/settings.example.yaml config/settings.yaml
# edit email_recipient + google_doc_id when ready for delivery
python -m src run -i data/raw/groww_play_reviews_sample.csv --local-only
```

Gates: pulse ≤250 words, 3 themes / 3 quotes / 3 actions, no PII.

---

## 4. Frontend → Vercel (latest dashboard)

### 4.1 Why Vercel

- Static Vite SPA, global CDN, preview deploys per PR
- Matches current [`vercel.json`](../vercel.json) + [`frontend/vercel.json`](../frontend/vercel.json)

### 4.2 Project settings (recommended)

In **Vercel → Project → Settings → General**:

| Setting | Value |
| --- | --- |
| **Root Directory** | `frontend` |
| Framework Preset | Vite |
| Build Command | `npm run build` |
| Output Directory | `dist` |
| Install Command | `npm install` |
| Node version | 20.x (or current LTS) |

> Prefer Root Directory = `frontend`. That avoids Vercel’s Python auto-detect from root `pyproject.toml` / `requirements.txt`.

If Root Directory stays at repo root, the root [`vercel.json`](../vercel.json) already sets:

- `installCommand`: `npm install --prefix frontend`
- `buildCommand`: `npm run build --prefix frontend`
- `outputDirectory`: `frontend/dist`
- SPA rewrite → `index.html`

### 4.3 Deploy steps

1. Push latest `main` (includes `frontend/`).
2. Import or reconnect the GitHub repo in Vercel.
3. Apply settings in §4.2.
4. Deploy Production from `main`.
5. Confirm:
   - Site loads Overview
   - Theme toggle (light/dark) works
   - Hash routes work: `#/themes`, `#/quotes`, `#/actions`, `#/reviews`, `#/delivery`
   - `/data/pulse.json` and `/data/reviews.json` return 200

### 4.4 SPA routing

Hash routing (`#/overview`) works without server rewrites. Rewrites are still configured so a future path-based router does not 404.

### 4.5 Frontend env vars

v1 dashboard reads committed/synced JSON under `frontend/public/data/`. No Vercel secrets required for the static console.

Optional later:

| Variable | Purpose |
| --- | --- |
| `VITE_DATA_BASE` | Optional absolute origin prefix for `/data/*.json` (default: same origin) |

---

## 5. MCP backend → Railway

This is the **Docs + Gmail** backend. Google OAuth tokens and bearer auth live only here.

### 5.1 Service (existing)

| Item | Value |
| --- | --- |
| Repo | `ambrosh7/gmail-docs-mcp-server` |
| Transport | Streamable HTTP |
| Health | `GET /health` → `{"status":"ok"}` |
| Tools | `google_docs_append_text`, `gmail_send_email` |
| Prod example | `https://gmail-docs-mcp-server-production.up.railway.app` |

### 5.2 Railway variables (MCP service)

Set in Railway → Variables (never commit):

| Variable | Required | Notes |
| --- | --- | --- |
| `MCP_TRANSPORT` | yes | `http` |
| `MCP_HTTP_HOST` | yes | `0.0.0.0` on Railway |
| `MCP_HTTP_PORT` | yes | Railway-provided `PORT` or mapped port |
| `MCP_HTTP_BEARER_TOKEN` | yes | Long random secret; same value clients use |
| Google OAuth / token store paths | yes | Per MCP server README |
| Idempotency store path | recommended | Survives retries |

### 5.3 Smoke test

```bash
export MCP_BASE_URL=https://gmail-docs-mcp-server-production.up.railway.app
export MCP_HTTP_BEARER_TOKEN=…   # same as Railway

curl -sS "$MCP_BASE_URL/health"
# expect: {"status":"ok"}
```

Clients of this MCP:

- Local: `python -m src run --deliver`
- CI: GitHub Actions secrets
- Optional Railway pulse worker (below)

---

## 6. Pulse pipeline (backend) — where it runs

The orchestrator is **batch**, not a 24/7 web server. Pick **one** primary host:

### Option A — GitHub Actions (recommended for v1)

Already implemented: [`.github/workflows/monthly-pulse.yml`](../.github/workflows/monthly-pulse.yml)

| Pros | Cons |
| --- | --- |
| Free-tier friendly | Cron can drift under load |
| No Docker required | Artifacts need an explicit sync to Vercel UI (§6.3) |
| Secrets in GitHub | Private repos have Actions minute limits |

**Schedule:** `0 3 1 * *` (1st of month 03:00 UTC ≈ 08:30 IST)

**GitHub Actions secrets / vars**

| Name | Type | Purpose |
| --- | --- | --- |
| `MCP_HTTP_BEARER_TOKEN` | secret | Auth to Railway MCP |
| `EMAIL_RECIPIENT` | secret | Gmail To: |
| `GOOGLE_DOC_ID` | secret | Existing Doc id |
| `GOOGLE_DOC_URL` | optional | Alternative to Doc id |
| `MCP_BASE_URL` | var | Defaults to Railway prod URL |
| `WINDOW_WEEKS` | var | 8–12 (default 10) |

**Manual test:** Actions → *Monthly Groww Pulse* → Run workflow  
(`use_sample=true` for dry-run without fetch/delivery).

### Option B — Railway cron / worker (optional)

Use when you want the pipeline co-located with MCP on Railway.

1. Add a **second Railway service** from `groww-weekly-pulse` (this repo).
2. Docker assets are in-repo: [`Dockerfile`](../Dockerfile), [`railway.toml`](../railway.toml), [`scripts/railway_run.sh`](../scripts/railway_run.sh).

3. Railway variables for the worker:

| Variable | Purpose |
| --- | --- |
| `MCP_HTTP_BEARER_TOKEN` | Call MCP |
| `MCP_BASE_URL` | Railway MCP public URL |
| `EMAIL_RECIPIENT` | Delivery |
| `GOOGLE_DOC_ID` / `GOOGLE_DOC_URL` | Delivery |
| `WINDOW_WEEKS` | Lookback |

4. Use Railway **Cron** (or a lightweight scheduler) to run the same command monthly. Persist `data/` on a volume if you need artifact retention.

5. Still sync `pulse.json` to the frontend (§6.3).

### 6.3 Keeping the Vercel dashboard fresh

Today the UI loads:

- `frontend/public/data/pulse.json`
- `frontend/public/data/reviews.json`

After each successful pipeline run, refresh those files and redeploy (or commit):

```bash
# After: python -m src run --local-only  (or --deliver)
cp data/output/pulse.json frontend/public/data/pulse.json
# regenerate reviews.json from the latest export/sample as needed
git add frontend/public/data/pulse.json frontend/public/data/reviews.json
git commit -m "Refresh dashboard pulse data"
git push   # Vercel redeploys
```

**Automated in CI:** [`.github/workflows/monthly-pulse.yml`](../.github/workflows/monthly-pulse.yml) runs [`scripts/sync_frontend_data.py`](../scripts/sync_frontend_data.py), then commits `frontend/public/data/*` to `main` when data changed (`sync_frontend` input; on by default for schedule). That push triggers Vercel.

Manual refresh anytime:

```bash
python -m src run -i data/raw/groww_play_reviews_sample.csv --local-only
python scripts/sync_frontend_data.py
```

---

## 7. Secrets matrix (never commit)

| Secret | Vercel | Railway MCP | GHA / Railway worker |
| --- | --- | --- | --- |
| `MCP_HTTP_BEARER_TOKEN` | — | set (server) | set (client) |
| Google OAuth / refresh tokens | — | set | — |
| `EMAIL_RECIPIENT` | — | — | set |
| `GOOGLE_DOC_ID` / URL | — | — | set |
| Frontend API keys | none in v1 | — | — |

Rules:

- No bearer tokens in `config/settings.yaml` committed to git
- `config/settings.yaml` stays gitignored; CI writes it from env ([`scripts/write_ci_settings.py`](../scripts/write_ci_settings.py))
- Docs failure must **block** Gmail ([`failure-modes.md`](./failure-modes.md))

---

## 8. End-to-end deployment checklist

### Phase 0 — Prep

- [ ] `main` contains latest `frontend/` + `vercel.json`
- [ ] Sample dry-run passes locally
- [ ] Empty Google Doc created + shared with MCP account
- [ ] Doc id / recipient known

### Phase 1 — Railway MCP

- [ ] MCP service healthy: `/health` → `ok`
- [ ] Bearer token rotated and stored in GHA (and worker if used)
- [ ] Manual `python -m src deliver` (or sample `--deliver`) succeeds once

### Phase 2 — Vercel frontend

- [ ] Root Directory = `frontend` (or root `vercel.json` build works)
- [ ] Production deploy green (no Python entrypoint error)
- [ ] Light/dark toggle + all six views verified on production URL
- [ ] Custom domain (optional)

### Phase 3 — Scheduled pipeline

- [ ] GHA secrets set **or** Railway worker + cron configured
- [ ] One `workflow_dispatch` success with delivery
- [ ] Doc append + inbox email verified
- [ ] Dashboard data sync step documented/automated (§6.3)

### Phase 4 — Handoff

- [ ] Operators can follow [`ops-checklist.md`](./ops-checklist.md)
- [ ] Failure runbook: [`failure-modes.md`](./failure-modes.md)
- [ ] Rollback: previous Vercel deployment + previous MCP Railway deploy

---

## 9. Recommended production topology (v1)

```text
Vercel                          GitHub Actions (monthly)
──────                          ────────────────────────
frontend/  ──static──► CDN      fetch → ingest → theme → pulse
                                 │
                                 ├─► Railway MCP ──► Google Docs append
                                 │               └──► Gmail send
                                 └─► sync pulse.json into frontend/public/data
                                      └──► push → Vercel redeploy
```

| Layer | Host | Status |
| --- | --- | --- |
| UI | Vercel | `vercel.json` + `frontend/` + Frontend CI workflow |
| MCP | Railway | Existing `gmail-docs-mcp-server` service |
| Orchestrator | GitHub Actions | Monthly workflow (deliver + sync) |
| Orchestrator (alt) | Railway worker | `Dockerfile` + `railway.toml` |
| UI data sync | GHA commit / `sync_frontend_data.py` | Implemented |

---

## 10. Rollback

| Layer | Action |
| --- | --- |
| Frontend | Vercel → Deployments → Promote previous successful deploy |
| MCP | Railway → rollback to previous deployment; confirm `/health` |
| Bad pulse in Doc | Do not delete history lightly; append a correction section next run |
| Bad email | Cannot unsend; fix content gates before next `--deliver` |

---

## 11. Out of scope for this plan (deferred)

- Hosting the Python app as a public HTTP API on Vercel
- Apple App Store ingest
- MCP Doc create / Gmail draft-only tools
- Multi-tenant auth on the dashboard
- Real-time websocket updates into the UI

---

## 12. Quick command card

```bash
# Local frontend
cd frontend && npm run dev

# Local backend dry-run
python -m src run -i data/raw/groww_play_reviews_sample.csv --local-only

# Local full delivery (uses Railway MCP)
export MCP_HTTP_BEARER_TOKEN=…
export MCP_BASE_URL=https://gmail-docs-mcp-server-production.up.railway.app
python -m src run --deliver

# Sync UI data after a run
cp data/output/pulse.json frontend/public/data/pulse.json
```

---

## 13. Success criteria

Deployment is **done** when:

1. Production Vercel URL serves the latest light/dark dashboard.
2. Railway MCP `/health` is `ok` and accepts bearer-authenticated tool calls.
3. Scheduled (or manual) pipeline produces a validated pulse and delivers via Docs + Gmail.
4. Dashboard `pulse.json` reflects the latest successful run after sync.
5. Operators can redeploy / rollback each layer independently without touching Google OAuth in the app repo.
