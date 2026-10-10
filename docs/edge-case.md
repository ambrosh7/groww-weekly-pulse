# Edge Cases & Corner Scenarios — Groww Weekly Review Pulse

Catalog of corner cases for each phase in [`implementation-plan.md`](./implementation-plan.md). Use this for tests, gate design, and operator runbooks.

**Legend**

| Severity | Meaning |
| --- | --- |
| **Block** | Abort the run; do not publish or draft |
| **Degrade** | Continue with documented fallback |
| **Skip** | Ignore the bad row/item; continue |
| **Config** | Fix config / environment; then retry |

---

## Phase 0 — Foundations

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E0.1 | `data/raw/` missing or empty | Fail fast with “place Play export in data/raw” | Block |
| E0.2 | Sample export older than 12 weeks only | Ingest will yield empty window later — warn at setup if dates are stale | Config |
| E0.3 | Sample mixes Play + App Store rows | Document Play-only; Phase 1 must drop/reject App Store | Skip / Block if all rows non-Play |
| E0.4 | Secrets committed (OAuth tokens, `.env`) | `.gitignore` must cover; rotate if leaked | Config |
| E0.5 | `window_weeks` set outside 8–12 | Reject at config load | Block |
| E0.6 | Missing `settings.yaml`; only example exists | Clear error pointing to copy `settings.example.yaml` | Config |

---

## Phase 1 — Ingest & Normalize

### File & format

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E1.1 | Unsupported file type (`.xlsx`, `.zip` only) | Error: unsupported format | Block |
| E1.2 | Corrupt / truncated CSV or invalid JSON | Parse error with file name; abort | Block |
| E1.3 | CSV with BOM / unexpected delimiter | Tolerate UTF-8 BOM; fail clearly on unknown delimiter | Degrade / Block |
| E1.4 | Duplicate files in `data/raw/` with overlapping reviews | Dedupe by stable `id` (or hash of store+date+text) | Degrade |
| E1.5 | Extremely large export (100k+ rows) | Stream/chunk if needed; still apply window before heavy work | Degrade |

### Field mapping

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E1.6 | Missing `text` / empty body | Skip row (cannot theme or quote) | Skip |
| E1.7 | Missing `rating` | Skip or default per policy (prefer skip) | Skip |
| E1.8 | Rating out of range (`0`, `6`, `"five"`) | Skip invalid rating rows | Skip |
| E1.9 | Missing or unparseable `date` | Skip row | Skip |
| E1.10 | Date formats mixed (`YYYY-MM-DD`, epoch ms, `DD/MM/YYYY`) | Normalize to ISO date; skip unparseable | Degrade / Skip |
| E1.11 | Timezone / UTC vs local midnight on window boundary | Define inclusive window in UTC (or documented TZ); test day edges | Degrade |
| E1.12 | Title present vs absent | Title optional; empty string OK | Degrade |
| E1.13 | Non-English / Hinglish / emoji-only reviews | Keep if in window; theming must tolerate | Degrade |
| E1.14 | HTML entities or escaped quotes in body | Unescape before scrub/theme | Degrade |
| E1.15 | Review for wrong package / app | Filter by `play_package_id` if field exists; else trust export source | Skip / Config |

### Scope & window

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E1.16 | All reviews outside 8–12 week window | Abort: empty corpus | Block |
| E1.17 | Only 1–2 reviews inside window | Proceed but flag “data-starved”; later phases may soft-fail 3/3/3 | Degrade |
| E1.18 | `window_weeks = 8` vs `12` changes theme mix | Deterministic for fixed `now` + config; document `week_ending` | — |
| E1.19 | Future-dated reviews (clock skew / bad export) | Drop dates `> now` | Skip |
| E1.20 | App Store rows present | Drop; log count skipped; if zero Play left → Block | Skip / Block |
| E1.21 | Operator tries App Store Connect export as sole input | Abort with Play-only scope message | Block |

