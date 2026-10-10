# Architecture — Groww Weekly Review Pulse

Source of truth for requirements: [`problemStatement.md`](./problemStatement.md).

## 1. Purpose

This system turns public **Google Play** reviews for **Groww** into a scannable weekly pulse and delivers it through:

| Surface | Role |
| --- | --- |
| **Google Docs** | Canonical written pulse stakeholders can open |
| **Gmail** | Draft email (to self/alias) with the note or a link to the Doc |

Design principle: **MCP-first delivery**. Docs and Gmail are reached via MCP tool calls, not custom Google OAuth/REST clients.

---

## 2. System Context

```text
┌──────────────┐     public exports      ┌─────────────────────────┐
│ Google Play  │ ──────────────────────► │  Weekly Review Pulse    │
│ Store only   │   (CSV/JSON/files)      │  (agent + pipeline)     │
└──────────────┘                         └───────────┬─────────────┘
                                                     │
                          MCP tools                  │
              ┌──────────────────────────────────────┼────────────────┐
              ▼                                      ▼                │
     ┌─────────────────┐                   ┌─────────────────┐        │
     │ Google Docs MCP │                   │   Gmail MCP     │        │
     │ create/update   │                   │ create draft    │        │
     └────────┬────────┘                   └────────┬────────┘        │
              ▼                                      ▼                │
     ┌─────────────────┐                   ┌─────────────────┐        │
     │ Pulse document  │◄──── link ────────│ Draft email     │        │
     └─────────────────┘                   └─────────────────┘        │
                                                                     │
     Human (PM / Support / Leadership) reads Doc + sends draft ──────┘
```

> **Scope:** Apple App Store reviews are **out of scope for now**. Ingest and schema assume Play Store only; App Store can be added later without changing the Docs/Gmail delivery path.

**Actors**

| Actor | Interaction |
| --- | --- |
| Operator (agent or CLI) | Runs ingest → theme → write → publish → draft |
| Product / Growth / Support / Leadership | Consume Doc + optional email |
| Store data sources | Provide public **Play Store** review exports only |

---

## 3. High-Level Architecture

The system is a **linear pipeline with clear stage contracts**, orchestrated by an agent (or scripted runner) that calls each stage and then MCP tools for delivery.

```text
┌─────────┐   ┌──────────┐   ┌───────────┐   ┌────────────┐   ┌──────────┐   ┌────────────┐
│ Ingest  │──►│ Normalize│──►│  Theme    │──►│  Pulse     │──►│ Publish  │──►│  Notify    │
│ reviews │   │ + scrub  │   │ (≤5)      │   │  writer    │   │ Docs MCP │   │ Gmail MCP  │
└─────────┘   └──────────┘   └───────────┘   └────────────┘   └──────────┘   └────────────┘
     │              │              │                │
     ▼              ▼              ▼                ▼
  raw/*.csv     reviews.json   themes.json     pulse.md / pulse.json
```

| Stage | Responsibility | Output artifact |
| --- | --- | --- |
| **Ingest** | Load public **Play Store** exports for last 8–12 weeks | Raw files under `data/raw/` |
| **Normalize** | Unified schema, date window filter, PII scrub | `data/processed/reviews.json` |
| **Theme** | Cluster into ≤5 themes; rank by volume/severity | `data/processed/themes.json` |
| **Pulse writer** | Top 3 themes, 3 quotes, 3 actions; ≤250 words | `data/output/pulse.md` (+ structured JSON) |
| **Publish** | Create/update Google Doc via MCP | Doc URL / ID |
| **Notify** | Create Gmail draft via MCP (body + Doc link) | Draft ID |

Stages are **idempotent where practical**: re-running with the same input window should overwrite intermediate artifacts rather than append duplicates.

---

## 4. Component Design

### 4.1 Orchestrator

- Entry point for a weekly run (agent prompt, CLI, or scheduled job).
- Owns stage ordering, failure short-circuit, and logging of artifact paths.
- Does **not** embed Google API credentials; only invokes MCP tools at Publish/Notify.

