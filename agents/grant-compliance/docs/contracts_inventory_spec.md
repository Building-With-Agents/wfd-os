# Feature Spec — Contracts Inventory

**Audience:** Claude Code (implementation)
**Spec owner:** Ritu Bahl
**Target location:** Engine-side data model with cockpit-side display
**Branch:** Engine-side work on `feature/compliance-engine-extract`; cockpit-side work on `feature/finance-cockpit`. Two separate Claude Code sessions, in that order.
**Status:** Draft for implementation
**Date:** April 30, 2026

---

## Spec amendment history

**2026-04-30 (engine-side session start, by Ritu Bahl):** `procurement_method`
field on Contract moves from v1.1 (deferred) to v1 (engine-side schema below).

Rationale — the Compliance Requirements Display Session 2 documentation status
workflow needs to filter Contracts by procurement method to auto-generate
per-target documentation status rows for sole-source-only requirements
(e.g. requirements that only apply when `procurement_method = sole_source`).
Adding the field now, while the Contract table is being created for the
first time, is materially smaller than retrofitting it after Session 2 has
already pinned its applicability filter shape against an absent column.

The associated artifact tracking (RFP files, proposal evaluations, sole-source
justification narratives, etc.) remains deferred to v1.1 per the original
plan — only the categorical method field itself moves forward. See the
v1 schema below and the updated deferred section item #3.

---

## Purpose

Establish a comprehensive structured inventory of every contract under K8341, engine-side, as the canonical entity that downstream features reference.

The Contracts inventory is the hub entity that connects:

- **Compliance Requirements documentation status** — applicable_target references contract_id when a requirement applies to specific contracts
- **Monitoring engagements** — ContractUnderReview sub-records reference Contract IDs to indicate which contracts are under review
- **Audit Readiness dimensions** (procurement, subrecipient monitoring) — sweep Contracts filtered by classification to compute readiness scores
- **Personnel feature** — Person.vendor_legal_entity matches Contract.vendor_legal_entity for CFA contractors (loose coupling in v1; tighter integration in future)
- **Future features** — RFP inventory, invoice inventory, subrecipient monitoring records all reference Contracts

Without a structured inventory, these features either duplicate contract data (creating multiple sources of truth) or operate against unstructured strings (creating brittle joins). Engine-side canonical storage solves both problems.

---

## Why this matters now

The Compliance Requirements Agent has produced 58 requirements. Many of them apply per-contract: "for each contract above $250K, document a cost or price analysis", "for each subrecipient, complete a §200.331(a) determination", "for each sole-source procurement, document the §200.320(c) basis." Mapping these requirements to specific CFA contracts requires knowing which CFA contracts exist, what their classifications are, and what their values are.

For Phouang's procurement review specifically, three contracts are under examination: AI Engage, Pete Vargo, Kelly Vargo. Krista will hunt documentation against the agent's requirements, and the cockpit needs a structured place to record what's found per contract. That's the documentation status workflow (Session 2 of the display spec). It depends on this Contracts inventory being in place.

For the broader audit-readiness vision, Contracts is the master data that everything else hangs off of. Building it cleanly now pays off across at least four downstream features.

---

## Scope

**In scope:**

Every formal agreement under which CFA pays a third party with K8341 grant funds, regardless of dollar amount, current status (active, closed, terminated), or party type.

This includes:
- Training provider contracts (Ada, Year Up, Vets2Tech, Per Scholas, Code Day, Apprenti, NCESD, Riipen)
- Strategic partner contracts (subrecipients: WABS, WTIA, Evergreen Goodwill, Seattle Jobs Initiative, ESD 112, I&CT, others)
- CFA contractor agreements (AI Engage, Pete Vargo, Kelly Vargo, others identified through Krista's data extraction)
- ESD-terminated contracts (WABS, NCESD, Riipen) with appropriate closed status
- Any other agreement under which K8341 grant funds flow to a third party

**Out of scope:**

- Employment agreements with CFA W2 employees (those are HR records, surfaced via Personnel feature)
- Vendor agreements not paid from grant funds (general office vendors, non-grant CFA operations)
- Pure purchase orders for goods (this feature is contracts for services and subawards; goods procurement deferred to v1.1+)
- Subcontracts between CFA's contractors and third parties (e.g., AIE's own subcontractors are AIE's responsibility, not CFA's first-class data)
- Memoranda of understanding without financial terms (informational; not paid contracts)

---

## Engine-side data model

