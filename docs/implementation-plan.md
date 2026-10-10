# Implementation Plan — Groww Weekly Review Pulse

Phase-wise build plan derived from [`problemStatement.md`](./problemStatement.md) and [`architecture.md`](./architecture.md).

**v1 scope:** Google Play Store reviews only · App Store deferred · Docs + Gmail via MCP

**MCP delivery (locked):** [ambrosh7/gmail-docs-mcp-server](https://github.com/ambrosh7/gmail-docs-mcp-server) — production HTTP host `gmail-docs-mcp-server-production.up.railway.app` (`GET /health` → `{"status":"ok"}`). Tools are **write-only** and narrower than the original “create Doc / create draft” sketch; Phases 5–6 below match the live tool surface.

| MCP tool | What it does | What it does **not** do |
| --- | --- | --- |
| `google_docs_append_text` | Append plain text to an **existing** Google Doc (`document_id` or `docs.google.com/.../d/<ID>/...` URL; optional `prepend_newline`, `request_id`) | Create, replace, delete, or share Docs |
| `gmail_send_email` | **Send** a real plain-text email (`to[]`, `subject`, `body`; optional `request_id`) | Create drafts, read/search/label mailbox, HTML/attachments |

Auth + Google OAuth stay in the MCP server env (Railway / local token store). This app only calls tools through an MCP client (Cursor agent or thin HTTP adapter). Prefer `request_id` for idempotent retries.

---

## Overview

| Phase | Name | Outcome |
| --- | --- | --- |
| 0 | Foundations | Repo, config, sample data, decisions locked |
| 1 | Ingest & normalize | Clean `reviews.json` for 8–12 weeks, PII scrubbed |
| 2 | Theming | ≤5 themes ranked in `themes.json` with quote candidates |
| 3 | Pulse writer & gates | Valid `pulse.md` / `pulse.json` (3/3/3, ≤250 words); golden path on sample CSV |
| 4 | Orchestrator (local) | One command runs ingest → pulse on disk |
| 5 | Docs MCP publish | Pulse **appended** to configured Google Doc via `google_docs_append_text` |
| 6 | Gmail MCP notify | Pulse (or Doc link) **sent** via `gmail_send_email` (real send, not draft) |
| 7 | Hardening & handoff | README, weekly checklist, acceptance pass |

```text
Phase 0 ──► Phase 1 ──► Phase 2 ──► Phase 3 ──► Phase 4 ──► Phase 5 ──► Phase 6 ──► Phase 7
                              (local artifacts)              (MCP delivery)     (ship)
```

Phases 5 and 6 depend on the Gmail/Docs MCP server being reachable (Railway HTTP or local stdio); Phases 0–4 can complete without Google auth.

---

## Phase 0 — Foundations

**Goal:** Scaffold the project so later stages plug into stable paths and config.

### Work

1. Choose runtime (Python or TypeScript) and orchestration style (CLI-first recommended; agent can wrap the same entrypoint).
2. Create directory layout from architecture §6 (`data/raw`, `data/processed`, `data/output`, `src/*`, `prompts/`, `config/`).
3. Add `config/settings.example.yaml` with keys from architecture §7 (`window_weeks`, `max_themes`, `email_recipient`, etc.).
4. Add `.gitignore` for bulky raw exports and local secrets.
5. Obtain or assemble a **public Play Store** review sample for Groww (`com.nextbillion.groww`) covering ~8–12 weeks — ToS-compliant export only.
6. Document in README: Play-only scope, no scraping, no App Store.

### Exit criteria

- [ ] Repo layout matches architecture
- [ ] Example config committed; real secrets not committed
- [ ] At least one Play export (or fixture) under `data/raw/` usable for later phases
- [ ] Open decisions recorded: language, clustering approach for Phase 2 (LLM-labeling is fine for v1)

### Depends on

Nothing.

---

## Phase 1 — Ingest & Normalize

**Goal:** Turn raw Play exports into a single scrubbed review corpus.

### Work

1. **Ingest**
   - Load CSV/JSON from `data/raw/`
   - Map store fields → internal schema (`id`, `store: play`, `rating`, `title`, `text`, `date`, `locale`)
   - Reject or ignore non-Play sources if present
2. **Window filter**
   - Keep reviews in `[now - window_weeks, now]` with `window_weeks ∈ [8, 12]`
   - Fail clearly if zero reviews remain
3. **PII scrubber**
   - Strip/redact emails, phones, device IDs, account-like tokens, reviewer display names if present
   - Drop identity fields from any artifact written forward
4. Write `data/processed/reviews.json`
5. Unit tests: field mapping, window edge cases, scrub patterns

### Exit criteria

- [ ] `reviews.json` produced from sample export
- [ ] All retained reviews within configured window
- [ ] No usernames/emails/device IDs in processed file
- [ ] Empty-window path aborts with a clear error

### Depends on

Phase 0.

### Maps to

Problem statement: import Play reviews for 8–12 weeks · Architecture §4.2–4.3

---

## Phase 2 — Theming Engine

**Goal:** Cluster reviews into at most 5 themes; rank and attach verbatim quote candidates.

### Work

1. Implement clustering/labeling (v1 default: LLM labeling with fixed theme budget, or keyword seed + LLM refine).
2. Enforce `max_themes ≤ 5`; merge lowest-ranked if over budget.
3. Compute `rank_score` (volume + negative-rating weight — document formula in code).
4. Attach `representative_quotes` per theme (verbatim substrings of scrubbed review text).
5. Seed Groww vocabulary as hints only (onboarding, KYC, payments, trading, withdrawals); rename if data differs.
6. Write `data/processed/themes.json`
7. Tests: theme count cap, quote substring check against source reviews

### Exit criteria

- [ ] `1 ≤ theme_count ≤ 5`
- [ ] Each theme has count, avg rating (or equivalent), and quote candidates
- [ ] Quotes are verbatim from scrubbed reviews (no invented text)
- [ ] Ranking order is deterministic for a fixed input file

### Depends on

Phase 1.

### Maps to

Problem statement: group into ≤5 themes · Architecture §4.4

---

## Phase 3 — Pulse Writer & Validation Gates

**Goal:** Produce the weekly one-page note and block bad output before any publish.

**Primary golden fixture:** [`data/raw/groww_play_reviews_sample.csv`](../data/raw/groww_play_reviews_sample.csv) — use this to design, implement, and accept Phase 3 before relying on the large live Play dump.

### Sample analysis (drives Phase 3 design)

| Signal from sample | Implication for pulse writer |
| --- | --- |
| 40 Play / `en_IN` rows; empty `title` column | Do **not** depend on titles; quotes and summaries come from `text` only |
| After Phase 1–2 filters (~36 kept; 4 dropped for ≤8 words; 0 emoji / 0 non-English) | Pulse header should report **kept count + window**, not raw export size |
| Theme mass (pre-merge): Trading ~12, Withdrawals ~6, KYC ~5, Payments ~5, Onboarding ~4 | Expect **top 3** after rank/merge to be product-pain heavy (e.g. Trading, Withdrawals, KYC) — not “General” |
| Ratings among kept skew **1★–2★** (praise exists but is minority) | Theme blurbs should state volume **and** pain (avg rating / low-star share), not only count |
| Bodies are short (~9–15 words) | Easy to stay **≤250 words**; prefer **full verbatim** quotes (no truncation needed on sample) |
| Recurring pains: KYC selfie/eSign/DigiLocker, withdrawal/IFSC/status, UPI add-money, opaque order cancels, chart freeze | Actions must be **concrete Groww fixes** tied to those themes (no generic “improve UX”) |
| Some 4★–5★ praise (MF/SIP/IPO/onboarding smooth) | Optional one-line “also working” note only if space; **do not** invent a 4th theme for praise |

Illustrative top-3 + quote pool the writer should support on this fixture (exact rank order follows `themes.json` after Phase 2):

1. **Trading / orders / quotes** — e.g. order pending then cancels; live prices lag; GTT errors; blank market depth  
2. **Withdrawals / settlements / statements** — e.g. multi-day bank withdrawal; invalid IFSC false reject; statement PDF hard to find  
3. **KYC / verification** — e.g. selfie step fails; Aadhaar eSign on Android 14; DigiLocker fetch fails  

### Pulse shape (fixed template)

```text
# {product_name} Weekly Pulse — week ending {week_ending}

Window: last {window_weeks} weeks ({window_start} → {window_end}) · Play reviews analyzed: {kept_count}
Filters: >{min_review_words} words · English only · emoji reviews excluded

## Top themes
1. {theme_label} — n={count}, avg ★={avg_rating}. {one_sentence_insight}
2. ...
3. ...

## What users said
- "{verbatim_quote_1}" ({theme_label})
- "{verbatim_quote_2}" ({theme_label})
- "{verbatim_quote_3}" ({theme_label})

## Action ideas
1. {action} — grounded in {theme_label}
2. ...
3. ...
```

Target length: **≤250 words** total (sample-sized corpus should land well under this without aggressive trimming).

### Work

1. **Load inputs**
   - `data/processed/themes.json` (ranked themes + `representative_quotes`)
   - `data/processed/reviews.json` (verbatim validation + header stats from `meta`)
2. **Select top 3 themes** by `rank_score` (tie-break: `theme_id`).
   - On the sample fixture, assert top 3 are among Groww product themes (Trading / Withdrawals / KYC / Payments / Onboarding) — if “General feedback” ranks #1 on live data, still allow it, but **prefer** the highest-ranked *specific* themes when writing insights.
3. **Select 3 verbatim quotes**
   - Prefer one quote per top theme (coverage first).
   - Prefer lower `rating`, then longer text, then stable `id` (same as Phase 2 quote ranking).
   - Copy **exact** `text` from reviews / theme candidates — never paraphrase.
   - On sample: full sentences fit; no ellipsis truncation required unless a live quote exceeds ~220 chars.
4. **Generate 3 action ideas** (one primary mapping to each top theme)
   - Template/rule-based v1 is enough for the sample (deterministic CI); optional LLM refine later via `prompts/pulse_actions.md`.
   - Actions must name a **userable product lever** visible in the sample language, e.g.:
     - KYC: improve selfie / eSign / DigiLocker failure recovery + status parity web↔mobile  
     - Withdrawals: clearer pending/rejected reasons (incl. IFSC) + SLA status in-app  
     - Trading: explain order cancel/pending outcomes; harden chart/F&O stability  
     - Payments: fix UPI mandate / add-money redirect + balance refresh  
5. **Write theme insight lines** (one short sentence each)
   - Combine count + avg rating + dominant pain phrase mined from that theme’s quotes (sample-friendly; no LLM required).
6. **Render artifacts**
   - `data/output/pulse.md` — stakeholder-facing  
   - `data/output/pulse.json` — structured (`week_ending`, window, `review_count`, `themes[3]`, `quotes[3]`, `actions[3]`, `word_count`, `doc_url: null`, `source_fixture` when run on sample)
7. **Validation gates** (fail closed before any later publish)
   - Shape: exactly 3 themes, 3 quotes, 3 actions (sample always can satisfy — do not enable soft-fail for sample acceptance)
   - Verbatim: each quote is a substring of some scrubbed review `text`
   - Theme linkage: each quote and action references a top-3 `theme_id` / label
   - Word count ≤ 250  
   - Privacy: no email/phone/device-id patterns in pulse body  
   - Corpus policy echo: header stats match `reviews.json` meta (`min_review_words`, English/emoji filters already applied upstream)
8. **CLI:** `python -m src pulse` (reads processed artifacts → writes `data/output/pulse.*`)
9. **Prompts (optional):** add `prompts/pulse_insights.md` / `prompts/pulse_actions.md` only if LLM path is used; quotes remain copy-paste verbatim.

### Acceptance path (sample-first)

```bash
python -m src ingest -i data/raw/groww_play_reviews_sample.csv
python -m src theme
python -m src pulse
```

Expected on sample (approximate — exact theme order follows ranker):

- [ ] `reviews.json` kept ≈ 36 (all English, >8 words)
- [ ] `themes.json` has 1–5 themes; top 3 usable for pulse
- [ ] `pulse.md` has header + Top themes + What users said + Action ideas
- [ ] 3 quotes appear unchanged in sample review bodies (e.g. KYC selfie / withdrawal delay / UPI or order pain)
- [ ] 3 actions clearly map to those themes
- [ ] `word_count` ≤ 250; privacy gate clean
- [ ] pytest covers sample golden path + invented-quote rejection

### Exit criteria

- [ ] Pulse contains top 3 themes, 3 quotes, 3 actions
- [ ] Word count ≤ 250
- [ ] Gates fail closed on invented quotes or PII hits
- [ ] Pulse is scannable (header + short sections)
- [ ] Sample CSV golden path passes end-to-end (`ingest → theme → pulse`)
- [ ] Actions are concrete and theme-grounded (sample-style Groww pains, not generic UX filler)

### Depends on

Phase 2 (and Phase 1 filters: >8 words, English only, drop emoji reviews).

### Maps to

Problem statement deliverables · Architecture §4.5, §9 · Eval hard metrics H4–H9

---

## Phase 4 — Local Orchestrator

**Goal:** One entrypoint runs the full local pipeline (no Google yet).

### Work

1. Implement `run_weekly_pulse(window_weeks, …)` wiring Stages 1–3 + gates.
2. Short-circuit on failure; log artifact paths.
3. Idempotent overwrite of `reviews.json`, `themes.json`, `pulse.*` for the same run config.
4. CLI or script: e.g. `python -m src.orchestrator` / `npm run pulse`.
5. Smoke-test with the Phase 0 sample export end-to-end to disk.

### Exit criteria

- [ ] Single command produces validated `pulse.md` + `pulse.json`
- [ ] Failures stop before writing a “success” pulse
- [ ] Operator can re-run safely (overwrite, not duplicate append)

### Depends on

Phases 1–3.

### Maps to

Architecture §4.1, §5 (steps 1–6)

---

## Phase 5 — Google Docs via MCP

**Goal:** Publish the weekly pulse into a stakeholder-readable Google Doc using the locked MCP tool surface.

**Server:** [gmail-docs-mcp-server](https://github.com/ambrosh7/gmail-docs-mcp-server) · prod HTTP `https://gmail-docs-mcp-server-production.up.railway.app` (health: `/health`).

**Tool (exact name):** `google_docs_append_text`

| Arg | Required | Notes |
| --- | --- | --- |
| `document_id` **or** `document_url` | yes | ID, or URL matching `https://docs.google.com/document/d/<ID>/...` (arbitrary URLs rejected) |
| `text` | yes | Pulse body to append (plain text; markdown from `pulse.md` is fine as text) |
| `prepend_newline` | no | Prefer `true` so weeks separate cleanly when appending |
| `request_id` | no | Idempotency key for safe retries (same key + same payload → cached result) |

**Constraint (v1 lock):** The server **cannot create** a Doc. Operator creates one empty/template Doc once; config stores its id/URL. Each weekly run **appends** a new section (does not replace prior weeks).

### Work

1. Confirm MCP reachability from the operator environment:
   - HTTP: `GET https://gmail-docs-mcp-server-production.up.railway.app/health` → `{"status":"ok"}`
   - Client must present bearer token when calling Streamable HTTP MCP (`MCP_HTTP_BEARER_TOKEN` lives only in MCP/client secrets — not in this repo).
   - Or local stdio per MCP repo `examples/cursor.mcp.json`.
2. Add config keys (example YAML only; no secrets):
   - `google_doc_id` **or** `google_doc_url` — target Doc for appends
   - Keep `doc_title_template` for the **section heading** inside appended text (not a Google Doc title API — create is unsupported).
3. Implement thin `DocsPublisher` adapter that only knows MCP tool names:
   - `publish(pulse_markdown, *, document_id|document_url, week_ending, request_id) → { document_id, doc_url, request_id }`
   - Build append payload: heading from `doc_title_template` (e.g. `Groww Weekly Pulse — {week_ending}`) + blank line + `pulse.md` body.
   - Call `google_docs_append_text` with `prepend_newline: true`.
   - Use a stable `request_id` per week (e.g. `groww-pulse-docs-{week_ending}`) so re-runs do not double-append.
4. On success: write `doc_url` (and `document_id` if returned/known) into `pulse.json` + run logs.
5. On Docs / MCP failure: **do not** proceed to Gmail; surface a clear error; leave local `pulse.*` intact (already validated in Phase 4).
6. Wire into orchestrator after gates pass: local pulse → Docs append → (Phase 6) email.
7. Manual verify: open the configured Doc; newest section shows header + top themes + quotes + actions.

### Exit criteria

- [ ] Pulse section appears in the **configured existing** Google Doc via `google_docs_append_text` (no custom Google REST client in this app)
- [ ] `doc_url` / `document_id` captured in `pulse.json` for the email phase
- [ ] Re-run with same `request_id` does not double-append (idempotent)
- [ ] Auth/OAuth/token store stay in MCP server env (Railway / local), not app code
- [ ] Docs failure blocks Phase 6

### Depends on

Phase 4 · MCP server healthy · Operator-created target Doc id/URL in config.

### Maps to

Problem statement: put note in Google Docs · Architecture §4.6, §8 · MCP tool `google_docs_append_text`

### Explicit non-goals for Phase 5

- Creating a new Google Doc per week (server limitation — [known limitations](https://github.com/ambrosh7/gmail-docs-mcp-server#known-limitations))
- Replacing/clearing the whole Doc each week (append-only rolling log is the v1 pattern)

---

## Phase 6 — Gmail notify via MCP

**Goal:** Email self/alias with the pulse (or Doc link) after a successful Docs publish.

**Server:** same as Phase 5 — [gmail-docs-mcp-server](https://github.com/ambrosh7/gmail-docs-mcp-server).

**Tool (exact name):** `gmail_send_email`

| Arg | Required | Notes |
| --- | --- | --- |
| `to` | yes | Array of addresses; use `[email_recipient]` from config |
| `subject` | yes | Plain text; never silently altered by the server |
| `body` | yes | Plain text only (HTML not enabled) |
| `request_id` | no | Idempotency key for safe retries |

**Constraint (v1 lock):** The server **sends a real email** (`gmail.send` scope). It does **not** create Gmail drafts, and cannot read/search the mailbox. Treat notify as an explicit send after Docs success; prefer client/tool approval when the MCP host supports it. Use `request_id` (e.g. `groww-pulse-mail-{week_ending}`) so retries do not double-send.

> Original problem-statement wording said “draft email.” With this MCP server, v1 delivers a **sent** plain-text message instead. If a true draft-only flow is required later, extend the MCP server (out of scope for this app’s Phases 5–6).

### Work

1. Confirm Gmail path on the same MCP server (`gmail_send_email` listed; health already checked in Phase 5).
2. Implement thin `GmailNotifier` adapter (not a drafts API):
   - `notify(to, subject, body, *, request_id) → { status, request_id }` (capture whatever the tool returns; no `draft_id`).
3. Subject: `Groww Weekly Pulse — week ending YYYY-MM-DD` (align with `doc_title_template` / week_ending).
4. Body (plain text):
   - Short intro + prominent `doc_url` from Phase 5 (preferred), **and/or**
   - Full pulse text from `pulse.md` if Doc link missing/unwanted.
   - No reviewer PII (gates already ran; do not add identity fields).
5. Recipient from `email_recipient` config (self or alias).
6. Wire orchestrator: **Notify runs only after successful Docs append** (Phase 5). Docs failure → skip email.
7. Manual verify: message arrives in the recipient inbox (Sent folder of the authorized MCP Google account); content matches pulse / Doc link.
8. Optional: set MCP `WRITE_ACTIONS_REQUIRE_CONFIRMATION` / Cursor tool approval so the operator confirms recipient/subject/body before send.

### Exit criteria

- [ ] Email **sent** via `gmail_send_email` MCP tool (no custom Gmail REST client in this app)
- [ ] Body contains pulse content and/or clear pointer to Doc (`doc_url`)
- [ ] No reviewer PII in email body
- [ ] Docs failure prevents email send
- [ ] Same `request_id` retry does not double-send
- [ ] Auth stays in MCP server env, not app code

### Depends on

Phase 5 · Same MCP server configured · `email_recipient` set in local settings.

### Maps to

Problem statement: deliver pulse by email · Architecture §4.7, §8 · MCP tool `gmail_send_email` (send, not draft)

### Explicit non-goals for Phase 6

- Gmail draft create / save-without-send (not exposed by MCP server)
- HTML email, attachments, CC/BCC-heavy workflows
- Reading inbox to verify delivery in automation (manual verify is enough for v1)

---

## Phase 7 — Hardening & Handoff

**Goal:** Make the weekly run reliable and acceptable against success criteria.

### Work

1. End-to-end acceptance against problem statement checklist:
   - Play reviews 8–12 weeks
   - ≤5 themes; pulse top 3
   - 3 quotes, 3 actions, ≤250 words
   - Docs append + Gmail **send** via MCP (`google_docs_append_text`, `gmail_send_email`)
   - No PII
2. Flesh out README: how to refresh Play export, set `google_doc_id` / `email_recipient`, run orchestrator, verify Doc section + inbox message; note Railway MCP host + health check.
3. Align ops with architecture weekly checklist (§13).
4. Add fixture-based regression tests for scrub, theme cap, gates; mock MCP adapters for publish/notify unit tests.
5. Note deferred work: App Store ingest; MCP-side Doc create / Gmail draft (non-goals given current server).

### Exit criteria

- [x] All problem-statement success criteria checked off (email delivery = sent message, not draft)
- [x] Fresh operator can run a pulse from README alone ([`ops-checklist.md`](./ops-checklist.md))
- [x] Known failure modes documented ([`failure-modes.md`](./failure-modes.md))

### Depends on

Phases 4–6.

---

## Milestone Summary

| Milestone | After phase | Demo-able result |
| --- | --- | --- |
| M1 — Clean corpus | 1 | Scrubbed Play reviews JSON |
| M2 — Insight draft | 3 | Local pulse.md meeting 3/3/3 + word limit |
| M3 — Local E2E | 4 | One-command local pipeline |
| M4 — Stakeholder surfaces | 6 | Doc append + Gmail send via MCP |
| M5 — Ship | 7 | Documented weekly ritual |

---

## Suggested Sequencing Tips

1. **Do not block on MCP early** — finish Phases 0–4 so theming/pulse quality is solid before Docs/Gmail.
2. **Lock quote integrity early** — Phase 2/3 tests for verbatim quotes prevent rework in publish.
3. **Sample before live dump** — accept Phase 3 on `groww_play_reviews_sample.csv`, then run the same pulse command on the large Play export.
4. **Adapter boundary** — keep MCP tool names (`google_docs_append_text`, `gmail_send_email`) out of theme/pulse code; only adapters know server/transport specifics.
5. **Play-only discipline** — reject App Store paths in ingest so scope does not creep mid-build.
6. **Match the real MCP surface** — append-only Doc + real email send; do not plan “create Doc” or “create draft” against this server.
7. **Idempotency** — always pass `request_id` on MCP writes so weekly re-runs are safe.

---

## Out of Scope (do not schedule in v1)

- Apple App Store / App Store Connect ingest
- Custom Google OAuth + REST as primary Docs/Gmail path (auth stays in [gmail-docs-mcp-server](https://github.com/ambrosh7/gmail-docs-mcp-server))
- Creating Google Docs or Gmail drafts (not exposed by the MCP server)
- Real-time alerts, support ticketing, full analytics dashboards
- Storing or displaying reviewer identities

---

## Traceability

| Success criterion | Delivered by |
| --- | --- |
| Play reviews ~8–12 weeks | Phase 1 |
| ≤5 themes; pulse top 3 | Phases 2–3 |
| 3 themes, 3 quotes, 3 actions; ≤250 words | Phase 3 (sample golden path + live run) |
| Google Docs via MCP (`google_docs_append_text`) | Phase 5 |
| Gmail notify via MCP (`gmail_send_email`, send not draft) | Phase 6 |
| No PII in artifacts | Phases 1, 3, 7 |
