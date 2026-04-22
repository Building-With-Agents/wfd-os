# Audit Readiness Tab — Design Spec

## Purpose

A live operational view of CFA's Single Audit posture. Answers one question at all times: **"Are we audit-ready right now, and if not, what's wrong?"**

The tab is the UI surface of the grant-compliance engine. Everything shown is backed by real data from the compliance module's API. No static checklists. No placeholders.

---

## Open questions to resolve before full build

These are known gaps or unverified assumptions, deliberately deferred from v1 of the spec. Each should be resolved before the corresponding section is considered production-ready.

1. **SF-425 report generator's budget category mapping.** The existing `POST /reports` endpoint generates SF-425 or foundation narrative drafts. Unverified whether the budget categories it uses map to K8341 Amendment 1's six categories (GJC Contractors, CFA Contractors, Personnel Salaries, Personnel Benefits, Other Direct Costs, Indirect Costs). If the mapping is generic or hardcoded to a different structure, the Reports sub-tab either needs a pre-build adaptation or needs to defer SF-425 specifics.

2. **QB sync transaction type scope.** Current sync pulls Bill, Purchase, and JournalEntry only. Deposits, Credit Memos, Transfers, Vendor Credits, and Refund Receipts are NOT synced. For K8341, the main concerns are: how was the Riipen $82,303 refund booked? How was NCESD contract termination recorded? If booked as Deposit or Credit Memo, the compliance engine won't see the offsetting entry and expenditure totals may be overstated. Verify with Krista before the engine is used for audit-quality totals.

3. **Pre-wfdos-common-refactor state.** The compliance engine currently uses hand-rolled primitives for API auth, OAuth token encryption, OAuth CSRF state, token refresh, and schema migration safety. These are all documented as POC limitations in `integration_notes.md` and are expected to be replaced when Gary's `wfdos-common` refactor is merged. The Audit Readiness tab is built against the engine's interfaces, which are expected to remain stable. Any tab behavior that depends on infrastructure maturity (e.g., real authentication, multi-tenancy) is explicitly out of scope for v1.

4. **Finance Cockpit UI location.** The spec assumes the Audit Readiness tab will be added to an existing Finance Cockpit UI. The location of that UI in the codebase is not yet confirmed on this branch — see separate UI location diagnostic. Implementation order step 3 is blocked until this is resolved.

---

## Design language

Matches the existing Finance Cockpit. Editorial voice ("Are we okay?" style headline), 4 summary cards at the top, a verdict box, a "This week's decisions" section, sub-tabs below. Typography, spacing, and color consistent with the Budget & Burn tab.

---

## Headline

**"Are we audit-ready?"**

Subhead: *A live view of grant compliance posture, document readiness, and audit engagement.*

Status line at top: *"STATUS AS OF [timestamp] · FY24-25 audit [X] days overdue · FY25-26 audit [X] days remaining"*

---

## 4 summary cards (mirrors Budget & Burn structure)

### Card 1 — COMPLIANCE FLAGS

**Primary number:** Count of open (unresolved) flags

**Sub-line:** *"[N] new this week · [N] awaiting review · [N] blocker-severity"*

**Status pill:**
- 0 open blockers = `ON TRACK` (green)
- 1-3 open blockers = `ACTION NEEDED` (amber)
- 4+ open blockers = `CRITICAL` (red)

**Data source:** `GET /compliance/flags?status=open`

### Card 2 — DOCUMENTATION COVERAGE

**Primary number:** `[X] / [Y] PBC items ready`

**Sub-line:** *"[X] gathering · [Y] missing · [Z] in SharePoint Audit folder"*

**Status pill:**
- >85% ready = `ON TRACK`
- 60-85% = `GATHERING`
- <60% = `GAPS`

**Data source:** PBC tracker (new table — see below) cross-referenced with SharePoint inventory CSV.

### Card 3 — ENGAGEMENT STATUS

**Primary text:** Firm name or `EVALUATING`

**Sub-line:** *"Engagement letter [status] · fieldwork target [date or TBD]"*

**Status pill:**
- Engaged with signed letter = `ENGAGED`
- Quoting / in discussion = `EVALUATING`
- Nothing active = `NOT STARTED` (red)

**Data source:** Firm engagement table (new — see below).

### Card 4 — TIME & EFFORT

