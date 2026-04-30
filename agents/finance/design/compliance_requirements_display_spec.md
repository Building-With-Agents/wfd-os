# Feature Spec — Compliance Requirements Display (Full Feature)

**Audience:** Claude Code (implementation)
**Spec owner:** Ritu Bahl
**Target location:** Cockpit-side feature; placement TBD by Claude Code based on existing IA (recommended fallback: sub-section of Audit Readiness tab)
**Branch:** `feature/finance-cockpit` (cockpit feature) — with one engine-side migration on `feature/compliance-engine-extract` (documented in dedicated section below)
**Status:** Draft for implementation
**Date:** April 30, 2026

---

## Spec file placement

Place this spec at `agents/finance/design/compliance_requirements_display_spec.md`, following the precedent set by `personnel_contractors_view_spec.md` and `monitoring_view_spec.md`.

---

## Purpose

Make the Compliance Requirements Agent's output usable in the cockpit. The agent (engine-side, shipped separately) generates and stores comprehensive structured documentation requirements for K8341 grounded in 2 CFR 200. This feature surfaces that output in the cockpit and adds the workflow Krista needs to work against it: ask questions when requirements are ambiguous, mark documentation status as the hunt produces results.

The feature has three connected parts:

- **Mode A display:** read-only rendering of the current `ComplianceRequirementsSet` with filtering, search, and per-requirement detail
- **Mode B Q&A:** interactive panel where users ask the agent specific compliance questions and see structured responses
- **Documentation status workflow:** Krista marks status against each requirement as she hunts, with audit trail

This is the "convenience layer" that turns the agent's structured output into a working tool.

---

## Why this matters

The Compliance Requirements Agent produces a comprehensive checklist. Without a cockpit display:

- The output sits as JSON in the engine's database
- Krista hunts against a list she has to read in raw form
- Mode B queries require curl commands or a separate API client
- Documentation status (what's found, what's missing) lives in a separate spreadsheet or in someone's head
- The work product of the hunt — what was located, where it lives, what's confirmed missing — has no structured home

With this feature:

- The requirements are readable and filterable in the cockpit
- Q&A is a panel away
- Status is captured per requirement, with audit trail
- The cockpit becomes the working artifact for the hunt, not a parallel artifact to it

For Phouang's review specifically, this lets you walk into the counsel meeting with the cockpit open, showing exactly which requirements have documentation, which are gaps, and which are under counsel review. That's a stronger position than "I have a Word doc somewhere."

---

## Multi-session consideration

This spec covers a substantial scope. Realistic assessment: implementation may span two Claude Code sessions rather than one, with this natural split:

- **Session 1:** Mode A display (read-only requirements view) + Mode B Q&A panel
- **Session 2:** Documentation status workflow (engine-side migration, status mutation endpoints, status UI)

If Claude Code can ship the full feature in one session reliably, that's fine. If it determines mid-implementation that splitting is wiser, that's also fine — pause at a clean boundary, commit what's done, resume next session. The acceptance criteria below distinguish "session 1 acceptance" from "full feature acceptance" so partial completion is recoverable.

---

## Mode A display

### Purpose

Show the current `ComplianceRequirementsSet` in a way that supports the hunt: organized, filterable, drill-down per requirement.

### Data source

The engine's `GET /compliance/requirements/current?grant_id=<K8341>` endpoint returns the current set. Cockpit fetches at view load and on explicit refresh.

For v1, the cockpit caches the response in component state on mount and refetches on user-initiated refresh. No background polling. v1.1 may add subscription to set-regeneration events.

### Layout

**Top of section — summary cards:**

Five summary stat cards:
- **Total requirements:** count across all compliance areas
- **Compliance areas covered:** count of distinct compliance_area values in the set
- **Verbatim citations:** count of requirements citing sections marked verbatim in the corpus (highest confidence)
- **Structured-paraphrase citations:** count citing structured-paraphrase sections (medium confidence; counsel verification recommended)
- **Skeleton/not-citable areas:** count of compliance areas where the corpus is incomplete (e.g., OMB Compliance Supplement)

The verification-status breakdown is critical for honesty discipline. It surfaces, prominently, which parts of the agent's output are most defensible and which need counsel verification before being treated as authoritative.

**Filter bar:**

- Compliance area (multi-select): procurement_standards, full_and_open_competition, cost_reasonableness, classification_200_331, subrecipient_monitoring, conflict_of_interest, standards_of_conduct
- Severity (multi-select): material, significant, minor, procedural
- Citation verification status: verbatim, structured-paraphrase, all
- Documentation status (when status workflow ships): not_started, partially_documented, documented, not_located
- Free-text search across requirement summaries and CFA-specific application narratives