### Contract (new SQLAlchemy table)

Primary entity with the following structure:

- `contract_id` (UUID PK)
- `grant_id` (FK to grants table)
- `vendor_party_id` (UUID, optional FK to a future parties table; for v1, free-text matching)
- `vendor_name_display` (string) — UI display name (e.g., "Ada Developers Academy", "Pete Vargo")
- `vendor_legal_entity` (string) — legal entity name as on the executed contract
- `vendor_qb_names` (array of strings) — all variations of how this vendor appears in QB (resolves the AI Engage / Jason Mangold / AI Engage Group LLC name problem)
- `contract_type` (enum) — `training_provider` | `strategic_partner_subrecipient` | `cfa_contractor` | `subrecipient_other` | `other`
- `compliance_classification` (enum) — `contractor_200_331b` | `subrecipient_200_331a` | `unclassified`
- `classification_rationale` (text, optional) — short narrative; references §200.331 characteristics. Optional in v1 — populated as classification work happens; full structured determination comes through Monitoring engagements where applicable.
- `procurement_method` (enum, **promoted to v1 — see amendment 2026-04-30**) — `competitive_rfp` | `competitive_proposals` | `small_purchase` | `micro_purchase` | `sole_source` | `informal` | `unknown` | `not_applicable_subaward`. Categorical only; the associated artifacts (RFP files, evaluations, sole-source justification text) remain v1.1 per the deferred section. Default at bootstrap is `unknown` so contracts whose method Krista hasn't yet confirmed are explicitly visible rather than silently mis-classified.
- `original_executed_date` (date)
- `original_effective_date` (date) — may pre-date executed_date for pre-award contracts
- `current_end_date` (date) — after any amendments
- `original_contract_value_cents` (BigInteger) — value at original execution (in cents, per engine convention)
- `current_contract_value_cents` (BigInteger) — after amendments
- `status` (enum) — `active` | `closed_normally` | `closed_with_findings` | `terminated_by_cfa` | `terminated_by_funder`
- `payment_basis` (enum) — `per_placement` | `fixed_fee` | `time_and_materials` | `milestone` | `cost_reimbursement` | `other`
- `payment_basis_detail` (text, optional)
- `executed_contract_link` (string, optional) — URL or path to executed contract document
- `scope_of_work_summary` (text, 1-3 sentences)
- `notes` (text, optional)
- `record_created_at` (datetime)
- `record_updated_at` (datetime)
- `record_updated_by` (string)

### ContractAmendment (new SQLAlchemy table)

For amendments to contracts. One row per amendment.

- `amendment_id` (UUID PK)
- `contract_id` (FK to contracts)
- `amendment_number` (integer) — 1, 2, 3, etc.
- `amendment_type` (enum) — `value_change` | `period_extension` | `scope_change` | `termination` | `other`
- `executed_date` (date)
- `effective_date` (date)
- `previous_value_cents` (BigInteger)
- `new_value_cents` (BigInteger)
- `previous_end_date` (date)
- `new_end_date` (date)
- `summary_of_changes` (text)
- `document_link` (string, optional)
- `record_created_at` (datetime)

### ContractTerminationDetail (new SQLAlchemy table, optional)

For terminated contracts. One row per terminated contract.

- `termination_id` (UUID PK)
- `contract_id` (FK)
- `terminated_by` (enum) — `cfa` | `funder` | `mutual`
- `termination_date` (date)
- `termination_reason` (text)
- `termination_correspondence_link` (string, optional)
- `final_reconciliation_link` (string, optional)
- `closeout_findings` (text, optional)
- `record_created_at` (datetime)

### Computed fields (NOT stored, computed at query time)

- `total_paid_to_date_cents` — sum of payments from existing transactions table where vendor_name matches Contract.vendor_qb_names
- `is_above_simplified_acquisition_threshold` — `current_contract_value_cents >= 25000000` ($250K)
- `is_above_micro_purchase_threshold` — `current_contract_value_cents >= 1000000` ($10K)
- `requires_cost_or_price_analysis` — true if above SAT and `compliance_classification = contractor_200_331b`
- `is_subject_to_subrecipient_monitoring` — true if `compliance_classification = subrecipient_200_331a`
- `is_active` — true if `status = active`
- `is_closed` — true if status in (closed_normally, closed_with_findings, terminated_by_cfa, terminated_by_funder)

### Reconciliation constraint (computed and surfaced)