### Privacy scrub

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E1.22 | Email in review body | Redact (e.g. `[email]`) | Degrade |
| E1.23 | Phone / UPI VPA-like strings | Redact | Degrade |
| E1.24 | Device ID / Android ID patterns | Redact | Degrade |
| E1.25 | Account / demat / order number-looking tokens | Redact conservatively | Degrade |
| E1.26 | Reviewer display name column in export | Never write to `reviews.json` | Skip field |
| E1.27 | PII-only body (entire text is an email) | After scrub, if text empty → skip row | Skip |
| E1.28 | False positive redaction (e.g. version `1.2.3`) | Prefer precise patterns; accept rare over-redaction vs leaking PII | Degrade |

### Output

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E1.29 | All rows skipped after validation | Abort: no usable reviews | Block |
| E1.30 | Re-run produces different `id`s for same reviews | Use stable hash so themes/quotes stay traceable | Degrade |

---

## Phase 2 — Theming Engine

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E2.1 | Fewer distinct topics than 5 (e.g. only 2) | Emit 2 themes; OK if `1 ≤ count ≤ 5` | Degrade |
| E2.2 | Clustering produces >5 themes | Merge lowest `rank_score` until ≤5 | Degrade |
| E2.3 | All reviews map to one theme | Single theme OK for engine; pulse soft-fail on “top 3” (see E3.x) | Degrade |
| E2.4 | Tie on `rank_score` | Deterministic tie-break (e.g. label alpha, then `theme_id`) | Degrade |
| E2.5 | Theme with zero quote candidates (all texts too short) | Exclude from pulse quote pool; if no quotes globally → Block at pulse | Degrade / Block |
| E2.6 | LLM invents theme labels unrelated to Groww | Prefer data-driven labels; allow rename; still cap at 5 | Degrade |
| E2.7 | LLM invents quotes not in source text | Reject; only attach substrings that match review bodies | Block (for that quote) |
| E2.8 | Seed vocabulary missing (no KYC mentions) | Do not force empty KYC theme; drop unused seeds | Degrade |
| E2.9 | Spam / one-word reviews (`"Good"`, `"Worst"`) | Low information: bucket to “general praise/complaint” or exclude from quotes | Skip / Degrade |
| E2.10 | Duplicate near-identical reviews | Dedupe or down-weight so one spam campaign ≠ top theme alone | Degrade |
| E2.11 | Extreme rating skew (all 1★ or all 5★) | Ranking still works; note skew in theme stats | Degrade |
| E2.12 | Non-deterministic LLM cluster labels across runs | Fix temperature/seed or post-process label canonicalize for idempotence | Degrade |
| E2.13 | Empty `reviews.json` passed to themer | Abort | Block |
| E2.14 | Review belongs to multiple themes | Allow primary theme only for v1 (or multi-label with single primary for ranking) | Degrade |

---

## Phase 3 — Pulse Writer & Validation Gates

### Shape (3 themes / 3 quotes / 3 actions)

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E3.1 | Only 1–2 themes available | Soft-fail policy: document in pulse (“only N themes”); do not invent themes. Prefer Block for strict acceptance unless `allow_soft_fail` config | Config / Block |
| E3.2 | Fewer than 3 usable verbatim quotes | Block gate (cannot invent wording) | Block |
| E3.3 | Quotes all from one theme | Prefer diversify; if impossible, allow with log warning | Degrade |
| E3.4 | Same quote selected three times | Deduplicate; pick next candidates | Degrade |
| E3.5 | Quote longer than usable for one-pager | Truncate with ellipsis only if remaining substring still verbatim-matches; else pick shorter quote | Degrade |
| E3.6 | Action ideas generic / not theme-linked | Reject in validation; regenerate or Block | Block |
| E3.7 | LLM rewrites quote “for clarity” | Gate fails verbatim check | Block |
| E3.8 | Actions mention internal users or PII | Privacy gate fails | Block |

