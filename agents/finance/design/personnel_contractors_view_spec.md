# Feature Spec — Personnel & Contractors View

**Audience:** Claude Code (implementation)
**Spec owner:** Ritu Bahl
**Target location in cockpit:** Sub-section under existing "Budget & Burn" tab
**Branch:** `feature/finance-cockpit` (cockpit-only feature; no engine changes needed)
**Status:** Draft for implementation
**Date:** April 29, 2026

---

## Spec file placement

Before implementing, Claude Code should determine where this spec file should live based on existing convention:

- **Cockpit design docs** are at `agents/finance/design/` (alongside `cockpit_data.py`, `cockpit_template.html`, `generate_cockpit.py`)
- **Grant-compliance design docs** are at `agents/grant-compliance/docs/` (alongside `audit_readiness_tab_spec.md`)

Inspect both locations and any other docs already present. Place this spec in whichever directory matches the convention used for cockpit-side design specs. If neither location has a precedent for cockpit-side specs, prefer co-locating with the cockpit code at `agents/finance/design/`. Save the spec as `personnel_contractors_view_spec.md`.

---

## Purpose

Surface every person being paid through the K8341 grant — CFA staff, CFA contractors, and AI Engage — with their rate, total amended budget allocation, paid-to-date, projected remaining payments through grant end, and variance against budget. This is the foundational view for understanding personnel and contractor spending in the cockpit.

The view must reconcile to the Amendment 1 budget (approved November 2025) at the budget-line roll-up level. Quarterly updates by Krista replace projected values with actuals as time passes.

This is the first add to the cockpit following the v1.2 release; it lands on the existing v1.2 architecture without dependencies on `wfdos-common` or other v1.3 work.

---

## Why this matters

CFA's project knowledge currently conflates budget line totals with individual contractor allocations — for example, the $775,823.40 "CFA Contractors" line in CLAUDE.md is incorrectly attributed to Pete & Kelly Vargo specifically when it actually covers all CFA-hired contractors except AI Engage. This view is the structural fix: each person gets their own row with their own numbers, and the aggregate ties back to budget lines, eliminating the conflation.

It also creates the data foundation that downstream compliance dimensions will reference (Allowable Costs sub-views for personnel, Time & Effort dimension, Procurement dimension for contractors).

---

## Population (who's surfaced)

Every person whose compensation is charged to K8341 federal funds, in any of the following Amendment 1 budget categories:

- **Personnel: Salaries** — CFA salaried employees with payroll allocation to the grant
- **Personnel: Benefits** — same employees as Salaries (benefits row per employee)
- **GJC Contractors** (Strategic Partners portion only — not training providers, see exclusions) — to the extent any individuals can be named
- **CFA Contractors** — all CFA-hired contractors including AI Engage and the Vargos

**Exclusions (out of scope for this feature):**

- Training provider staff (Ada instructors, Per Scholas trainers, etc.) — these are paid through the providers, not directly by CFA, and are not surfaced as individuals
- People working *for* AI Engage on placement recovery — surface AI Engage as the contractor; AI Engage's internal team is AI Engage's responsibility
- PAP teachers and other CFA staff funded from non-grant sources (donations, etc.) — only grant-funded personnel are in scope
- Provider/training organization employees in any form

---

## Data model

Each person is a row with the following fields:

### Identity
- `name` (string) — display name
- `role` (string) — function or job title (e.g., "Project Director," "Finance Manager," "Placement Recovery Lead")
- `engagement_type` (enum) — `employee` | `contractor` | `subcontractor`
- `vendor_legal_entity` (string, optional) — for contractors, the legal entity name as it appears on contracts and in QB (e.g., "AI Engage Group LLC"); may differ from display name
- `start_date` (date)
- `end_date` (date or null) — null means through grant end

### Budget allocation
- `budget_line` (enum) — `personnel_salaries` | `personnel_benefits` | `cfa_contractors` | `gjc_contractors_strategic` (extend if needed)
- `amended_budget_total` (decimal, USD) — total Amendment 1 allocation for this person across the full grant period
- `amended_budget_remaining_periods` (decimal, USD, computed) — `amended_budget_total` minus `paid_to_date`