For each contract_type that maps to an Amendment 1 budget line:

- Sum of `current_contract_value_cents` for `contract_type = training_provider OR strategic_partner_subrecipient` should reconcile to GJC Contractors line: $2,315,623.07
- Sum for `contract_type = cfa_contractor` should reconcile to CFA Contractors line: $1,020,823.40

If totals don't reconcile, surface drift warnings prominently. Same honesty discipline as Personnel.

---

## Engine-side endpoints

- `GET /contracts?grant_id=...` — returns all contracts for a grant, optionally filtered by contract_type, classification, status
- `GET /contracts/{contract_id}` — returns one contract with amendments and termination detail
- `POST /contracts` — creates a contract (used by bootstrap import; v1 has no UI for this)
- `PUT /contracts/{contract_id}` — updates a contract (v1 used by bootstrap import; v1.1 will add UI)
- `GET /contracts/reconciliation?grant_id=...` — returns reconciliation status: per-budget-line expected vs actual sums, drift warnings

All mutations create audit_log entries per the engine's existing pattern.

---

## Bootstrap import mechanism

The initial population of contracts happens via Excel import, similar to the Personnel feature pattern but as a one-time bootstrap rather than ongoing data entry.

### Excel structure

File: `agents/grant-compliance/data/contracts_bootstrap/K8341_Contracts.xlsx`

Three sheets:
- **Contracts**: one row per contract, denormalized — joins Contract identity + classification + dates + financial + status + scope + executed contract link
- **Amendments**: one row per amendment with `contract_id` foreign key
- **Terminations**: one row per terminated contract with `contract_id` FK

### Import pipeline

A new module `agents/grant-compliance/src/grant_compliance/contracts_bootstrap/` with:

- `loader.py` — reads the Excel file, validates schema, produces structured Contract/Amendment/Termination records
- `importer.py` — takes loaded records, persists them to the engine database via the SQLAlchemy models, with audit_log entries
- `reconciliation.py` — computes the budget-line reconciliation, surfaces drift

### CLI command

A new CLI command `python -m grant_compliance.contracts_bootstrap import --file <path>` that:

1. Reads the Excel file
2. Validates structure
3. Reports what would be imported (dry run)
4. Asks for confirmation
5. Performs the import with full audit_log trail

This is meant to be run once per grant for the initial population. Subsequent updates happen through the API (or, in v1.1, through cockpit UI).

---

## Cockpit-side display

After the engine-side work ships, cockpit-side display follows.

### Placement

Recommend based on existing IA — same pattern as Compliance Requirements Display. Default fallback options:

- New top-level "Contracts" tab (probably 8th tab; cockpit is getting tab-heavy but Contracts is foundational)
- Sub-section of Audit Readiness tab (smaller surface; less prominent)
- Sub-section of Compliance Requirements tab (logical adjacency; contracts are what compliance requirements apply to)

Claude Code's IA review picks based on what fits the cockpit's actual structure.

### Layout

**Top of section — summary cards:**

- Total contracts: count
- By classification: contractor count vs subrecipient count vs unclassified count
- Active vs closed: current operational status
- Reconciliation: per-budget-line expected vs actual, with drift indicators
- Above SAT count: how many contracts cross the $250K threshold (relevant for cost-or-price analysis requirements)

**Filter bar:**

- Contract type (multi-select): training_provider, strategic_partner_subrecipient, cfa_contractor, subrecipient_other, other
- Classification (multi-select): contractor_200_331b, subrecipient_200_331a, unclassified
- Status (multi-select): active, closed_normally, closed_with_findings, terminated_by_cfa, terminated_by_funder
- Payment basis (multi-select): per_placement, fixed_fee, time_and_materials, milestone, cost_reimbursement, other
- Procurement method (multi-select, **new in v1 per amendment 2026-04-30**): competitive_rfp, competitive_proposals, small_purchase, micro_purchase, sole_source, informal, unknown, not_applicable_subaward
- Above thresholds (toggles): above MPT ($10K), above SAT ($250K)
- Free-text search (vendor name, scope summary)

**Main view — grouped table:**

Default grouping by `contract_type`, with each section showing:
- Section header: type label, count, total committed value, status distribution
- Data rows: vendor name (display + legal entity), classification badge, status badge, original value, current value, paid to date, amendment count, scope summary (truncated)

Sort within each section: by current_contract_value descending.

**Per-contract drill-down:**

