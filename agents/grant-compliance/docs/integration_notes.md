# Integration Notes — `agents/grant-compliance/`

Status: pre-wfdos-common-merge. This document captures what the module provides
today, what will be replaced by shared infrastructure once Gary's
`wfdos-common` refactor merges, what stays compliance-specific, and the open
questions to resolve before adaptation begins.

## Current state (POC)

The module runs as a standalone FastAPI application on port 8000 against a
QuickBooks **sandbox** tenant, with hand-rolled primitives for authentication,
token storage, OAuth session state, and DB session management. It lives in an
isolated `grant_compliance` Postgres schema (12 tables, zero cross-schema
foreign keys). Tests use an in-memory SQLite with `ATTACH DATABASE … AS
grant_compliance` to emulate the schema. Nothing is wired to production QB,
production Postgres, or any shared auth/session layer yet. The module was
cherry-picked from `integrate/grant-compliance-scaffold` onto
`feature/compliance-engine-extract` without modification — adaptation work has
not started.

## Infrastructure that will come from `wfdos-common` after refactor merges

- **API authentication.** Currently: actor identity is trusted from request
  body fields (`proposer_email`, `decider_email`, `resolver_email`, etc.) with
  no verification, and routes have no auth dependency. Future: `wfdos-common`
  auth middleware; actor derived from the authenticated session, not the body.
- **OAuth token storage.** Currently: access and refresh tokens stored as
  plaintext in `qb_oauth_tokens.access_token` / `.refresh_token` columns.
  Future: Fernet-encrypted at rest via `wfdos-common`'s shared crypto utility
  (keyed from env), matching the pattern the CLAUDE.md already specifies.
- **OAuth CSRF state.** Currently: in-process `dict` in `qb_oauth.py`
  (`_oauth_states`), which breaks under multi-worker uvicorn and is lost on
  restart. Future: proper session store (Redis or DB-backed) from
  `wfdos-common`.
- **Token refresh.** Currently: access-token refresh is a `TODO(Step 1b)` —
  `POST /qb/sync` returns 401 the moment the access token expires (~1 hour)
  and the operator must re-authorize manually through `/qb/connect`. Future:
  shared OAuth client in `wfdos-common` that handles refresh transparently
  for any Intuit- or Microsoft-style OAuth integration.
- **Schema creation in migrations.** Currently: Alembic migrations assume the
  `grant_compliance` schema already exists; there is no `op.execute("CREATE
  SCHEMA IF NOT EXISTS grant_compliance")` in the initial migration, so
  `alembic upgrade head` fails on a fresh Postgres. Future: standardized
  schema-bootstrap pattern from `wfdos-common` (likely a per-module
  convention for pre-migration schema creation).
- **Multi-tenancy.** Currently: single-tenant POC — every table assumes one
  organization. No `tenant_id` column anywhere, no row-level filtering in
  queries, no tenant context in the audit log. Future: `wfdos-common`
  multi-tenant model; adaptation will require adding tenant columns to
  `grants`, `transactions`, `allocations`, `compliance_flags`,
  `time_certifications`, `report_drafts`, `audit_log`, and `qb_oauth_tokens`,
  plus tenant-scoped query helpers.

## What stays compliance-specific (not replaced by `wfdos-common`)

These are the pieces this module owns and will continue to own after the
refactor — `wfdos-common` provides infrastructure, not domain logic.

- The 12 Subpart E rules in
  `src/grant_compliance/compliance/unallowable_costs.py` (advertising,
  alcoholic beverages, bad debts, contingency provisions, entertainment,
  fundraising, fines and penalties, goods/services for personal use, lobbying,
  memberships/dues, selling and marketing of goods/services, trustees). Each
  is a `CostRule` dataclass with citation, summary, trigger keywords, and
  trigger account types. These are policy-as-code and belong here.
- The `QbClient` and `_ReadOnlyHttpxClient` read-only enforcement pattern in
  `src/grant_compliance/quickbooks/client.py`, plus the companion test
  `test_qbclient_has_no_write_method_names` in
  `tests/test_quickbooks_readonly.py`. Intuit's OAuth scope is unavoidably
  read+write; this httpx-subclass guard is the only layer that actually
  prevents writes at runtime, and it stays in this module.
- The detection logic in `src/grant_compliance/compliance/rules.py` — the
  deterministic rule engine that turns transactions into flags. Reads
  `unallowable_costs.py`, period-of-performance data, budget overruns.
- The `ComplianceMonitor` engine in
  `src/grant_compliance/agents/compliance.py` and its `explain_flag` LLM
  helper. Deterministic scanning; the LLM is used only to rephrase an
  already-raised flag into plain language — no allowability decisions are
  delegated to the LLM.
- The `grant_compliance` Postgres schema (12 tables: `grants`, `funders`,
  `employees`, `qb_accounts`, `qb_classes`, `transactions`, `allocations`,
  `time_certifications`, `compliance_flags`, `report_drafts`,
  `qb_oauth_tokens`, `audit_log`) and the Alembic migrations under
  `alembic/versions/`. The schema's isolation from `public.*` is enforced by
  the `include_name` filter in `alembic/env.py` — see CLAUDE.md's "Enforced
  constraints" section for the near-miss history.
- The FastAPI route handlers under `src/grant_compliance/api/routes/`
  (`grants`, `transactions`, `allocations`, `compliance`, `time_effort`,
  `reports`, `qb_oauth`). The business logic in these handlers stays; only
  the auth dependency and actor-derivation middleware change when
  `wfdos-common` lands.

## Finance Cockpit integration dependencies

**TBD, to be filled in with UI design.**

The Audit Readiness tab will consume a subset of the read-side routes listed
in this module's API surface. Specific endpoints, expected latency budgets,
and the choice of polling vs. event-driven updates are deferred until UI
design begins.

## Open questions for Gary (or anyone reviewing the adaptation)

1. **Where does the adaptation happen — this branch or the merge PR?**
   Option A: adapt `feature/compliance-engine-extract` to `wfdos-common` in
   place, then open a single PR against `development` once `wfdos-common`
   lands. Option B: leave this branch as the pristine extraction, and do the
   adaptation in a follow-up branch opened off the merged `wfdos-common`
   work. Option B keeps the "extraction" commit history clean and makes the
   adaptation diff easier to review independently.

2. **Does `grant_compliance` stay as a separate Postgres schema, or get
   migrated into the main wfd-os Postgres under a different schema name?**
   Current choice: separate schema in the same Postgres instance, zero
   cross-schema FKs. This is defensible (isolation from the wfd-os
   application schema that near-miss the DROP migration) but `wfdos-common`
   may standardize on a single-schema-per-module convention with a different
   naming scheme. If the schema name changes, all 12 tables' `__table_args__
   = {"schema": ...}` plus the Alembic env filter must move together.

3. **Does multi-tenant awareness need to be added to `grants`, `allocations`,
   `compliance_flags`, `time_certifications`, `report_drafts`, and
   `audit_log` before the `wfdos-common` refactor merges — or as part of
   the adaptation?** Adding `tenant_id` up front means a schema migration
   that breaks the current single-tenant tests; deferring it means the
   adaptation PR grows. The call also depends on whether `wfdos-common`
   expects tenant identity to propagate via a session context variable or
   explicit query parameter.