**Main view — grouped table:**

Default grouping by `compliance_area`, with each section showing:
- Section header: area label, count of requirements in this area, distribution by severity
- Data rows: one per requirement with columns:
  - Requirement summary (truncated)
  - Citation
  - Severity badge
  - Verification status indicator (color-coded: green for verbatim, yellow for structured-paraphrase, red for skeleton/not-citable)
  - Applicability (one-line summary)
  - Documentation status (when status workflow ships) — color-coded badge

Sort within each section: by severity (material → procedural), then by citation order.

**Per-requirement drill-down:**

Clicking a requirement row opens a drill panel showing:

- **Requirement detail:** summary expanded, full applicability description, severity rationale
- **Regulatory citation:** citation, regulatory text excerpt (if verbatim, displayed as quoted text; if structured-paraphrase, displayed with "verify against eCFR" caveat; if skeleton, displayed with "not yet citable" warning)
- **Documentation artifacts required:** structured list of specific documents/records that constitute compliance
- **Documentation form guidance:** how the documentation should be structured (signed by whom, dated when, retained where)
- **CFA-specific application:** the agent's narrative for how this requirement applies to CFA's situation
- **Documentation status section** (when status workflow ships): current status, evidence links, status history with audit trail, controls to update status
- **Q&A about this requirement** (when Mode B ships): a "Ask the agent about this" button that opens Mode B with the requirement pre-loaded as context

**Bottom of section — exclusions footer:**

A "What's not in this view" footer noting:
- Requirements outside the current corpus scope (e.g., Subpart F audit requirements)
- Pass-through-specific requirements (ESD framework, when populated will appear here)
- Other compliance areas under future v1.1 expansion

### Honesty discipline

- Verification status (verbatim/structured-paraphrase/skeleton) is surfaced everywhere — summary cards, table indicators, drill panel detail
- Structured-paraphrase requirements show "verify against eCFR before treating as authoritative" caveats prominently
- Skeleton-area requirements (when populated, e.g., OMB Compliance Supplement) are visually distinct as "not yet citable"
- Severity is clearly labeled as "agent's reasoned default; counsel may revise"
- The "current set" indicator shows generation timestamp and model used (e.g., "Generated 2026-04-30 14:23, claude-opus-4-7")

---

## Mode B Q&A

### Purpose

Interactive panel for asking the agent specific compliance questions. Acts as a 2-CFR-200-literate assistant available on demand.

### Layout

**Placement:** A right-docked or modal panel within the Compliance Requirements display. Toggle button visible from the main view; opens a panel with chat-like interface.

**Panel structure:**

- Header: "Ask the Compliance Agent"
- Conversation history: prior questions and responses in the current session, scrollable
- Input field: text input for the question, multi-line, with character count
- Submit button: disabled while a query is in flight
- Loading state: while query is processing (typical 20-40 seconds for Mode B)

**Per-question display:**

When the user submits a question:

1. Question appears in conversation history (right-aligned, user style)
2. Loading indicator (left-aligned, agent style)
3. When response arrives, replaced with:
   - Answer text (markdown rendered)
   - Regulatory citations (linked back to the requirement detail in Mode A display where applicable)
   - "Relevant existing requirements" section (links to specific requirements in the current set)
   - Caveats section (informational-not-legal-advice notice, scope limits if mentioned)
   - Out-of-scope warning (if the agent declined to answer)
   - Refusal acknowledgment (if the agent refused as legal-opinion territory)

### Conversation persistence

For v1, conversation history is per-session — closes when the panel closes. Users can clear conversation explicitly.

The engine's `compliance_qa_log` table records every Q&A exchange independently of UI session. Conversation history in the UI is for in-session continuity; the audit log is for permanent record.

### Refusal handling

When the agent refuses (legal opinion, out-of-scope), the response is structurally distinct:

- Visual indicator (different color or icon) marking it as a refusal
- The refusal text (which the agent generates structurally per the spec)
- Suggested next step ("This requires counsel review" or "This is outside the current corpus")
- For out-of-scope refusals, link to the v1.1 corpus expansion plan (skeleton areas, future additions)

### Citation linking

When a Mode B response cites a requirement that exists in the current set, the citation is linked. Clicking the citation opens that requirement's drill panel in Mode A. This creates the natural workflow: ask a question → get an answer with citations → click into the relevant requirement detail → see documentation status and update if needed.

### Honesty constraints (UI level)