**Primary number:** `[X] / [Y] certifications complete`

**Sub-line:** *"Current period: [month]. [N] employees, [N] certified, [N] pending"*

**Status pill:**
- All current-period certifications signed = `CURRENT`
- 1-2 pending = `PENDING SIGNATURES`
- 3+ pending or prior period incomplete = `OVERDUE`

**Data source:** `GET /time-effort/certifications`

---

## Verdict box

Editorial paragraph matching the Budget & Burn style. Generated from current data:

**Template:**
> *[One-sentence headline — e.g., "FY24-25 Single Audit is [X] days overdue; engagement with [firm] [status]."]*
>
> *[Body: 2-4 sentences on current state — what's solid, what's at risk, what decision is needed this week. References specific numbers from the cards.]*
>
> *[Optional closing line on the "lever" — the one action that most moves the needle.]*

Example rendered:

> *"FY24-25 Single Audit is 112 days overdue; engagement with Clark Nuber in evaluation.*
>
> *Compliance engine has scanned 2,103 transactions and raised 18 flags; 14 are resolved, 4 remain open including one blocker-severity item on the Ada $65k Q4 invoice. Documentation coverage is at 67% with board minutes and prior-year audit materials still missing. Time and effort certifications are current.*
>
> *The lever this week: Clark Nuber engagement letter needs a decision — if not them, activate Peterson Sullivan or Jacobson Lawrence by April 30."*

Verdict is generated by the compliance engine's LLM (single call to `/audit-summary` or composed client-side from the other GETs).

---

## "This week's audit decisions"

Same list pattern as Budget & Burn's "This week's decisions." Items sourced from:

- Open blocker-severity compliance flags
- Overdue PBC items with owner
- Pending firm engagement decisions
- Incomplete time and effort certifications for closed periods
- Documentation gaps with named owner

Each item has: description, owner, priority (HIGH/MEDIUM/LOW), status (open/in-progress/blocked). Click to drill down.

Example items:

- *FY24-25 engagement — Decide Clark Nuber vs. alternatives by April 30* (Owner: Ritu, HIGH)
- *Locate FY24 board meeting minutes — ask Victor Bahl* (Owner: Krista, HIGH)
- *Ada Q4 $65k invoice — unresolved compliance flag, need justification* (Owner: Krista, BLOCKER)
- *SEFA draft — compile from K8341 expenditures* (Owner: Krista, MEDIUM)

---

## Sub-tabs

Same tab pattern as Budget & Burn. Below the summary cards and verdict, numbered sub-tabs for deeper views.

### Sub-tab 1 — Compliance Flags (default view)

Table of all flags with filters for status, severity, rule category, date range. Columns: flag ID, rule citation (e.g., "§200.438"), message, severity, status, raised date, resolved info.

**Drill-down behavior:** Click any flag → detail view shows rule text, source transaction, status history, and a button: *"Generate plain-language explanation"*. Clicking the button calls `/compliance/flags/{id}/explain`, which makes the LLM call and writes to the audit log. Result is cached; subsequent views show the cached explanation instantly. A small "regenerate" option is available if the cached explanation is outdated. Every regeneration is a new audit log entry.

Rationale: each LLM-generated explanation is an auditable artifact. Making generation an explicit action keeps the audit log meaningful and prevents unintentional LLM cost.

The flag detail view also includes:
- Full rule text and CFR citation (live link to ecfr.gov)
- Source transaction detail (`GET /transactions/{id}`)
- Proposed resolution options (resolve / waive / acknowledge)
- Full audit log of all actions on this flag

Bulk actions: scan all unscanned transactions (`POST /compliance/scan`), resolve multiple flags.

### Sub-tab 2 — PBC Tracker

Comprehensive list of documents the auditor will request, generated from 2 CFR 200 + OMB Compliance Supplement for Good Jobs Challenge.

Columns: item, category (Financial / Compliance / Governance), regulatory basis, status (Not Started / Gathering / Ready / Sent), location (SharePoint link if available), owner, target date, notes.

Each item links back to its regulatory basis (CFR section or Compliance Supplement reference). Each "Ready" item links to the actual file(s) in SharePoint.

Filter: by audit year (FY24-25 / FY25-26), by status, by category, by owner.