### Length & content

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E3.9 | Word count > 250 after first draft | Auto-trim summaries; re-count; if still >250 → Block | Degrade / Block |
| E3.10 | Word count boundary exactly 250 | Pass | — |
| E3.11 | Counting ambiguity (hyphenated words, numbers) | Document tokenizer (whitespace split is OK for v1); use consistently | Degrade |
| E3.12 | Pulse in mixed language | Allowed if quotes are verbatim; summaries can be English for stakeholders | Degrade |
| E3.13 | Markdown injection / weird characters in quotes | Escape or plain-text render for Doc/email safety; do not alter quote meaning | Degrade |
| E3.14 | Header missing week_ending / review_count | Invalid pulse shape → Block | Block |

### Privacy (post-write)

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E3.15 | PII slipped into summary (model copied a phone) | Privacy gate Block; do not publish | Block |
| E3.16 | Reviewer name appears inside quote text | Prefer different quote; or redact and **fail verbatim** → choose another quote | Block / Skip quote |

---

## Phase 4 — Local Orchestrator

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E4.1 | Mid-pipeline failure (theme crashes) | Short-circuit; no “success” pulse written; leave prior artifacts untouched or mark incomplete | Block |
| E4.2 | Partial write (pulse.md written, pulse.json not) | Atomic write (temp + rename) or delete incomplete pair on failure | Degrade |
| E4.3 | Re-run same week | Overwrite `reviews.json` / `themes.json` / `pulse.*` — no duplicate append | Degrade |
| E4.4 | Concurrent two runs | Lock file or document “do not run concurrent”; last writer wins is unsafe | Config |
| E4.5 | Disk full / permission denied on `data/` | Clear IO error; abort | Block |
| E4.6 | Invalid CLI args (`--weeks 3`) | Validation error before ingest | Block |
| E4.7 | Gate fail after pulse draft on disk | Delete or quarantine failed pulse; exit non-zero | Block |
| E4.8 | Stale processed files from last month left in place | Always regenerate from raw for the run; do not merge stale themes silently | Degrade |

---

## Phase 5 — Google Docs via MCP

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E5.1 | Docs MCP server not installed / not running | Abort publish; no Gmail | Config / Block |
| E5.2 | Auth expired / user not signed in | Surface MCP auth error; abort | Config / Block |
| E5.3 | Tool name mismatch after server upgrade | Adapter error; fix mapping | Config |
| E5.4 | Doc create succeeds, URL missing in response | Treat as failure unless ID can build URL; do not proceed to Gmail without pointer | Block |
| E5.5 | Network timeout mid-create | Retry once (optional); else Block; avoid duplicate Docs if unsure | Block |
| E5.6 | Duplicate weekly title (create-new-each-week) | Allow duplicates or suffix timestamp; document choice | Degrade |
| E5.7 | Update-template mode but template Doc deleted | Fail with clear message; do not create email | Block |
| E5.8 | Markdown → Docs formatting loss | Accept plain structure; ensure quotes/actions still readable | Degrade |
| E5.9 | Pulse failed gates but publish called anyway | Orchestrator must not call Docs | Block |
| E5.10 | Very long single line / special Unicode breaks Docs tool | Fallback to simpler plain text payload | Degrade |

---

## Phase 6 — Gmail Draft via MCP

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E6.1 | Gmail MCP unavailable | Report Doc URL + email failure; Doc may stand alone | Degrade |
| E6.2 | Docs failed but Notify still invoked | Must not happen — orchestrator invariant | Block |
| E6.3 | Invalid `email_recipient` | Validation error before MCP call | Block |
| E6.4 | Draft create returns no `draft_id` | Treat as failure | Block |
| E6.5 | Body too large for draft API | Prefer Doc-link-only body | Degrade |
| E6.6 | Operator expected “sent”, got “draft” | By design — document; send is manual | — |
| E6.7 | Accidental send tool used instead of draft | Never call send in v1 | Block (policy) |
| E6.8 | Email body includes raw export snippets with PII | Re-run privacy gate on email body | Block |
| E6.9 | Missing `doc_url` when body strategy is link-only | Block or fall back to full pulse text if gates passed | Degrade / Block |
| E6.10 | Duplicate drafts on re-run | Accept multiple drafts or idempotency key in subject+date; document | Degrade |