Suggested interface:

```text
run_weekly_pulse(window_weeks=10, recipient="me@example.com")
  → { doc_url, draft_id, pulse_path, theme_count }
```

### 4.2 Ingest

**Allowed sources**

- Manual or official public **Play Store** exports (e.g. Play Console export or other ToS-compliant public dumps for `com.nextbillion.groww`).
- **App Store / App Store Connect exports are out of scope for now.**
- No authenticated scraping, no store login automation, no ToS-violating crawlers.

**Inputs**

| Field (typical) | Notes |
| --- | --- |
| rating | 1–5 |
| title | Optional (Play reviews often omit a separate title) |
| text / body | Review body |
| date | Review timestamp / date |
| store | Always `play` in v1 |
| locale / language | Optional; useful for filtering `en_IN` |

**Window**: Keep only reviews with `date` in `[now - W weeks, now]` where `W ∈ [8, 12]`.

### 4.3 Normalize + Privacy Scrubber

Transforms heterogeneous exports into a single internal schema and strips PII before any clustering or writing.

**Internal review schema**

```json
{
  "id": "stable-hash-or-export-id",
  "store": "play",
  "rating": 2,
  "title": "optional",
  "text": "scrubbed review body",
  "date": "2026-09-01",
  "locale": "en_IN"
}
```

**PII rules (hard)**

- Drop usernames, emails, phone numbers, device IDs, account numbers.
- Quotes in the pulse must be anonymous (no reviewer identity).
- Scrub before themes and before any Doc/email content is generated.

### 4.4 Theming Engine

**Constraints**

- Produce **at most 5** themes total.
- Pulse surfaces only the **top 3**.

**Suggested Groww-oriented theme vocabulary** (adapt from data):

1. Onboarding / signup  
2. KYC / verification  
3. Payments / UPI / deposits  
4. Trading / orders / quotes  
5. Withdrawals / settlements / statements  

Themes should be **data-driven**: if the corpus clusters differently (e.g. app crashes, customer support), rename themes to match evidence — still capped at 5.

**Theme record**

```json
{
  "theme_id": "kyc",
  "label": "KYC / verification",
  "review_ids": ["..."],
  "count": 42,
  "avg_rating": 2.1,
  "representative_quotes": ["verbatim...", "verbatim..."],
  "rank_score": 0.87
}
```

**Ranking heuristic (example)**

```text
rank_score = normalize(count) * 0.6 + normalize(negative_rating_weight) * 0.4
```

Prefer themes that are both frequent and painful (low ratings). Document the exact formula in code comments when implemented.

**Clustering approach (implementation choice)**

| Approach | When to use |
| --- | --- |
| LLM labeling with fixed theme budget | Fast to ship; good for course/agent workflows |
| Embedding + clustering then label | Better scale; still map clusters → ≤5 labels |
| Keyword / rule seed + LLM refine | Controllable for known Groww pain areas |

All approaches must attach **verbatim** quote candidates from real review text.

### 4.5 Pulse Writer

Produces a **one-page weekly note** that is scannable and **≤250 words**.

**Required sections**

1. **Header** — product, week ending date, review count, date window  
2. **Top 3 themes** — short bullets (what + why it matters)  
3. **3 user quotes** — verbatim, anonymous  
4. **3 action ideas** — concrete, theme-grounded next steps  

**Structured companion** (`pulse.json`) recommended for machine reuse:

```json
{
  "week_ending": "2026-10-10",
  "window_weeks": 10,
  "review_count": 380,
  "themes": [{ "label": "...", "summary": "..." }],
  "quotes": [{ "text": "...", "theme": "...", "rating": 1 }],
  "actions": [{ "title": "...", "rationale": "...", "theme": "..." }],
  "word_count": 210,
  "doc_url": null
}
```

**Writer rules**

- Never invent quotes or paraphrase as if verbatim.
- Actions must map to observed themes (no generic “improve UX” without theme link).
- Enforce word-count check before publish; trim if over 250.

