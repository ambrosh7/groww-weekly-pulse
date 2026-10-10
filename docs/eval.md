# Evaluation Plan — Groww Weekly Review Pulse

How we measure quality and “done” for each phase in [`implementation-plan.md`](./implementation-plan.md).

Related docs: [`problemStatement.md`](./problemStatement.md) · [`architecture.md`](./architecture.md) · [`edge-case.md`](./edge-case.md)

**v1 scope under eval:** Play Store only · App Store deferred · MCP-first Docs + Gmail

---

## 1. Purpose

Eval answers three questions before ship:

1. **Correctness** — Does the pipeline respect window, theme caps, verbatim quotes, privacy, and MCP delivery?
2. **Quality** — Is the weekly pulse useful and scannable for Product / Support / Leadership?
3. **Reliability** — Do failure modes from `edge-case.md` behave as specified (Block / Degrade / Skip)?

---

## 2. Eval Types

| Type | What | When | Pass signal |
| --- | --- | --- | --- |
| **Automated gates** | Deterministic checks on artifacts | Every local run + CI | All required gates green |
| **Fixture / regression** | Fixed Play-like CSVs for edge IDs | CI + Phase 7 | Expected exit codes + artifact shape |
| **LLM-assisted scoring** | Rubric scores for theme/action quality | After Phase 2–3 changes | Mean score ≥ threshold |
| **Human review** | PM/operator spot-check of pulse + Doc + draft | Phase 7 acceptance | Checklist signed off |
| **E2E smoke** | One-command run through Gmail draft | Pre-ship | Doc URL + draft ID exist |

---

## 3. Golden Assets

| Asset | Path (suggested) | Role |
| --- | --- | --- |
| Happy-path export | `tests/fixtures/happy_path_10w.csv` | Full local E2E |
| Edge fixtures | `tests/fixtures/*.csv` | Map to `edge-case.md` IDs |
| Golden pulse (optional) | `tests/golden/pulse.happy.md` | Structural diff / smoke, not exact wording lock |
| Eval config | `config/eval.yaml` | Thresholds, soft-fail flags, PII patterns |

**Rules for goldens**

- Fixtures are synthetic or anonymized public-style reviews — no real PII.
- Do not lock exact LLM prose in CI; lock **structure, caps, verbatim quotes, privacy**.
- For theme labels, eval similarity or allow-list of acceptable labels when non-deterministic.

---

## 4. Metrics Catalog

### 4.1 Hard metrics (must-pass for acceptance)

| Metric ID | Metric | Definition | Target |
| --- | --- | --- | --- |
| H1 | Window compliance | Share of `reviews.json` rows with `date` in configured window | **100%** |
| H2 | Play-only | Share of rows with `store == play` | **100%** |
| H3 | Theme count | `len(themes)` | **1–5** |
| H4 | Pulse theme count | Themes in pulse | **3** (or soft-fail policy documented) |
| H5 | Quote count | Quotes in pulse | **3** |
| H6 | Action count | Actions in pulse | **3** |
| H7 | Verbatim quote rate | Quotes that are substrings of scrubbed review `text` | **100%** |
| H8 | Word count | Whitespace word count of pulse body | **≤ 250** |
| H9 | PII hit rate | Regex hits for email/phone/device-id in pulse + email body | **0** |
| H10 | Docs publish | MCP create/update returns usable `doc_url` / id | **Success** |
| H11 | Gmail draft | MCP draft create returns `draft_id` | **Success** |
| H12 | No-publish on gate fail | Docs/Gmail not called when any hard gate fails | **100%** of fail runs |

### 4.2 Soft metrics (quality; track, don’t always block CI)

| Metric ID | Metric | Definition | v1 target |
| --- | --- | --- | --- |
| S1 | Theme coherence | Human/LLM: reviews in theme mostly about that theme (1–5) | Mean **≥ 3.5** |
| S2 | Action usefulness | Human/LLM: action is concrete and theme-grounded (1–5) | Mean **≥ 3.5** |
| S3 | Quote representativeness | Quote illustrates its theme (1–5) | Mean **≥ 3.5** |
| S4 | Scannability | Can a reader get the point in &lt; 2 minutes (1–5) | Mean **≥ 4.0** |
| S5 | Ranking sanity | Top theme is among the two highest-volume or most negative themes (human) | **Pass** on happy path |
| S6 | Idempotence | Same fixture + config → same theme count, quote set stability* | Documented tolerance |