---

## Phase 7 — Hardening & Handoff

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| E7.1 | Acceptance with fixture data only (no live MCP) | Local criteria pass; MCP criteria marked blocked on env | Config |
| E7.2 | README omits Play-only / no-scrape rules | Treat as release blocker | Block |
| E7.3 | Regression: scrubber loosened and PII reappears | Fixture tests must catch | Block |
| E7.4 | Stakeholder asks for App Store “quick add” | Point to non-goals; do not hack into v1 ingest | Skip |

---

## Cross-Cutting Scenarios

| ID | Scenario | Expected handling | Severity |
| --- | --- | --- | --- |
| EX.1 | Clock change / DST during window calc | Use timezone-aware library; document TZ | Degrade |
| EX.2 | `now` mocked in tests vs real runs | Tests inject clock; prod uses system time | — |
| EX.3 | Prompt injection in review text (“ignore instructions…”) | Treat as plain user content; never follow review instructions in LLM prompts | Degrade |
| EX.4 | Reviews insulting / abusive | Keep for product signal; no extra PII; quotes OK if anonymous | Degrade |
| EX.5 | Legal / regulatory complaint in reviews | Still theme normally; actions may flag “escalate to compliance” without storing PII | Degrade |
| EX.6 | Partial MCP success (Doc created, local `pulse.json` not updated) | Retry status write; log Doc id from MCP response for recovery | Degrade |
| EX.7 | Operator cancels mid-run | Leave artifacts consistent; non-zero exit | Block |

---

## Soft-Fail Matrix (data-starved runs)

When the corpus is too thin for a perfect 3/3/3 pulse:

| Condition | Strict mode (default for acceptance) | Soft mode (`allow_soft_fail: true`) |
| --- | --- | --- |
| Themes < 3 | Block | Pulse with available themes; state limitation in header |
| Quotes < 3 | Block | Block still (never invent quotes) |
| Actions < 3 | Block | Block or regenerate once; no filler actions |
| Reviews < N (e.g. 10) | Warn + continue if gates pass | Warn |

**Rule:** Soft mode never invents verbatim quotes or PII-bearing content.

---

## Recommended Test Fixtures

Maintain small fixtures under e.g. `data/raw/fixtures/` (or `tests/fixtures/`):

| Fixture | Covers |
| --- | --- |
| `empty.csv` | E1.16 / E1.29 |
| `outside_window.csv` | E1.16 |
| `pii_heavy.csv` | E1.22–E1.27, E3.15 |
| `short_quotes.csv` | E2.5, E3.2 |
| `single_theme.csv` | E2.3, E3.1 |
| `rating_junk.csv` | E1.7–E1.8 |
| `app_store_mixed.csv` | E1.20–E1.21 |
| `prompt_injection.csv` | EX.3 |
| `happy_path_10w.csv` | Full local E2E |

---

## Quick Triage

```text
Empty / unusable reviews     → Block at Phase 1
Theme/quote integrity fail   → Block at Phase 2–3 gates
Local IO / config errors     → Block at Phase 0/4
Docs MCP fail                → Block; no Gmail
Gmail MCP fail               → Degrade; keep Doc URL in logs
PII detected anytime         → Block publish & draft
App Store–only input         → Block (out of scope)
```

---

## Traceability

| Implementation phase | Edge-case IDs |
| --- | --- |
| Phase 0 | E0.1–E0.6 |
| Phase 1 | E1.1–E1.30 |
| Phase 2 | E2.1–E2.14 |
| Phase 3 | E3.1–E3.16 |
| Phase 4 | E4.1–E4.8 |
| Phase 5 | E5.1–E5.10 |
| Phase 6 | E6.1–E6.10 |
| Phase 7 | E7.1–E7.4 |
| Cross-cutting | EX.1–EX.7 |