### Rate
- `rate_amount` (decimal, USD)
- `rate_unit` (enum) — `hourly` | `daily` | `weekly` | `monthly` | `annual` | `fixed_fee` | `milestone`
- `rate_basis` (string, free text) — short description of how the rate was set (e.g., "Negotiated at contract execution; comparable to market rate for equivalent services" or "Annual salary per CFA HR policy"). This is the field that supports cost reasonableness documentation downstream.
- `rate_effective_date` (date)
- `rate_history` (list of prior rate records, optional for v1) — defer if not in input data

### Actuals (per quarter)
A list or sub-table of quarterly payment records:
- `quarter` (string, format `YYYY-QN`, e.g., `2024-Q1`)
- `amount_paid` (decimal, USD)
- `source` (string) — `qb` | `payroll` | `manual_entry`
- `qb_vendor_name` (string, optional) — the vendor name as it appears in QuickBooks, since these may differ from display name (this resolves the "AI Engage Group LLC vs Jason Mangold vs AI Engage" reconciliation problem)

### Projected (per remaining quarter)
A list of projected quarterly payments through grant end (September 30, 2026):
- `quarter` (string)
- `projected_amount` (decimal, USD)
- `projection_basis` (string, free text) — short note on how the projection was derived (e.g., "Linear projection based on average of last 4 quarters" or "Per contract terms — fixed monthly fee")

### Computed
- `paid_to_date` (decimal, USD, computed) — sum of all `amount_paid` across actual quarters
- `projected_total_remaining` (decimal, USD, computed) — sum of `projected_amount` across remaining quarters
- `total_committed` (decimal, USD, computed) — `paid_to_date + projected_total_remaining`
- `variance_vs_amended` (decimal, USD, computed) — `amended_budget_total - total_committed` (positive = under budget, negative = projected overrun)
- `variance_pct` (decimal, computed) — `variance_vs_amended / amended_budget_total`

---

## Source of truth and update workflow

**Recommendation request:** Claude Code should read the existing data pipeline at `agents/finance/design/cockpit_data.py`, the existing data inputs (spreadsheets) it reads, and the QB integration patterns. Then recommend the input mechanism that best matches the existing architecture. Two leading candidates:

- **Spreadsheet input** (e.g., `WJI_Personnel_and_Contractors.xlsx` dropped into the existing inputs location, parsed by an extension to `cockpit_data.py`)
- **JSON/YAML config** in a co-located data directory, versioned in the repo

The recommendation should consider: how Krista currently updates other financial data, the existing extraction pattern, what minimizes friction for quarterly updates, and what's auditable for federal grant work. Whichever pattern is recommended, document the choice in a comment at the top of the new extraction function and use the same pattern.

**Update cadence:**
- Initial population: comprehensive, manual entry from existing payroll records, contracts, and QB vendor history
- Quarterly thereafter: Krista updates the actuals quarter for the quarter just closed, and re-projects remaining quarters based on actuals to date
- Mid-quarter changes (new contractor added, rate change, contract amendment): updated as they occur

The "revised every quarter to reflect actuals" requirement means projections must be recalculated against actuals at quarter-close. This is a manual workflow for Krista, not an automated recompute.

---

## Data extraction (`agents/finance/design/cockpit_data.py` changes)

Add an `extract_personnel_and_contractors()` function (or equivalent, matching existing naming conventions in `cockpit_data.py`) that:

1. Reads the chosen input source (spreadsheet or config file per recommendation above)
2. Validates the data shape against the data model above
3. Computes the derived fields (`paid_to_date`, `projected_total_remaining`, `total_committed`, `variance_vs_amended`, `variance_pct`)
4. Computes budget-line roll-ups: for each `budget_line`, sum `amended_budget_total`, `paid_to_date`, `total_committed`, `variance_vs_amended` across all people in that line
5. Returns a structured object that the template consumes

The roll-up totals MUST reconcile to the Amendment 1 budget for each line. If they don't, raise a validation error or surface a prominent warning in the rendered output. This is a hard constraint — silent reconciliation drift is exactly the failure mode this feature is designed to prevent.

Reconciliation reference (Amendment 1):