- Every Mode B response shows the model used and timestamp
- Caveats are visible, not hidden in expandable sections
- Refusals are structurally distinct from substantive answers
- The "verify against eCFR" caveat applies to structured-paraphrase citations within Mode B answers, just as in Mode A display

---

## Documentation status workflow

### Purpose

Capture, per requirement, whether CFA has the corresponding documentation. Track state changes with audit trail. Surface gaps prominently.

### Engine-side changes (this is the part that requires `feature/compliance-engine-extract`)

A new table `compliance_documentation_status` with the following structure:

- `status_id` (UUID PK)
- `requirement_id` (FK to `compliance_requirement_rows`)
- `applicable_target_type` (enum) — `grant_wide` | `contract` | `person` | `other`
- `applicable_target_id` (string, optional) — the specific contract_id, person_id, or other identifier the requirement applies to; null for grant_wide
- `status` (enum) — `not_started` | `partially_documented` | `documented` | `not_located` | `not_applicable_after_review`
- `evidence_links` (array of strings) — URLs or paths to documentation artifacts
- `gap_description` (text, optional) — for partial or not_located status, narrative of what's missing
- `notes` (text, optional)
- `updated_by` (string)
- `updated_at` (datetime)
- `created_at` (datetime)

Plus a `compliance_documentation_status_history` table for the audit trail:

- `history_id` (UUID PK)
- `status_id` (FK)
- `previous_status` (enum)
- `new_status` (enum)
- `previous_evidence_links` (array)
- `new_evidence_links` (array)
- `previous_gap_description` (text)
- `new_gap_description` (text)
- `changed_by` (string)
- `changed_at` (datetime)
- `change_summary` (text, optional) — short narrative describing the change

Engine-side endpoints:

- `GET /compliance/documentation-status?grant_id=...` — returns all status entries for a grant
- `POST /compliance/documentation-status` — creates a new status entry
- `PUT /compliance/documentation-status/{status_id}` — updates an existing entry; old values copied to history table
- `GET /compliance/documentation-status/{status_id}/history` — returns history for one status

Migration: `<new>_add_compliance_documentation_status_tables.py` on `feature/compliance-engine-extract`.

### Set-regeneration handling (engine-side)

When a new `ComplianceRequirementsSet` is generated, status entries from the prior set must be reconciled. The engine logic:

1. For each requirement in the new set, attempt to match against requirements in the prior set by `requirement_id` (note: regenerated sets may produce different requirement_ids; the matching is by the set of fields that identify a "same" requirement: compliance_area + regulatory_citation + applicability)
2. Where a match exists, copy the status entry from prior to new
3. Where no match exists in the new set, mark the prior status entry as `orphaned` (status preserved, but no longer linked to a current requirement)
4. Where new requirements have no prior match, create status entries with `status = not_started`

This re-mapping logic should be a separate service function called by the Mode A generation pipeline, not embedded in the cockpit.

### Cockpit-side rendering

In Mode A's per-requirement drill panel:

- **Documentation status section:**
  - Current status with color-coded indicator
  - Evidence links (clickable to source documentation in SharePoint/Drive/etc.)
  - Gap description (if applicable)
  - Last updated by and when
  - Status history (collapsible) showing all previous states

- **Update controls** (visible to authenticated users; for v1, no auth distinction so visible to all):
  - Status dropdown
  - Evidence links input (add/remove URLs)
  - Gap description text area
  - Notes text area
  - "Update status" button

When status is updated:
- Cockpit calls the engine's PUT endpoint
- Optimistic UI update (status badge changes immediately)
- Audit trail entry created server-side
- On server response, refresh the displayed history

### Per-(requirement, target) status entries

A complication worth being explicit about: many requirements apply to multiple targets. "For each contract above $250K, document cost or price analysis" produces one requirement, but if K8341 has three contracts above $250K, there are three documentation statuses to track.

The schema accommodates this via `applicable_target_type` and `applicable_target_id`. The UI must:

- For requirements that apply to multiple targets: show one status row per target, with target identification (e.g., "AI Engage", "Pete Vargo", "Kelly Vargo")
- For grant-wide requirements: show a single status row with `applicable_target_type = grant_wide`
- Allow Krista to add status entries per target as the hunt progresses

This is structurally important. Don't oversimplify by tracking just one status per requirement — that loses the per-target granularity Krista actually needs.

### Status states semantic clarity

- `not_started`: no one has hunted for this yet (initial state)
- `partially_documented`: some evidence exists, some gaps remain (use gap_description to detail)
- `documented`: full documentation present, evidence_links populated
- `not_located`: hunted for, confirmed absent in CFA's records, gap is real
- `not_applicable_after_review`: counsel or domain expert has reviewed and determined the requirement doesn't apply to CFA's situation despite initial classification (e.g., "this requirement targets contracts above $250K; on review, no CFA contracts cross that threshold")