### 4.6 Publish (Google Docs MCP)

- Create a new Doc or update a known weekly Doc template.
- Body = rendered pulse (from `pulse.md` or structured fields).
- Capture returned document URL/ID into `pulse.json` and run logs.
- Auth and HTTP stay inside the MCP server — app only calls tools.

### 4.7 Notify (Gmail MCP)

- Create a **draft** (not necessarily send) to self or configured alias.
- Subject example: `Groww Weekly Pulse — week ending YYYY-MM-DD`.
- Body: short intro + full note **or** summary + prominent Doc link.
- No PII beyond the operator’s own address as recipient.

---

## 5. End-to-End Data Flow

```text
1. Operator places / provides public **Play Store** exports for Groww
2. Ingest loads files → filter last 8–12 weeks
3. Normalize maps fields → scrub PII → reviews.json
4. Theme engine clusters ≤5 themes → ranks → themes.json
5. Pulse writer selects top 3 + 3 quotes + 3 actions → pulse.md / pulse.json
6. Word-count + privacy validation gates
7. Docs MCP: create/update pulse document → doc_url
8. Gmail MCP: create draft with note and/or doc_url → draft_id
9. Operator opens Doc; optionally sends the draft
```

**Failure behavior**

| Failure | Behavior |
| --- | --- |
| Empty / too-few reviews in window | Abort with clear message; do not publish empty pulse |
| Theme count would exceed 5 | Merge lowest-ranked clusters until ≤5 |
| Word count > 250 | Auto-trim summaries; fail gate if still over |
| PII detector hit post-scrub | Block publish; log which field/pattern |
| Docs MCP failure | Do not create email draft; surface error |
| Gmail MCP failure | Doc may already exist; report Doc URL + email error |

---

## 6. Suggested Repository Layout

```text
AI Agents/
├── docs/
│   ├── problemStatement.md
│   └── architecture.md          ← this file
├── data/
│   ├── raw/                     # public exports (gitignored if bulky)
│   ├── processed/
│   │   ├── reviews.json
│   │   └── themes.json
│   └── output/
│       ├── pulse.md
│       └── pulse.json
├── src/
│   ├── ingest/
│   ├── normalize/
│   ├── theme/
│   ├── pulse/
│   ├── validate/
│   └── orchestrator/
├── prompts/                     # agent / LLM prompts for theme + pulse
├── config/
│   └── settings.example.yaml    # window weeks, recipient, theme labels
└── README.md
```

Exact language/runtime is an implementation choice; the stage boundaries above should stay stable.

---

## 7. Configuration

| Key | Description | Default / guidance |
| --- | --- | --- |
| `product_name` | Display name in pulse | `Groww` |
| `play_package_id` | Play listing id | `com.nextbillion.groww` |
| `window_weeks` | Review lookback | `10` (allowed 8–12) |
| `max_themes` | Clustering budget | `5` |
| `pulse_top_themes` | Themes in written note | `3` |
| `quote_count` | Verbatim quotes in note | `3` |
| `action_count` | Action ideas in note | `3` |
| `max_pulse_words` | Length gate | `250` |
| `email_recipient` | Draft To: | operator / alias |
| `doc_title_template` | Docs title pattern | `Groww Weekly Pulse — {week_ending}` |

Secrets (Google auth) live in the **MCP server environment**, not in app config files committed to git.

---

## 8. Integration Architecture (MCP)

```text
┌────────────────────┐
│ Orchestrator       │
│ publish_pulse()    │──► MCP: docs.create / docs.update
│ notify_draft()     │──► MCP: gmail.create_draft
└────────────────────┘
           │
           │  tool-call protocol only
           ▼
┌────────────────────┐
│ MCP host runtime   │  (Cursor / course tooling / agent runtime)
└─────────┬──────────┘
          │
    ┌─────┴─────┐
    ▼           ▼
 Docs server  Gmail server
 (OAuth/API)  (OAuth/API)
```