| Budget line | Amendment 1 total |
|---|---|
| Personnel: Salaries | $1,097,662.41 |
| Personnel: Benefits | $173,169.94 |
| CFA Contractors (incl. AI Engage) | $1,020,823.40 |

(GJC Contractors and other lines per Amendment 1; reference the existing budget data already in `cockpit_data.py`.)

---

## Rendering (`agents/finance/design/cockpit_template.html` changes)

Add a new sub-section to the existing **Budget & Burn** tab. Place after existing budget category roll-ups, before any other existing sub-sections (or wherever best fits the existing IA — Claude Code's judgment based on what's already there).

### Sub-section header
"Personnel & Contractors" (or whatever naming matches the existing tab's section-naming convention).

### Layout

**Top:** Three summary stat cards in the existing card style (matching the home page's "Are we okay?" cards):
- **Total grant-funded personnel & contractors:** count of distinct people
- **Paid to date (all categories):** sum of `paid_to_date` across all rows
- **Projected variance through Sept 30, 2026:** sum of `variance_vs_amended` across all rows, with sign and color coding (positive = under budget = green, negative = over budget = red)

**Middle:** A grouped table, one section per `budget_line`. Within each section:
- Header row: budget line name, amended budget for the line, paid to date for the line, projected remaining for the line, line-level variance
- Data rows: one per person, with columns: Name, Role, Engagement type, Rate (formatted as `$X / unit`), Amended budget, Paid to date, Projected remaining, Variance, Variance %
- Sort: by `amended_budget_total` descending within each section
- Variance column color-coded: green if positive (under budget), red if negative (overrun)

**Bottom:** A "What's not in this view" footer noting the explicit exclusions (training provider staff, AI Engage internal team, non-grant-funded staff). This is for transparency — anyone reading the view should know what's deliberately omitted.

### Per-person drill-down

Clicking a person row opens a drill panel (matching the existing audit dimension drill pattern) showing:
- **Identity:** all fields from the Identity section
- **Rate detail:** `rate_amount`, `rate_unit`, `rate_basis`, `rate_effective_date`
- **Quarterly actuals:** chronological table of all `actuals` records for this person
- **Quarterly projections:** chronological table of all projected payments
- **QB reconciliation:** the `qb_vendor_name`, paid-to-date sum, with a flag if the sum differs from QB by more than $100 (use existing QB data already in the cockpit pipeline if available)

### Honesty discipline
Use the same three-state pattern as the v1.2 audit dimensions:
- If a person row is missing required fields (e.g., no `rate_basis` documented), display a clear "documentation incomplete" indicator on that row, do not invent or interpolate values
- If a budget line's roll-up doesn't reconcile to Amendment 1, display a prominent warning at the section level with the reconciliation delta — do not silently accept the drift
- If projections are missing for remaining quarters, mark them explicitly as "not yet projected" rather than defaulting to zero (zero is a value; missing is missing)

---

## Acceptance criteria

The implementation is complete when all of the following are true:

1. The Personnel & Contractors sub-section renders under the Budget & Burn tab
2. Every person currently paid through K8341 grant funds appears as a row in the appropriate budget line section (depends on initial data population — see open questions)
3. The roll-up for each budget line reconciles to Amendment 1 (or surfaces a clear reconciliation warning if it doesn't)
4. Each row shows the full data model (name, role, engagement type, rate, amended budget, paid to date, projected remaining, variance, variance %)
5. Drill-down on each person shows the full per-person detail including quarterly actuals and projections
6. Quarterly update workflow is documented (a README or inline comment explaining how Krista updates the data each quarter)
7. The chosen input mechanism (spreadsheet or config) is in place with at least the initial complete data population
8. Three summary stat cards render at the top of the sub-section
9. The "What's not in this view" footer is present and accurate
10. No silent reconciliation drift; no invented values; no defaulted-to-zero projections

---

## Out of scope (explicit — Claude Code, do not implement these)

- Automated payroll integration (manual entry / spreadsheet input only)
- Automated QB sync to refresh actuals (this comes when v1.3.0 wfdos-common integration lands; for now, actuals are manually entered or sourced from the existing QB extracts already in the pipeline)
- CRUD UI for editing person records in the browser (defer to v1.3+ with proper auth)
- Time and effort certification workflow (this is the v1.3.3 dimension, separate spec)
- Cost reasonableness analysis automation (this is the v1.3.4 procurement dimension, separate spec)
- Subrecipient personnel surfacing (training provider staff are out of scope per the exclusions section)
- Cross-grant personnel (people working on multiple grants — for now, K8341 only)
- Projection algorithms beyond linear/manual (no machine learning, no curve fitting; Krista projects manually per person and the cockpit displays what she enters)
- Engine-side changes (this feature is cockpit-only; do not touch `agents/grant-compliance/`)

---

## CLAUDE.md correction (required as part of this PR)

The current CLAUDE.md contains an incorrect attribution: under "CFA Contractors Detail," the line `CFA Contractors (Pete & Kelly Vargo): $775,823.40 amended budget` conflates a budget category total with a per-individual allocation. This is wrong — the $775,823.40 covers all CFA-hired contractors except AI Engage, not just Pete & Kelly Vargo.

As part of this PR, replace that line with an accurate description. Suggested replacement (Ritu to confirm wording):

> CFA Contractors (excluding AI Engage): $775,823.40 amended budget — covers all CFA-hired contractors working under the grant, with individual allocations surfaced in the Personnel & Contractors view in the Budget & Burn tab.

This correction is part of the same PR as the feature implementation because the new view replaces the need for individual attribution in CLAUDE.md — the cockpit becomes the source of truth for per-person allocations.

---

## Implementation order

Recommended sequence (Claude Code may adjust if the existing codebase suggests otherwise):

1. Read the existing pipeline (`agents/finance/design/cockpit_data.py`, `cockpit_template.html`, `generate_cockpit.py`) and recommend the input mechanism
2. Place this spec file in the appropriate directory per the convention check at the top of this document
3. Define the data model in code (dataclasses or schema, matching existing patterns in `cockpit_data.py`)
4. Implement the input parser and validation
5. Implement `extract_personnel_and_contractors()` with computed fields and roll-ups
6. Implement reconciliation check against Amendment 1 budget lines
7. Add rendering to the template (stat cards, grouped table, drill-down)
8. Populate initial data with the complete person list (Ritu and Krista provide the underlying data; Claude Code structures it into the chosen input format) — pause here if the data isn't ready
9. Verify acceptance criteria
10. Apply CLAUDE.md correction
11. Commit with a clear commit message describing the new feature, the input mechanism chosen, and the CLAUDE.md fix

Stop after step 11 and report. Do not proceed to v1.3 work or other features without explicit instruction. Do not modify anything in `agents/grant-compliance/` — this is cockpit-only.

---

## Open questions for Ritu (before step 8)

1. The complete list of grant-funded personnel and contractors — Ritu and Krista to provide. Without this list, the spec can be implemented but cannot be populated with real data.
2. Confirm the suggested CLAUDE.md replacement wording, or provide an alternative.
3. Confirm placement under Budget & Burn (vs. elsewhere) is final.

These should be resolved before step 8 (initial data population). Steps 1–7 can proceed in parallel with Ritu gathering the personnel list.

---

## Implementation decisions (recorded by Claude Code)

**Step 1 — input mechanism:** Excel workbook at `agents/finance/design/fixtures/K8341_Personnel_and_Contractors.xlsx`. Three sheets: `People` (one row per person), `Actuals` (one row per person-quarter payment), `Projections` (one row per person-quarter projection). A `_README` sheet documents the schema. Rationale: matches the existing five-Excel pipeline pattern Krista already uses; openpyxl is already a dependency; commits of the .xlsx in git provide audit trail; the parser also writes a JSON snapshot to `K8341_Personnel_and_Contractors.snapshot.json` at extract time for diffability.

**Step 2 — spec placement:** `agents/finance/design/personnel_contractors_view_spec.md`. Co-located with cockpit-side design docs (`chat_spec.md`, `design_notes.md`, `cockpit_design_fixes.md`, `deferred_fixes.md`).

**Render targets:** Both the HTML mockup (`cockpit_template.html` rendered by `generate_cockpit.py`) and the React cockpit (`portal/student/app/internal/finance/...` served by `cockpit_api.py` on :8013). React is the live surface Krista uses; the mockup is design reference.