**Drill-down:** Click any item → detail panel with regulatory basis, current evidence, history of status changes, ability to attach new evidence (link to SharePoint file).

**Data source:** PBC tracker table (new — see schema section below).

### Sub-tab 3 — Firms & Engagement

Table of firms contacted with status. Columns: firm name, primary contact, first contact date, quote amount, GAGAS/Yellow Book qualified (yes/no/unknown), scope offered (financial only / Single Audit), status (contacted / quoting / negotiating / engaged / declined / passed), notes.

Highlights which firm is the current front-runner and why.

**Drill-down:** Click any firm → full engagement history, correspondence timeline, quote details, decision rationale.

**Data source:** Firm engagement table (new — see schema section).

### Sub-tab 4 — Time & Effort

Table of certifications by employee and period. Columns: employee, period (year-month), grants covered, draft status, signed status, certifier, signature date, audit log.

Uses existing endpoints: `GET /time-effort/certifications`, `POST /time-effort/draft`, `POST /time-effort/certifications/{id}/certify`.

### Sub-tab 5 — Documents (SharePoint inventory)

Table of audit-relevant files from the SharePoint inventory. Columns: channel (Finance/General/HR), path, filename, audit category, relevance score, audit scope (FY24-25/FY25-26), last modified.

Filters: by channel, by category, by score, by fiscal year.

**Data source:** `scripts/audit_relevance_scored.csv` (static for POC; eventually replaced by live SharePoint sync).

### Sub-tab 6 — Findings & Gaps

What's missing. Each gap has: description, regulatory basis (why it matters), owner, target resolution date, status.

Seeded from:
- PBC items marked "Not Started" or "Missing"
- Known gaps from the relevance scoring pass (board minutes, prior audit reports)
- Any compliance category showing zero coverage in the rules engine

**Drill-down:** Click any gap → resolution plan, history, current status.

### Sub-tab 7 — Reports

Uses existing `/reports` endpoints. Table of draft and finalized reports (SF-425, narrative). Status, period, generated date, finalized date, finalizer.

Blocker check: displays prominently if `POST /reports` returns 409 due to open flags.

See open question 1 above regarding the SF-425 generator's budget category mapping for K8341.

---

## AI Assistant panel (right side)

Consistent with the existing Finance Cockpit assistant design.

**Header:** "Audit Assistant"
**Context:** "AUDIT READINESS TAB"

**Try asking** (6 suggested prompts):

1. *"What's blocking our FY24-25 audit right now?"*
2. *"Explain this compliance flag"* (contextual when a flag is selected)
3. *"What does 2 CFR §[X] require?"*
4. *"Draft a response to the auditor about [topic]"*
5. *"What PBC items are still missing?"*
6. *"Compare the firms we've contacted"*

**Assistant behavior:**

- For questions about specific flags → route to `GET /compliance/flags/{id}/explain` (with caching per sub-tab 1 design)
- For regulation questions → pull from the structured `CostRule` data and the live CFR text via eCFR.gov link
- For status questions → compose from the dashboard endpoints
- For correspondence drafting → LLM generation grounded in the current state (firm name, flag details, etc.)
- For comparison questions → pull from the firm engagement table

**Critical design rule:** The assistant must never answer a regulation question without citing the specific CFR section. Never answer a compliance status question without linking to the source flag/transaction. No ungrounded answers.

---

## User personas

Primary user: **finance operator** (for CFA specifically: Krista). Uses the tab for daily compliance triage, flag resolution, PBC gathering, certification chasing.

Secondary user: **executive director** (for CFA specifically: Ritu). Uses the tab for status oversight, firm engagement decisions, audit correspondence, board reporting.

Tertiary (future): **auditor** with scoped read-only access. Not in scope for v1.

---

## New data model additions

Two new tables in the `grant_compliance` schema:

### `pbc_items`

```
id (pk)
audit_scope (enum: FY24-25, FY25-26, both)
category (enum: financial, compliance, governance, program_specific)
title (text)
regulatory_basis (text) -- e.g., "§200.332(b)"
description (text)
status (enum: not_started, gathering, ready, sent)
owner (text)
target_date (date)
evidence_url (text, nullable) -- SharePoint file link
notes (text)
created_at, updated_at
```

Seeded from a YAML file at `agents/grant-compliance/data/pbc_template.yaml` generated from 2 CFR 200 + the Good Jobs Challenge Compliance Supplement.