\*Exact theme labels may vary with LLM; quote set and counts should be stable if selection is deterministic post-theme.

### 4.3 Operational metrics

| Metric ID | Metric | Target |
| --- | --- | --- |
| O1 | Local pipeline success rate on happy fixture | **100%** in CI |
| O2 | Edge fixture expected Block/Degrade match rate | **100%** for listed IDs in §8 |
| O3 | Time to run local E2E (happy path) | Informative only (log) |

---

## 5. Scoring Rubrics (human / LLM judge)

Use 1–5 integer scores. Average across 3 themes / 3 actions / 3 quotes as applicable.

### Theme coherence (S1)

| Score | Meaning |
| --- | --- |
| 1 | Theme label unrelated to most assigned reviews |
| 3 | Mixed; roughly half fit |
| 5 | Clear, consistent theme; outliers rare |

### Action usefulness (S2)

| Score | Meaning |
| --- | --- |
| 1 | Generic (“improve UX”) with no theme link |
| 3 | Directionally relevant but vague |
| 5 | Concrete next step clearly tied to a named theme |

### Quote representativeness (S3)

| Score | Meaning |
| --- | --- |
| 1 | Quote off-theme or empty of meaning |
| 3 | Weakly related |
| 5 | Crisp illustration of the theme’s pain/praise |

### Scannability (S4)

| Score | Meaning |
| --- | --- |
| 1 | Dense, unstructured, hard to skim |
| 3 | Sections exist but noisy |
| 5 | Header + bullets; leadership-ready in minutes |

**Judge prompt constraints:** Judge must not reward invented quotes; if any quote fails verbatim check, overall quality eval is **auto-fail** regardless of soft scores.

---

## 6. Phase-Wise Eval (maps to implementation plan)

### Phase 0 — Foundations

| Check | Method | Pass |
| --- | --- | --- |
| Layout / config present | Manual or script | Matches architecture §6–7 |
| Secrets not in git | `git status` / scan | No tokens in tracked files |
| Fixture available | File exists | ≥1 Play-like export usable |
| `window_weeks` validation | Unit test | Reject &lt;8 or &gt;12 (E0.5) |

**Phase gate:** Phase 0 exit criteria checklist complete.

---

### Phase 1 — Ingest & Normalize

| Check | Metric / edge | Pass |
| --- | --- | --- |
| Schema fields present | Unit | All required keys on each row |
| Window filter | H1 | 100% |
| Play-only | H2 | 100%; App Store dropped (E1.20–E1.21) |
| Empty window aborts | E1.16 | Non-zero exit, no `reviews.json` success claim |
| PII scrub | Spot + regex on `reviews.json` | No raw emails/phones/device ids |
| Bad rows skipped | E1.6–E1.9 | Pipeline continues; counts logged |
| Stable ids | E1.30 | Same input → same ids |

**Phase gate:** `reviews.json` from happy fixture + empty-window fixture behaves correctly.

---

### Phase 2 — Theming

| Check | Metric / edge | Pass |
| --- | --- | --- |
| Theme cap | H3, E2.2 | ≤5 after merge |
| Min themes on happy path | H3 | ≥1; typically ≥3 on rich fixture |
| Quote candidates verbatim | Substring check | 100% of candidates |
| No invented quotes | E2.7 | Fail if model quote not in corpus |
| Deterministic ranking ties | E2.4 | Stable order on fixture |
| Single-theme corpus | E2.3 | Does not crash; emits 1 theme |

**Phase gate:** `themes.json` valid; hard metrics H3 + verbatim candidates pass.

**Soft eval:** Score S1 on happy-path themes (sample 20 reviews/theme if large).

---

### Phase 3 — Pulse Writer & Gates