The states are designed to be unambiguous in audit context. "Documented" means the auditor would find evidence; "not_located" means CFA looked and confirmed absence; "not_applicable_after_review" requires explicit determination, not just default exclusion.

### Filter and search by status

The Mode A display's filter bar includes documentation status. Critical filtered views:

- "All `not_located`" — the documented gaps Krista needs to address or escalate
- "All `not_started`" — the requirements not yet hunted for, prioritized work for Krista
- "All `partially_documented`" — partial findings that need completion or counsel review
- "All `material` severity with status not `documented`" — the highest-priority gaps

These filtered views are the operational center of the hunt. Make them easy to access (saved filter chips, perhaps).

---

## Acceptance criteria

### Session 1 acceptance (Mode A + Mode B, no documentation status)

The session 1 implementation is complete when:

1. The Compliance Requirements section appears in the cockpit (placement per Claude Code's IA recommendation)
2. The current `ComplianceRequirementsSet` is fetched from the engine and displayed
3. Five summary stat cards render with accurate counts and verification status breakdown
4. Filter bar functions for compliance area, severity, citation verification status, free-text search
5. Grouped table renders with area-grouped sections, sorted within each section
6. Per-requirement drill-down shows full requirement detail with proper verification-status indicators
7. Mode B Q&A panel functions: input → API call → response display with citations, caveats, and refusal handling
8. Mode B citations link to relevant requirements in Mode A display
9. Both the static HTML mockup and React surface render the section
10. Verification status indicators (verbatim/structured-paraphrase/skeleton) are visible at every level
11. No silent defaults; missing fields shown explicitly as missing

### Full feature acceptance (adds documentation status)

After session 2 (or end of session 1 if shipped together), additionally:

12. Engine-side migration creates `compliance_documentation_status` and `compliance_documentation_status_history` tables
13. Engine-side endpoints (GET, POST, PUT, GET history) function correctly
14. Set-regeneration handling re-maps status entries from prior to new sets correctly, marking orphans
15. Mode A per-requirement drill panel shows documentation status section with current status, evidence links, gap description, history
16. Status update controls work: dropdown for status, evidence links input, gap description, notes
17. Updates create audit trail entries server-side
18. Filter bar's documentation status filter works
19. Filtered views (all not_located, all not_started, all partially_documented, all material with non-documented status) function
20. Per-(requirement, target) status entries render correctly for requirements applying to multiple targets

---

## Out of scope

### Out of scope for v1

- Document content ingestion (evidence_links are URLs only, not embedded content)
- Automated documentation hunting (the cockpit doesn't search SharePoint or Drive for evidence; Krista enters links manually)
- Conversation persistence across sessions in Mode B (session-only for v1)
- Authentication-aware display of internal-only fields (defer to v1.3.0+)
- Multi-tenant operation (K8341-specific)
- Email notifications when status changes
- Bulk status updates (one at a time for v1)
- Custom requirement creation by users (only agent-generated requirements; Krista can't add new requirements manually)

### Deferred to v1.1+

Captured here so the ideas don't get lost:

**1. Direct chat-with-broad-chat integration:** Currently the Mode B Q&A panel is separate from the existing finance assistant chat (BroadChat). v1.1 may consolidate via routing logic that detects compliance questions and routes to Mode B versus general queries.

**2. Conversation persistence and threading:** Mode B currently treats each session as ephemeral. v1.1 should persist conversations with named threads.

**3. Tool use within Mode B:** Mode B currently produces text-only responses. v1.1 may extend to allow the agent to query CFA's actual contract or personnel data when answering, providing context-aware responses.

**4. Email or notification on status changes:** When a documentation status changes (e.g., gap surfaced), v1.1 may notify designated stakeholders.

**5. Bulk operations on status:** Mass-update many requirements at once (e.g., "mark all requirements pending counsel review as `awaiting_counsel`"). v1.1.

**6. Status workflow with assignments:** Assign specific requirements to specific people for hunting. v1.1.

**7. Direct integration with SharePoint:** When evidence_links are SharePoint URLs, render preview cards inline. v1.1+, depends on v1.3.0 SharePoint connector.

**8. Custom severity overrides:** Counsel may want to revise the agent's severity assessment. v1.1.

**9. Status comments and discussion:** Allow comments on status entries for collaborative review. v1.1.

**10. Versioned audit trail of evidence_links:** Currently the history captures changes to evidence_links as before/after; v1.1 may want to track each link with its own metadata (added_by, verified_by, last_checked_date).

**11. Role-based field visibility:** When auth lands in v1.3.0, sensitive fields (counsel notes, internal posture) hidden from non-privileged users.

**12. Cross-grant status comparison:** When the cockpit serves multiple grants, comparing status across grants surfaces patterns. v1.2+.

---

## Forward seams

This feature integrates with several upcoming or existing features:

- **Compliance Requirements Agent (engine, shipping now):** This feature consumes its output. When the agent's Mode A regenerates a set, this feature's set-regeneration handling kicks in.
- **Monitoring v1 (cockpit, upcoming):** The Monitoring tab will reference compliance requirements — for the procurement engagement, "these are the requirements being examined." Monitoring engagements display the relevant subset of requirements.
- **Monitoring Agent (engine, future):** Will read documentation status entries to evaluate engagement readiness.
- **Audit Readiness — Procurement and Subrecipient dimensions (v1.3.4, v1.3.1):** Will read documentation status to compute readiness scores.
- **Personnel feature:** Per-person status entries may reference Person records when requirements apply to specific personnel.
- **Future Contracts inventory feature:** Per-contract status entries may reference Contract records when requirements apply to specific contracts.

---

## Implementation order

### Engine-side prerequisites

Before cockpit work begins, the engine must have:

1. The Compliance Requirements Agent shipped and operational (currently being implemented in parallel)
2. For session 2, the documentation status tables and endpoints (this spec's engine-side migration)

### Session 1 implementation

1. Read existing pipeline and the personnel + monitoring features' structure to understand conventions
2. Save this spec at `agents/finance/design/compliance_requirements_display_spec.md`
3. Recommend section placement based on existing IA — sub-section of Audit Readiness, sub-section of Monitoring (when that ships), or new top-level Compliance tab. Document the choice.
4. Define the data model in TypeScript types (mirror the engine's Pydantic schemas: `ComplianceRequirementsSet`, `Requirement`, Q&A response types)
5. Implement the engine API client (fetching from `/compliance/requirements/current`, `/compliance/requirements/qa`)
6. Build Mode A display: summary cards, filter bar, grouped table, per-requirement drill panel
7. Build Mode B Q&A panel: input, conversation history, response rendering with citations and caveats
8. Wire the section into the chosen placement
9. Commit session 1 work

### Session 2 implementation (documentation status)

10. Engine-side: implement the documentation status tables migration on `feature/compliance-engine-extract`
11. Engine-side: implement endpoints (GET, POST, PUT, history)
12. Engine-side: implement set-regeneration re-mapping logic
13. Cockpit-side: extend types to include documentation status
14. Cockpit-side: extend Mode A drill panel with status section and update controls
15. Cockpit-side: extend filter bar with documentation status filter
16. Cockpit-side: implement per-(requirement, target) rendering for multi-target requirements
17. Verify acceptance criteria 12-20
18. Commit session 2 work

### Session boundary considerations

If Claude Code shipping the full feature in one session is feasible, the boundary between session 1 and session 2 is logical, not chronological. Implement straight through.

If multi-session is required, the boundary at the end of session 1 (before documentation status) is clean: Mode A and Mode B are usable as a read-only display + interactive Q&A; status workflow follows. The cockpit ships partial functionality after session 1 and adds the rest in session 2.

---

## Worktree state notes

Before beginning, confirm worktree state:

- Personnel feature commit and chat-spec step 4 BroadChat commit must both be landed before this work begins
- Monitoring v1 may or may not be shipped — this feature can ship before, after, or in parallel with Monitoring v1 (no hard dependency)
- The Compliance Requirements Agent must be shipped before this feature can do anything useful (Mode A display has no data without the agent's output)

---

## Open questions for Ritu (before implementation)

1. Confirm placement decision is delegated to Claude Code's IA review (default fallback: sub-section of Audit Readiness)
2. Confirm session 1 + session 2 split is acceptable if scope demands; alternatively, confirm the spec author's authority to ship in one session if Claude Code judges it feasible
3. Confirm the four-state documentation status enum (not_started, partially_documented, documented, not_located) plus the fifth (not_applicable_after_review) — is this the right granularity?
4. Confirm Mode B operates as a separate panel from BroadChat for v1 (no chat consolidation)
5. Confirm authentication is deferred to v1.3.0 (so all users see all fields and can update all status entries in v1)

These should be resolved before implementation begins. Some can be answered by Claude Code making reasonable defaults if Ritu's response isn't immediate.
