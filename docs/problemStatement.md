# Problem Statement — Groww Weekly Review Pulse

## Product

**Groww** (Stocks, Mutual Funds, IPO) — [Google Play listing](https://play.google.com/store/apps/details?id=com.nextbillion.groww&hl=en_IN)

## Goal

Turn raw **Google Play** feedback into a **weekly pulse** the team can scan in minutes: what users care about, what they actually said, and what to do next.

> **Scope note:** Apple App Store reviews are **out of scope for now**. v1 uses Play Store reviews only.

Reviews are already public. The system should **aggregate, theme, summarize, and deliver** that insight through familiar surfaces:

- **Google Docs** — written weekly pulse
- **Gmail** — draft email you can send yourself

Credentials and REST wiring should not be handled manually; integrations go through MCP.

## End-to-End Flow (“Done”)

1. Pull recent **Google Play Store** reviews for Groww (within the constraints below).
2. Cluster them into a small set of themes and distill a one-page weekly note.
3. Put that note where stakeholders can read it (Google Docs).
4. Create a draft email to yourself (or an alias) that contains or links to that pulse (Gmail).

## Deliverables

The weekly one-page pulse must include:

| Element | Requirement |
| --- | --- |
| Top themes | What people are talking about most |
| Real user quotes | Verbatim snippets from reviews — no invented wording |
| Three action ideas | Concrete next steps grounded in the themes |
| Draft email | Send yourself a draft containing the weekly note (or a clear pointer to it) |

## Who This Helps

| Audience | Why |
| --- | --- |
| Product / Growth | Prioritize fixes and improvements from real signals |
| Support | Align messaging with what users are actually saying |
| Leadership | One-page health check without drowning in raw reviews |

## What You Must Build

1. **Import Play Store reviews** from roughly the last **8–12 weeks** (fields such as rating, title, text, date — whatever the export provides).
2. **Group reviews** into at most **5 themes** (examples: onboarding, KYC, payments, statements, withdrawals — pick what fits Groww).
3. **Generate a weekly one-page note** with:
   - Top 3 themes (subset of your themes as appropriate)
   - 3 user quotes
   - 3 action ideas
4. **Draft an email** with the note to yourself or an alias.

## Integrations: Google Docs & Gmail via MCP

Use **MCP (Model Context Protocol)** servers for Google Docs and Gmail — for example, creating or updating the pulse document and creating the draft message — rather than integrating Google APIs directly (no bespoke OAuth client + REST client code as the primary integration path).

MCP servers expose tools the agent or app can call; lean on that pattern so Docs and Gmail stay consistent with course tooling and avoid duplicating auth and HTTP plumbing.

> Requirement is **MCP-first**, not “call Google APIs manually.” Choose MCP servers or connectors the environment provides for Docs and Gmail.

## Key Constraints

| Constraint | Rule |
| --- | --- |
| Reviews | Public **Play Store** review exports only — no scraping behind store logins or ToS-violating automation; **App Store out of scope for now** |
| Themes | Maximum **5** themes for clustering; the written pulse highlights the **top 3** |
| Length | Keep the note scannable and **≤250 words** where applicable |
| Privacy | No PII — no usernames, emails, device IDs, or other identifiable reviewer data in any artifact (quotes should be anonymous / stripped as needed) |

## Success Criteria (Summary)

- [ ] Play Store reviews imported for ~8–12 weeks from public sources (App Store deferred)
- [ ] ≤5 themes clustered; pulse shows top 3
- [ ] One-page note with 3 themes, 3 quotes, 3 actions (≤250 words)
- [ ] Pulse published to Google Docs via MCP
- [ ] Draft email created in Gmail via MCP
- [ ] No PII in any delivered artifact
