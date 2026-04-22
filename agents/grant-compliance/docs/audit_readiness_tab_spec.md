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

3. **Frontend tab scaffolding.** Add the Audit Readiness tab to the Finance Cockpit navigation. Lay out the 4 cards, verdict box, decisions section, sub-tab container.

4. **Cards data wiring.** Connect each card to its data source.

5. **Sub-tabs one at a time.** Build in this order: Compliance Flags (highest value, uses most existing endpoints), PBC Tracker, Firms, Documents, Time & Effort, Findings & Gaps, Reports.

6. **AI assistant integration.** Extend the existing assistant to know about the new tab context and route queries appropriately.

7. **Verdict generation.** Add LLM call for the editorial verdict paragraph.

Each step should stop and report before continuing to the next.

---

## What this gets you

A working Audit Readiness tab that:

- Shows live compliance posture from the engine
- Tracks PBC items grounded in actual regulation
- Manages firm engagement state
- Surfaces gaps and decisions that need action
- Lets Krista explain any flag in plain language with CFR citation
- Mirrors the editorial design you already have

Not a static checklist. An operational tool that makes compliance a daily thing and audit readiness a byproduct.

---

## Version history

- **v1 — 2026-04-23 — Initial spec.** Drafted by Ritu with Claude (claude.ai). Based on compliance engine API surface documented in `integration_notes.md`. Pre-wfdos-common-refactor state. Three open questions explicitly deferred (see top of document).