| Check | Metric / edge | Pass |
| --- | --- | --- |
| Shape 3/3/3 | H4–H6 | Exact on happy path |
| Verbatim quotes | H7, E3.7 | 100% |
| Word count | H8, E3.9–E3.10 | ≤250 |
| Privacy on pulse | H9, E3.15 | 0 hits |
| Data-starved &lt;3 quotes | E3.2 | Block (never invent) |
| Soft-fail themes &lt;3 | E3.1 | Matches `allow_soft_fail` config |
| Actions theme-linked | S2 + structural link field | Mean ≥3.5 on human sample |

**Phase gate:** All hard metrics H4–H9 pass on happy path; fail-closed on PII and invented quotes.

---

### Phase 4 — Local Orchestrator

| Check | Metric / edge | Pass |
| --- | --- | --- |
| One-command happy path | O1 | `pulse.md` + `pulse.json` written |
| Failure short-circuit | E4.1, H12 | Non-zero exit; no success pulse |
| Idempotent overwrite | E4.3 | Re-run replaces artifacts |
| Invalid weeks CLI | E4.6 | Reject before ingest |
| Atomic / consistent outputs | E4.2, E4.7 | No half-success pair left behind |

**Phase gate:** CI job runs orchestrator on happy + ≥3 edge fixtures with expected codes.

---

### Phase 5 — Docs MCP

| Check | Metric / edge | Pass |
| --- | --- | --- |
| Publish success | H10 | Doc opens with pulse sections |
| No custom Google REST as primary path | Manual / code review | MCP adapter only |
| Gate fail skips Docs | H12, E5.9 | Docs not called |
| MCP down | E5.1–E5.2 | Clear error; no Gmail |
| `doc_url` persisted | Artifact | Present in `pulse.json` |

**Phase gate:** Manual smoke — Doc URL from a real MCP run contains themes, quotes, actions.

---

### Phase 6 — Gmail MCP

| Check | Metric / edge | Pass |
| --- | --- | --- |
| Draft created | H11 | `draft_id` returned |
| Body has note or Doc link | Manual | Pass |
| Privacy on email body | H9 | 0 hits |
| Docs fail ⇒ no draft | E6.2, H12 | Invariant holds |
| Draft not auto-sent | E6.6–E6.7 | Only draft tool used |

**Phase gate:** Operator opens Gmail drafts; content acceptable; optional send left manual.

---

### Phase 7 — Hardening & Handoff

| Check | Method | Pass |
| --- | --- | --- |
| Problem-statement success criteria | §9 checklist below | All checked |
| Edge regression suite | O2 | Listed IDs green |
| README operable | Fresh-operator trial | Run without tribal knowledge |
| Soft metrics sample | S1–S4 | Meet v1 targets on happy path |
| Out-of-scope App Store | E7.4 | Not implemented; documented |

**Phase gate:** Ship / demo ready.

---

## 7. Automated Gate Suite (pre-publish)

Run in order; first failure stops publish/notify.

```text
1. load pulse.json + reviews.json + themes.json
2. assert H1–H3
3. assert H4–H6 (or soft-fail branch)
4. assert H7 verbatim
5. assert H8 word count
6. assert H9 privacy
7. only then allow Docs MCP → Gmail MCP
```

Suggested CLI: `pulse eval --artifacts data/` → exit `0` / `1`.

---

## 8. Minimum Edge Cases in CI

From [`edge-case.md`](./edge-case.md), these are **required** regression coverage before Phase 7 sign-off:

| Edge ID | Expect |
| --- | --- |
| E0.5 | Config reject |
| E1.16 / E1.29 | Block, empty corpus |
| E1.20 / E1.21 | App Store dropped / Block if only App Store |
| E1.22 | Email redacted in processed output |
| E2.2 | Theme merge to ≤5 |
| E2.7 / E3.7 | Invented quote rejected |
| E3.2 | &lt;3 quotes → Block |
| E3.9 | Over-length trimmed or Block |
| E3.15 | PII in pulse → Block |
| E4.1 / E4.6 | Orchestrator short-circuit / bad args |
| E5.9 | No Docs on gate fail (unit/mock) |
| E6.2 | No Gmail without Docs success (unit/mock) |
| EX.3 | Prompt-injection text treated as data |

