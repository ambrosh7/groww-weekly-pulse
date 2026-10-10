# Operator checklist — Groww pulse

Aligned with [`architecture.md`](./architecture.md) §13. Delivery uses MCP **append + send** (not Doc create / Gmail draft). Deploy topology: [`deployment-plan.md`](./deployment-plan.md).

## Monthly ritual (or ad-hoc)

1. **Refresh Play reviews**
   ```bash
   python -m src fetch-reviews --lang en --country in --max-reviews 15000
   ```
   Or place a ToS-compliant CSV under `data/raw/`.
2. **Config** — `config/settings.yaml` (from `settings.example.yaml`):
   - `window_weeks` ∈ 8–12
   - `google_doc_id` or `google_doc_url` (existing Doc)
   - `email_recipient`
3. **MCP token** (shell only; never commit):
   ```bash
   export MCP_HTTP_BEARER_TOKEN=…
   curl -sS "$MCP_BASE_URL/health"   # or prod Railway /health → {"status":"ok"}
   ```
4. **Run end-to-end** (local pulse + Docs append + Gmail send):
   ```bash
   python -m src run --deliver
   # sample dry-run without Google:
   python -m src run -i data/raw/groww_play_reviews_sample.csv --local-only
   ```
5. **Verify Doc** — open `doc_url` from `data/output/pulse.json`; newest section has themes / quotes / actions.
6. **Verify email** — message in recipient inbox (sent from MCP Google account).
7. **Spot-check** — 3 themes, 3 verbatim quotes, 3 actions, ≤250 words, no PII.

## Re-deliver from an existing pulse

If `pulse.md` / `pulse.json` already exist and you only want Docs + email:

```bash
python -m src deliver
```

## Sync dashboard for Vercel

After any successful pulse run:

```bash
python scripts/sync_frontend_data.py
# commit + push frontend/public/data/ to redeploy the UI
```

Monthly GitHub Actions does this automatically when `sync_frontend` is enabled.

## GitHub Actions (monthly)

Workflow [`.github/workflows/monthly-pulse.yml`](../.github/workflows/monthly-pulse.yml) — 1st of month 03:00 UTC. Secrets: `MCP_HTTP_BEARER_TOKEN`, `EMAIL_RECIPIENT`, `GOOGLE_DOC_ID`.

## Deferred (not v1)

- Apple App Store ingest
- MCP Doc create / Gmail draft-only (server does not expose these)