Click a contract row → drill panel shows:
- Identity: full name, legal entity, QB name variations, type, classification with rationale if populated, procurement method (with `unknown` displayed as a visible amber state — not silently absent)
- Dates: original executed, original effective, current end date, status timeline
- Financial: original value, current value, paid to date, payment basis with detail, threshold indicators
- Amendments: chronological list with summaries and document links
- Termination (if applicable): reason, date, correspondence, closeout findings
- Documentation: executed contract link, scope of work
- Compliance: list of Compliance Requirements that reference this contract via documentation_status entries (when Session 2 is shipped); empty until then with a note explaining when it'll populate
- Linked entities: Person rows from Personnel feature where vendor_legal_entity matches (loose coupling in v1)

**Reconciliation banner:**

Same pattern as Personnel: prominent warning when per-budget-line sums don't match Amendment 1 totals. Visible at the top of the section.

### Honesty discipline

- Reconciliation drift surfaced prominently
- Closed and terminated contracts visibly distinct from active
- Classification status (unclassified vs contractor vs subrecipient) shown explicitly
- Procurement method shown explicitly — `unknown` is a visible state, never silently filtered out
- Computed fields (threshold indicators, requires_cost_or_price_analysis) shown without rounding up or hiding edge cases
- "Last updated" timestamp on each contract so staleness is visible

---

## Acceptance criteria

### Engine-side acceptance

The engine-side work is complete when:

1. New tables (Contract, ContractAmendment, ContractTerminationDetail) exist with proper schema
2. Alembic migration applied
3. Endpoints (GET list, GET detail, POST, PUT, GET reconciliation) function correctly
4. Bootstrap import CLI works end-to-end against a populated Excel file
5. Audit trail captures all mutations
6. Reconciliation computation correctly identifies drift against Amendment 1 line totals

### Cockpit-side acceptance

The cockpit-side work is complete when:

7. Contracts display surface appears in the cockpit (placement per Claude Code's IA recommendation)
8. Summary cards render with accurate counts and reconciliation status
9. Filter bar functions for all listed dimensions
10. Grouped table renders with type-grouped sections
11. Per-contract drill panel shows full detail including amendments and termination if applicable
12. Reconciliation banner shows drift prominently when present
13. Both static HTML mockup and React surface render

---

## Out of scope (explicit — Claude Code, do not implement)

### Out of scope for v1

- CRUD UI in the cockpit (Krista cannot edit contracts through the cockpit in v1; bootstrap import is the only write path; v1.1 adds UI)
- Automated SharePoint sync of contract metadata (defer to v1.3.0 SharePoint connector)
- Procurement file ingestion (RFPs, proposals, evaluations are a separate feature)
- Cost reasonableness documentation per contract (lives in compliance_documentation_status entries, separate concern)
- Multi-tenant operation (K8341-specific in v1)
- Cross-grant contract comparison (single grant in v1)

### Deferred to v1.1+

Captured here so the ideas don't get lost:

**1. CRUD UI for contract editing.** Krista (and authorized users) edit contracts through the cockpit. v1.1 with proper auth.

**2. Cost reasonableness documentation per contract.** Per-contract structured fields for IC estimates, market comparisons, cost-or-price analysis status. v1.1 — initially these are tracked through compliance_documentation_status entries (Session 2 of display spec).

**3. Procurement artifact tracking per contract.** _Amended 2026-04-30: only the artifact tracking remains deferred; the categorical `procurement_method` enum field on Contract moved to v1, see schema and amendment history above._ RFP/proposal artifacts, evaluation documentation, sole-source justification narratives. v1.1.

**4. Conflict-of-interest documentation per contract.** COI disclosures, family relationships, disposition. Particularly relevant for Pete and Kelly Vargo. v1.1.

**5. Subrecipient monitoring records.** For subrecipient contracts, the structured monitoring activities (risk assessment, monitoring visits, follow-up, closure). Separate feature.

**6. Subaward agreement required terms tracking.** §200.332(b) requires fifteen specific elements in every subaward agreement. v1.1 adds structured per-agreement compliance tracking.

**7. Document content ingestion.** v1 stores links only; v1.1+ may extract structured data from contract PDFs.

**8. Cross-contract pattern detection.** "Multiple contracts using same sole-source justification basis" — kind of pattern alert. v1.2+.

**9. Notification on contract changes.** When contract data changes, notify designated stakeholders. v1.1+.

**10. Contract template management.** Standard contract templates with required clauses. Outside cockpit scope; defer to vendor-managed contract management system.

**11. Direct integration with QB Vendor Center.** When a QB transaction is recorded against a vendor, automatically link to the matching Contract row. v1.3.0+ via QB connector.

---

## Forward seams

This feature establishes the Contract entity that other features reference:

- **Compliance Requirements Display Session 2 (documentation status):** applicable_target_id references contract_id when a requirement applies to specific contracts. Session 2 will additionally filter by `procurement_method` to auto-generate per-target documentation status rows for sole-source-only requirements (the reason `procurement_method` was promoted to v1 — see amendment history above).
- **Monitoring v1:** ContractUnderReview sub-records reference Contract IDs. Monitoring's per-contract data (counsel review status, engagement-specific documentation tracking) projects onto Contract identity.
- **Audit Readiness — Procurement dimension (v1.3.4):** sweeps Contracts filtered by classification = contractor_200_331b to compute readiness from documentation status.
- **Audit Readiness — Subrecipient Monitoring dimension (v1.3.1):** sweeps Contracts filtered by classification = subrecipient_200_331a.
- **Personnel feature:** Person.vendor_legal_entity loose-couples to Contract.vendor_legal_entity for CFA contractors. Future migration may add explicit contract_id reference.
- **Future Invoice inventory feature:** Invoices reference Contract IDs.
- **Future RFP inventory feature:** RFPs reference Contract IDs (the contract that resulted from the RFP).
- **Future Subrecipient Monitoring records feature:** Monitoring activities reference Contract IDs for subrecipient contracts.

---

## Implementation order

### Engine-side session

1. Read existing engine architecture and conventions
2. Save this spec at `agents/grant-compliance/docs/contracts_inventory_spec.md`
3. Define SQLAlchemy models (Contract, ContractAmendment, ContractTerminationDetail) in `db/models.py`
4. Create Alembic migration
5. Define Pydantic schemas in `contracts_bootstrap/schemas.py`
6. Implement bootstrap loader (Excel parsing) in `contracts_bootstrap/loader.py`
7. Implement bootstrap importer (database persistence) in `contracts_bootstrap/importer.py`
8. Implement reconciliation computation in `contracts_bootstrap/reconciliation.py`
9. Implement API endpoints in `api/routes/contracts.py`
10. Wire CLI command for bootstrap import
11. Test end-to-end with a minimal sample Excel file (2-3 contracts)
12. Commit engine-side work

### Cockpit-side session (after engine-side ships)

13. Read cockpit IA and recommend display placement
14. Define TypeScript types mirroring engine schemas
15. Implement contracts API client in cockpit
16. Build summary cards, filter bar, grouped table, drill panel
17. Wire reconciliation banner (calls /contracts/reconciliation endpoint)
18. Verify end-to-end against engine-side data
19. Commit cockpit-side work

### Bootstrap data population (after both ship)

20. Krista provides comprehensive contract list with all required fields per the spec — leveraging the data extraction email already drafted for her
21. Excel file populated against the bootstrap template
22. CLI import run to populate engine database
23. Verify reconciliation against Amendment 1 budget lines

This step is human work, not implementation. Roughly 1-2 days of Krista's time given she's already pulling related data for the Personnel feature.

---

## Open questions for Ritu (before implementation)

_All five answered as defaults at session start 2026-04-30; preserved here for future reference._

1. Confirm comprehensive scope (all 18-20 K8341 contracts including training providers, strategic partners, CFA contractors, ESD-terminated). **Answered: yes, comprehensive.**
2. Confirm engine-side data model with cockpit-side display (vs. cockpit-only Excel). **Answered: engine + cockpit.**
3. Confirm placement decision is delegated to Claude Code's IA review. **Answered: yes.**
4. Confirm bootstrap-import-only for v1 (no CRUD UI; CRUD comes in v1.1). **Answered: yes.**
5. Confirm reconciliation against Amendment 1 line totals is hard requirement. **Answered: yes.**

---

## Worktree state notes

Before beginning engine-side work:

- Confirm `feature/compliance-engine-extract` is checked out at the main repo
- Confirm worktree is clean (no modifications outside agents/grant-compliance/)
- Confirm origin is in sync with local

Before beginning cockpit-side work:

- Confirm `feature/finance-cockpit` is checked out at the worktree
- Confirm worktree is clean (Compliance Requirements Display Session 1 should be committed and on origin first)
- Confirm origin is in sync with local

Each session ships independently with its own commit.
