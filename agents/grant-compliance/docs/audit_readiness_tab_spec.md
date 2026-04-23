# Audit Readiness Tab — Design Spec (v1.2)

## What changed from v1

v1 of this spec was drafted before the existing implementation was discovered. It proposed a 7-sub-tab structure with separate views for PBC Tracker, Firms & Engagement, Documents, Findings & Gaps, Reports, and Time & Effort.

The discovered reality is better than the proposal. On `feature/finance-cockpit` there is already a complete UI with:
- Verdict box with tone-aware styling
- Three stat cards (Overall Readiness, Documentation Gap, T&E Certifications)
- Audit Dimensions table (six dimensions, "What auditors look for" column, readiness %, owner)
- Drillable dimension rows backed by a working drill-panel system
- Recent Activity feed (placeholder)

The dimensions approach is architecturally superior to the sub-tab approach because it aligns with how Single Audit firms actually structure their testing — by compliance area with named owners, not by document type.

v1.2 preserves the existing UI entirely. The work is all backend: replace hardcoded values with computed values, and fill in the "Open gaps" placeholder in drill panels with real gap lists.

v1 is preserved in git history for anyone who wants to see the evolution.

---

## Purpose

A live operational view of CFA's Single Audit posture. Answers one question at all times: **"Are we audit-ready right now, and if not, what's wrong?"**

Everything shown must be backed by real data from the compliance engine, cockpit backend, and supporting sources. No hardcoded percentages. No sample numbers dressed as live data.

---

## Current state (2026-04-23)

The tab at `/internal/finance` → "Audit Readiness" is a visual mock. All values come from hardcoded Python literals in `_tab_audit` at `agents/finance/cockpit_api.py:422`. The function accepts but ignores its `data` argument. `build_drills()` at `agents/finance/design/cockpit_data.py:832` generates drill panels per dimension with real "What auditors look for" copy but a placeholder "Open gaps" row ("Full gap detail pending first audit-readiness sweep"). The Recent Activity feed at `components/cockpit-shell/activity-feed.tsx` is a hardcoded `const FEED = [...]` array.

The type contract, the dispatcher, the styling, the error surfaces (`<TabError>`, `<DrillPanel>`), the drillable-row pattern, and the React components are all production-quality and working. The deficit is entirely in data sourcing.

Additionally: the six dimensions' `{id, title, owner, readiness, tone}` values are hardcoded in two places — `_tab_audit` and the `audit_dimensions` literal in `build_drills()`. They currently agree by coincidence, not by design. Any future update must touch both. This duplication must be eliminated as part of the real-data rewrite.

---

## The six audit dimensions

These stay as-is. They are well-chosen and map cleanly to 2 CFR 200 compliance areas:

1. **Allowable costs** (`allowable_costs`) — Every transaction maps to an allowable category
2. **Transaction documentation** (`transaction_documentation`) — Vendor invoices, receipts, approvals on file
3. **Time & effort certifications** (`time_effort`) — Quarterly attestations from federally-funded staff
4. **Procurement & competition** (`procurement`) — Competitive process or sole-source justification per contract
5. **Subrecipient monitoring** (`subrecipient_monitoring`) — Risk assessment, monitoring, follow-up per provider
6. **Performance reporting accuracy** (`performance_reporting`) — Reported placements reconcilable to source data

Each dimension maps to specific 2 CFR 200 sections (see mapping table below).

---

## What needs to change

### Change 1 — Replace `_tab_audit` with computed values

Function location: `agents/finance/cockpit_api.py:422`.

Current behavior: returns hardcoded Python literals for verdict, three stats, and six dimensions.

New behavior: computes values from real sources.

**Stat 1 — Overall Readiness (`stats.overall`).** Weighted average of the six dimension readiness percentages. Weights to be defined; a defensible default is equal weighting. Whatever the formula is, it must be documented and stable. Never a literal. The "Across N of 6 audit dimensions" subcopy dynamically reflects how many dimensions are computable (currently 2 of 6 in v1.2). Computed dimensions with `readiness_pct: null` (e.g., engine has no scan data yet) are excluded from the average and from the count.

**Stat 2 — Documentation Gap (`stats.doc_gap`).** Count of transactions above the de minimis threshold ($2,500) that lack linked invoice documentation. Source: compliance engine's `transactions_without_documentation(threshold_cents=250_000)` method (added in step 1.5). Populated by the QB `Attachable` sync pathway. Per the diagnostic at `scripts/transaction_documentation_linkage.md`, no linkage field exists on the current `Transaction` model; step 1.5 adds it.