### `firm_engagements`

```
id (pk)
firm_name (text)
primary_contact_name (text)
primary_contact_email (text)
first_contact_date (date)
most_recent_interaction (date)
quote_amount_cents (bigint, nullable)
gagas_qualified (enum: yes, no, unknown)
scope_offered (enum: financial_only, single_audit, unclear)
status (enum: contacted, quoting, negotiating, engaged, declined, passed)
notes (text)
created_at, updated_at
```

Seeded with the known firms: Jacobson Lawrence (JJCO), Clark Nuber.

---

## API additions needed

For endpoints that don't exist yet:

- `GET /pbc-items` — list with filters
- `POST /pbc-items` — create
- `POST /pbc-items/{id}/update-status`
- `GET /firm-engagements`
- `POST /firm-engagements`
- `POST /firm-engagements/{id}/update`
- `GET /audit-summary` — single-call composite for the 4 cards (optional — can compose client-side for POC)

All follow the existing pattern (route groups, request/response shapes, human-in-the-loop for writes).

---

## POC-specific handling

Because the compliance engine is currently POC and Gary's `wfdos-common` refactor hasn't landed:

- No authentication on the tab — it's localhost-only just like the rest of the Finance Cockpit POC
- "Last scan" shown as manual timestamp, with a prominent "Scan Now" button instead of pretending there's a scheduler
- Any operation that would require token refresh (QB sync) shows a "may require re-auth" warning
- The `integration_notes.md` file is linked from a small "i" icon in the tab header

When Gary's refactor lands and these are addressed, remove the POC handling. That's a single commit.

---

## Out of scope for POC

Explicitly not building in this first pass:

- SEFA generation (auditor's deliverable, not yours)
- Federal Audit Clearinghouse submission
- Bulk document redaction for sharing with auditor
- Rule editor (rules are code-managed until review process is in place)
- Multi-tenant isolation (handled by wfdos-common refactor)
- Email monitoring for auditor correspondence
- Auto-matching SharePoint files to PBC items (manual linking for POC)

---

## Implementation order (for Claude Code)

1. **Backend first.** Add the two new tables (`pbc_items`, `firm_engagements`) via Alembic migration. Add the new API routes. Seed the PBC template YAML with initial items from 2 CFR 200 + Good Jobs Challenge requirements. Seed firm engagements with Jacobson Lawrence and Clark Nuber.

2. **Audit summary composite.** Either add a single `/audit-summary` endpoint or compose client-side — whichever is simpler given existing cockpit patterns.

3. **Frontend tab scaffolding.** BLOCKED until Finance Cockpit UI location is confirmed (see open question 4). Once resolved: add the Audit Readiness tab to the Finance Cockpit navigation. Lay out the 4 cards, verdict box, decisions section, sub-tab container.

4. **Cards data wiring.** Connect each card to its data source.

5. **Sub-tabs one at a time.** Build in this order: Compliance Flags (highest value, uses most existing endpoints), PBC Tracker, Firms, Documents, Time & Effort, Findings & Gaps, Reports.

6. **AI assistant integration.** Extend the existing assistant (currently at `agents/assistant/` on `development`, not inside `agents/grant-compliance/`) to know about the new tab context and route queries appropriately. This requires cross-module coordination — approach TBD.

7. **Verdict generation.** Add LLM call for the editorial verdict paragraph.

Each step should stop and report before continuing to the next.

---

## What this gets you

A working Audit Readiness tab that:

- Shows live compliance posture from the engine
- Tracks PBC items grounded in actual regulation
- Manages firm engagement state
- Surfaces gaps and decisions that need action
- Lets the finance operator explain any flag in plain language with CFR citation
- Mirrors the editorial design of the existing Finance Cockpit

Not a static checklist. An operational tool that makes compliance a daily thing and audit readiness a byproduct.

---

## Version history

- **v1 — 2026-04-23 — Initial spec.** Drafted by Ritu with Claude (claude.ai). Based on compliance engine API surface documented in `integration_notes.md`. Pre-wfdos-common-refactor state. Four open questions explicitly deferred (see top of document): SF-425 budget category mapping, QB sync scope for refunds/credits, wfdos-common infrastructure dependencies, Finance Cockpit UI location.