MCP-live edges (E5.1, E6.1) are **manual/smoke** unless mocks exist.

---

## 9. Acceptance Checklist (problem statement)

| # | Criterion | Eval evidence | Owner |
| --- | --- | --- | --- |
| A1 | Play reviews ~8–12 weeks imported | H1, H2 + fixture/export dates | Eng |
| A2 | ≤5 themes; pulse top 3 | H3, H4 | Eng |
| A3 | 3 quotes, 3 actions, ≤250 words | H5, H6, H7, H8 | Eng |
| A4 | Google Docs via MCP | H10 + screenshot/URL | Eng + Operator |
| A5 | Gmail draft via MCP | H11 + draft visible | Eng + Operator |
| A6 | No PII in artifacts | H9 on `reviews.json`, pulse, email | Eng |
| A7 | Useful & scannable | S1–S4 human pass | PM |

**Ship rule:** A1–A6 all pass; A7 mean scores meet §4.2 targets on the happy-path run.

---

## 10. Eval Workflow Per Milestone

| Milestone (impl plan) | Required eval |
| --- | --- |
| M1 — Clean corpus | Phase 1 hard metrics + PII spot check |
| M2 — Insight draft | Phase 2–3 hard metrics + S1–S3 sample |
| M3 — Local E2E | Phase 4 CI suite + §8 fixtures |
| M4 — Stakeholder surfaces | Phase 5–6 smoke + H10–H12 |
| M5 — Ship | Full §9 checklist + soft metrics |

---

## 11. Human Eval Protocol (lightweight)

1. Run orchestrator on happy-path (and optional fresh Play export).  
2. Open `pulse.md` (and Doc if Phase 5+).  
3. Score S1–S4 using §5 rubrics (one rater OK for v1; two raters preferred).  
4. Confirm every quote appears in `reviews.json` text (spot-check all 3).  
5. Confirm no names/emails/phones in Doc + draft.  
6. Record scores + Doc URL + draft ID in a short eval log (`data/output/eval-log.md` or team doc).

**Time box:** ~15 minutes per weekly candidate pulse.

---

## 12. Failure Taxonomy (for eval logs)

| Code | Meaning | Typical phase |
| --- | --- | --- |
| `FAIL_WINDOW` | Empty/invalid date window | 1 |
| `FAIL_SCOPE` | Non-Play / App Store-only | 1 |
| `FAIL_THEME_CAP` | Could not reduce to ≤5 | 2 |
| `FAIL_QUOTE` | Missing/invented quotes | 2–3 |
| `FAIL_SHAPE` | Not 3/3/3 under strict mode | 3 |
| `FAIL_LENGTH` | &gt;250 words after trim | 3 |
| `FAIL_PII` | Privacy gate hit | 1/3/6 |
| `FAIL_DOCS_MCP` | Publish error | 5 |
| `FAIL_GMAIL_MCP` | Draft error | 6 |
| `FAIL_OPS` | Config/IO/orchestrator | 0/4 |

Use these codes in CI output and Phase 7 runbooks.

---

## 13. What We Explicitly Do Not Eval in v1

- App Store coverage or cross-store agreement  
- Real-time latency / streaming freshness  
- Perfect inter-rater theme taxonomy stability across weeks  
- Auto-send email delivery rates  
- Comparison to proprietary internal support ticket systems  

---

## 14. Traceability

| Implementation phase | Primary metrics | Edge coverage |
| --- | --- | --- |
| 0 | Config validation | E0.5–E0.6 |
| 1 | H1, H2, H9 (processed) | E1.* |
| 2 | H3, verbatim candidates | E2.* |
| 3 | H4–H9, S1–S4 | E3.* |
| 4 | O1, O2, H12 | E4.* |
| 5 | H10, H12 | E5.* |
| 6 | H11, H9 | E6.* |
| 7 | A1–A7 ship checklist | E7.*, EX.* |