**Rules**

- Primary path for Docs/Gmail is MCP tool invocation.
- Do not build a bespoke Google OAuth + REST client as the main integration.
- Map concrete tool names to whatever Docs/Gmail MCP servers the environment provides; keep a thin adapter layer so tool renames do not rewrite business logic.

**Adapter sketch**

```text
DocsPublisher.publish(title, markdown) → { doc_id, url }
GmailDrafts.create(to, subject, body_html_or_text) → { draft_id }
```

---

## 9. Validation Gates

Run before Publish:

| Gate | Pass condition |
| --- | --- |
| Window | Reviews span configured 8–12 week policy |
| Themes | `1 ≤ theme_count ≤ 5` |
| Pulse shape | Exactly 3 themes, 3 quotes, 3 actions (or clearly documented soft fail if data-starved) |
| Verbatim quotes | Each quote substring-matches a scrubbed review body |
| Word count | `≤ 250` |
| Privacy | No email/phone/device-id patterns in pulse text |

---

## 10. Privacy & Compliance

| Rule | Enforcement point |
| --- | --- |
| Public exports only | Ingest policy + README |
| No store-login scraping | Out of scope by design |
| No PII in artifacts | Normalize scrub + pre-publish validator |
| Anonymous quotes | Strip identity fields; never print reviewer names |

Artifacts under `data/output/` are considered shareable with stakeholders only after gates pass.

---

## 11. Non-Goals

- **Apple App Store reviews** (deferred; Play Store only for now)
- Real-time review streaming or alerting
- Full customer-support ticketing integration
- Sentiment dashboards beyond the one-page pulse
- Direct Google API SDKs as the primary Docs/Gmail path
- Storing or displaying reviewer identities

---

## 12. Quality Attributes

| Attribute | Target |
| --- | --- |
| Scannability | Leadership can read the pulse in minutes |
| Traceability | Quotes and actions map back to themes and review ids |
| Repeatability | Same inputs → stable themes/pulse structure |
| Operability | One command / one agent run for the full weekly path |
| Safety | Privacy and ToS constraints never bypassed for convenience |

---

## 13. Weekly / Monthly Run Checklist (Operational)

See also [`ops-checklist.md`](./ops-checklist.md).

1. Refresh public **Play Store** review export for Groww (`fetch-reviews` or CSV).  
2. Set `window_weeks` (8–12), `google_doc_id` / URL, and `email_recipient`.  
3. Run orchestrator through Notify: `python -m src run --deliver` (or GitHub monthly Action).  
4. Confirm Doc URL opens with the newest appended section (themes / quotes / actions).  
5. Confirm Gmail **sent** message arrived (MCP `gmail_send_email` — not a draft).  
6. Spot-check: no invented quotes, no PII, ≤250 words.

---

## 14. Mapping to Problem Statement

| Requirement | Architecture coverage |
| --- | --- |
| Aggregate / theme / summarize | Ingest → Normalize → Theme → Pulse writer |
| Google Docs delivery | Publish via Docs MCP |
| Gmail draft | Notify via Gmail MCP |
| 8–12 weeks of reviews | Ingest window + config |
| ≤5 themes, top 3 in note | Theming engine + pulse writer |
| 3 quotes + 3 actions | Pulse writer + validation gates |
| Public Play Store reviews only (App Store deferred) | Ingest constraints + non-goals |
| No PII | Scrubber + privacy gate |
| ≤250 words | Word-count gate |
| MCP-first Google integrations | §8 Integration Architecture |

---

## 15. Open Implementation Decisions

These do not change the architecture; resolve during build:

1. Runtime language (Python vs TypeScript) and whether orchestration is agent-driven vs CLI-first.  
2. Exact Docs/Gmail MCP server packages available in the environment.  
3. Clustering method (LLM-only vs embeddings).  
4. Create-new-Doc each week vs append to a living Doc.  
5. When to add App Store ingest later (schema already has a `store` field reserved as `play` for v1).