**Stat 3 — T&E Certifications (`stats.te_certs`).** Ratio of completed quarterly certifications to expected certifications since grant start. Both numerator and denominator depend on Employee↔Grant assignment data which does not exist in the engine in v1.2. As with the time_effort dimension, this stat is a placeholder in v1.2: returns `null` with a status flag, displayed as "Not yet tracked" or equivalent. Becomes computable in v1.3+ when Employee↔Grant data model is added.

**Verdict.** LLM-generated based on the three stats + dimension percentages + identified top gap. Must cite the specific dimension that drives the "biggest gap" phrasing. One LLM call per tab load; cached for some interval (e.g., 5 minutes) to avoid repeated generation.

**Dimensions.** Each dimension's readiness % computed per dimension-specific rules:

| Dimension | Computation | Status in v1.2 |
|---|---|---|
| Allowable costs | 100 × (1 − distinct transactions with unresolved Subpart E flags / scanned-recently transactions). Numerator counts distinct transactions, not raw flag count, so a transaction with multiple flags counts once. Ensures percentage stays in [0, 100]. "Scanned-recently" means `last_scanned_at >= now() - scan_freshness_days` (default 7 days). | Computed |
| Transaction documentation | 100 × (1 − transactions_without_documentation / transactions_above_threshold). | Computed |
| Time & effort certifications | 100 × (completed_certifications / expected_certifications). Requires Employee↔Grant assignment data not present in current model. | Placeholder (None) |
| Procurement & competition | Requires procurement records data model not present in current engine. | Placeholder (None) |
| Subrecipient monitoring | Requires subrecipient risk assessment data model not present in current engine. | Placeholder (None) |
| Performance reporting accuracy | Requires WSAC reconciliation data model not present in current engine. | Placeholder (None) |

Four of six dimensions return `None` (placeholder) in v1.2 because the underlying data models do not exist in the compliance engine. This is intentional — showing hardcoded percentages for dimensions where we have no data is dishonest. The placeholder dimensions become future work (v1.3+) as the data models are added.

Owner assignments stay as currently hardcoded (Krista, Ritu, Bethany · Gage, etc.) until a real ownership-assignment mechanism is added.

### Three-state dimension status

The `GET /compliance/dimensions` endpoint distinguishes three states per dimension via two fields:

- `status: "computed"` + `readiness_pct: <integer>` — formula exists and produced a value. Display the percentage.
- `status: "computed"` + `readiness_pct: null` — formula exists but no data yet (e.g., scanner hasn't run, no transactions above threshold). Display "Awaiting first scan" or equivalent.
- `status: "placeholder"` + `readiness_pct: null` — no formula exists in v1.2 (deferred to v1.3+ pending data model additions). Display "Readiness measurement not yet available for this dimension."

The cockpit must distinguish all three states. Treating "computed but null" the same as "placeholder" loses the useful "you need to run a scan" signal.

### Defensive percentage clamping

All computed percentages are clamped to [0, 100] before being returned by the endpoint. This is defensive — under normal operation the formulas are bounded, but momentary inconsistencies (e.g., between scan completion and flag resolution) could produce out-of-range values that would render badly in the UI. Clamping ensures the wire payload always validates.

### Change 2 — Replace "Open gaps" placeholder in drill panels

Location: `build_drills()` in `agents/finance/design/cockpit_data.py:832`.

Current behavior: each `audit:*` drill panel has a real "What auditors look for" row and a placeholder "Open gaps" row ("Full gap detail pending first audit-readiness sweep").

New behavior: the "Open gaps" row is replaced by a list of actual open gaps for that dimension. For example, clicking "Allowable costs" opens a drill showing specific unresolved compliance flags; clicking "Subrecipient monitoring" shows which subrecipients lack current monitoring records.

Each gap entry should show: what's missing, why it matters (regulatory basis, one sentence), owner, and status. If possible, a link to the source (specific flag, specific subrecipient record, specific transaction).

### Change 3 — Replace hardcoded Recent Activity feed

Location: `components/cockpit-shell/activity-feed.tsx`.

Current behavior: `const FEED = [...]` with six hardcoded entries.

New behavior: fetch from a new `/cockpit/activity` endpoint that returns recent operational events (placements verified, QB syncs, invoices approved, compliance flags resolved, certifications signed).

The underlying data sources already exist (compliance engine audit log, cockpit backend transactions, WSAC placement imports). The work is assembling them into a unified activity stream with a consistent shape.

This change is lower priority than changes 1 and 2. It can ship independently.

### Change 4 — Eliminate duplicated dimension values

The six audit dimensions currently have their `{id, title, owner, readiness, tone}` values hardcoded in two places: `_tab_audit` at `cockpit_api.py:422` and the `audit_dimensions` literal in `build_drills()` at `cockpit_data.py:832`. Currently the values agree; synchronization is manual, not structural.

As part of the `_tab_audit` and `build_drills()` rewrite in changes 1 and 2, these should draw from a single canonical source — either a shared module or a computed result — so future updates cannot cause drift.

### Change 5 — Archive or remove the orphaned fixture

Location: `portal/student/app/internal/finance/lib/cockpit-fixture.json`.

Current state: 4,196 lines, committed to git, referenced nowhere in code. Appears to be a snapshot from an earlier prototype. Its audit drill content is richer than what `build_drills()` produces.

Options:
- **Archive:** Rename to `cockpit-fixture.reference.json.archived` and add a README note explaining it is not consumed but preserved as a reference for the richer drill content it contains.
- **Delete:** Remove entirely; git history preserves it for anyone who needs to reference.

Either approach is acceptable. Skim first to determine if its drill structure is useful as a template for v1.2 implementation before deciding.

---

## Dimension-to-regulation mapping

Each dimension traces to specific 2 CFR 200 citations. This is what the drill panels should show under "What auditors look for" and what the gap list is tested against.

| Dimension | 2 CFR 200 citation(s) | Compliance Supplement relevance |
|---|---|---|
| Allowable costs | §§200.403–200.405, 200.420–200.476 | Cost principles, unallowable costs |
| Transaction documentation | §200.302, §200.334 | Financial management, record retention |
| Time & effort certifications | §200.430(i) | Personnel compensation support |
| Procurement & competition | §§200.317–200.327 | Procurement standards |
| Subrecipient monitoring | §§200.331–200.333 | Subrecipient monitoring requirements |
| Performance reporting accuracy | §§200.328–200.329 | Performance reporting |

This mapping should be encoded as structured data in the compliance engine (similar to how `unallowable_costs.py` encodes Subpart E rules), so drill panels can cite the regulation live.

---

## Data flow

```
[Next.js UI at :3000]
    ↓ (calls via /api/finance/* rewrite)
[Cockpit backend at :8013]
    ↓ (calls via /api/grant-compliance/* rewrite)
[Compliance engine at :8000]
    ↓
[grant_compliance Postgres schema]
```

For the Audit Readiness tab:

The compliance engine computes its own dimension readiness percentages and exposes them via `GET /compliance/dimensions`. The cockpit backend orchestrates by calling this endpoint, combining with its own data sources (firms, future PBC items), and assembling the tab payload for the UI.

---

## Out of scope for v1.2

Preserved from v1. Still out of scope:

- SEFA generation
- Federal Audit Clearinghouse submission
- Bulk document redaction for sharing with auditor
- Rule editor (rules are code-managed until review process is in place)
- Multi-tenant isolation (handled by wfdos-common refactor)
- Email monitoring for auditor correspondence

Also explicitly out of scope for v1.2:

- Replacing or restructuring the existing AuditTab React component
- Adding sub-tabs below the dimensions table
- Building a separate Firms & Engagement tab (can be added later as a drill-down or separate concern)
- Building a separate PBC Tracker tab (PBC items become a data source for computing dimension readiness; they do not need a dedicated tab)

---

## Implementation order

1. **Dimension-to-regulation mapping.** Encode the table above as structured data in the compliance engine. Use the same pattern as `unallowable_costs.py`. This becomes the foundation for drill panel citations.

1.5. **Add documentation linkage to Transaction model.** Add an `attachment_count: int` column (default 0) to the compliance engine's `Transaction` table. Add a `sync_attachables(db, client)` step to the QB sync pathway that queries QB's `Attachable` entity and updates `attachment_count` for each transaction. Add an Alembic migration for the new column. Add a method `transactions_without_documentation(threshold_cents: int) -> int` to the data access layer. This step unblocks the Documentation Gap stat in step 3.

2. **Compute dimension percentages on the engine, expose via endpoint.** On `feature/compliance-engine-extract`: add `Transaction.last_scanned_at` column + migration + sync hook. Add `transactions_above_threshold_total` helper. Add computation functions for `allowable_costs` and `transaction_documentation`. Add `GET /compliance/dimensions` endpoint returning all six dimensions with computed percentages where computable, `None` where placeholder. Two-commit sequence: engine-side here, cockpit-side wiring on `feature/finance-cockpit` as a follow-up.

3. **Compute the three stat cards.** Engine-side: extend `/compliance/dimensions` response (or add a sibling `/compliance/stats` endpoint) to include the three stat values: `overall_readiness_pct` (computed from dimension percentages, equal-weighted average of computed dimensions only), `doc_gap_count` (from `transactions_without_documentation`), `te_certs_status` (placeholder in v1.2). Cockpit-side: replace the three hardcoded `StatCard` literals in `_tab_audit` with values from the engine response. Two-commit sequence: engine-side first, cockpit-side wiring as follow-up. Same pattern as step 2.

4. **Replace "Open gaps" drill content.** For each audit dimension, implement real gap-list generation in `build_drills()`.

5. **LLM-generated verdict.** Add cached verdict generation. Ensure the verdict cites the specific dimension driving the top gap.

6. **Recent Activity feed.** Add `/cockpit/activity` endpoint. Replace hardcoded feed with fetched data.

7. **Archive or remove orphaned fixture.** Based on decision in Change 5.

Each step should stop and report before continuing.

---

## Acceptance tests

For v1.2 to be considered implemented:

1. Navigate to `/internal/finance` → Audit Readiness. Verify all three stat cards, six dimension percentages, and verdict text change in response to underlying data changes (e.g., resolving a flag should nudge "Allowable costs" readiness, adding a certification should move T&E from 0/9 to 1/9).

2. Click each of the six dimensions. Verify drill panel shows: dimension name, readiness %, owner, "What auditors look for" text, relevant 2 CFR 200 citation, and a list of actual open gaps (not the placeholder).

3. Grep the codebase for any remaining hardcoded literal in `_tab_audit` or `build_drills()` for `audit:*` keys. Expected result: zero matches.

4. Recent Activity feed shows events from the last N days in chronological order, with source attribution.

5. Verdict LLM generation cites a specific dimension by name ("Biggest gap is X") where X is the dimension with the lowest readiness percentage.

6. Grep the codebase for the six dimension IDs (`allowable_costs`, `transaction_documentation`, `time_effort`, `procurement`, `subrecipient_monitoring`, `performance_reporting`). Each should appear in exactly one canonical definition location, with all other references being imports or lookups.

7. Either the orphaned `cockpit-fixture.json` has been archived with a clear rename and README note, or it has been removed from the repo (git history preserves it).

---

## Version history

- **v1 — 2026-04-23 — Initial spec (speculative).** Drafted before existing implementation was inspected. Proposed 4 cards + 7 sub-tabs. Replaced by v1.2 after reconciliation diagnostic revealed existing Audit Readiness tab is more built than v1 assumed.
- **v1.1 — 2026-04-23 — Path A committed.** Two-service architecture confirmed. Superseded by v1.2.
- **v1.2 — 2026-04-23 — Reconciled with existing implementation.** Preserves the existing UI (verdict + 3 stat cards + 6-dimension table + drillable rows). Work is backend-only: replace hardcoded values with computed values, replace placeholder "Open gaps" with real gap lists, replace hardcoded activity feed with fetched events. Drops v1's speculative sub-tab structure. Incorporates duplication-elimination requirement (Change 4) and orphaned-fixture cleanup (Change 5) based on the drill panel inventory diagnostic.
- **v1.2.2 — 2026-04-23 — Documentation linkage path resolved.** Diagnostic confirmed no field exists on `Transaction` model and QB sync does not capture attachment data. Step 1.5 added to implementation order: add `attachment_count` column, `sync_attachables` step, Alembic migration. Documentation Gap computation specified.
- **v1.2.3 — 2026-04-23 — Step 2 scope decisions.** Diagnostic on data-model gaps determined that four of six dimensions (time_effort, procurement, subrecipient_monitoring, performance_reporting) require data models not present in the engine and are deferred to v1.3+. Two dimensions (allowable_costs, transaction_documentation) are computed in v1.2 — allowable_costs requires adding Transaction.last_scanned_at for an honest denominator. Computation location decided: engine computes, cockpit orchestrates (B1). Branch split decided: engine-side commit first on feature/compliance-engine-extract, cockpit-side wiring as follow-up commit on feature/finance-cockpit.
- **v1.2.4 — 2026-04-23 — Engine-side step 2 implementation decisions captured.** Allowable costs formula clarified to use distinct-flagged-transactions in numerator (prevents pct < 0 with multi-flag transactions). Three-state dimension status (`computed` with value, `computed` with null, `placeholder` with null) documented for cockpit consumption. Defensive percentage clamping documented.
- **v1.2.5 — 2026-04-23 — Step 3 scope decisions.** T&E Certifications stat card joins time_effort dimension as a v1.2 placeholder pending Employee↔Grant data model. Overall Readiness aggregates only computed dimensions with non-null percentages; subcopy reflects dynamic count. Documentation Gap is computable now, unblocked from step 1.5.
