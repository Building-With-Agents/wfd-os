# CLAUDE.md

> **READ THIS BEFORE WRITING ANY CODE IN THIS REPO.**
> This file gives you the context, rules, and constraints you need to be useful here.
> If a request would violate anything below, push back instead of complying.

---

## What this system is

A grant-accounting and federal-compliance assistant for a small organization that
holds **multiple grants simultaneously** — federal, state, and private foundation —
and uses **QuickBooks** as its system of record. The org currently has ~17 months
left on a federal grant (ends Sept 2026) and needs to (a) operate cleanly until
closeout, (b) reconstruct/document anything weak from the prior 2.5 years, and
(c) be ready for a Single Audit if applicable.

This codebase is **not** a replacement for QuickBooks. QB remains the system of
record for accounting. This system is the layer of reasoning, allocation, and
documentation **on top of** QB that QB doesn't natively do well.

## Regulatory context you must respect

- **2 CFR 200 (Uniform Guidance)** is the primary federal rulebook. Subpart E
  (Cost Principles) §§200.420–200.475 defines allowable / unallowable costs.
  See `src/grant_compliance/compliance/unallowable_costs.py` for the encoded list.
- **Time and effort** documentation is required under §200.430 for any salary
  charged to a federal award. After-the-fact certification, signed by the
  employee or a supervisor with first-hand knowledge.
- **Indirect costs** require either a Negotiated Indirect Cost Rate Agreement
  (NICRA) or use of the 10% de minimis rate (§200.414).
- **Period of performance** matters: costs must be incurred within the grant's
  start and end dates with limited exceptions (§200.309).
- **Single Audit** (§200.500+) is triggered at $750k+ in federal expenditures
  in a fiscal year.

When in doubt, cite the section. Do not invent rules.

## Architecture principles — non-negotiable

1. **Agents propose, humans dispose.** No agent writes back to QuickBooks, sends
   a funder report, or finalizes a time certification without explicit human
   approval recorded in the audit log. Stub-out write paths until a human
   approval workflow is wired in.

2. **Everything is auditable.** Every agent action — input, output, model name
   and version, prompt, timestamp, and the human decision that followed —
   writes to the immutable `audit_log` table. The audit log is append-only;
   never UPDATE or DELETE rows there.

3. **Deterministic where possible, LLM where necessary.** Unallowable-cost
   checks, period-of-performance checks, budget-line overruns, and arithmetic
   are deterministic Python. LLM judgment is only for fuzzy classification
   (e.g., "does this office-supply purchase belong to Grant A or B?") and
   draft generation. Never let an LLM decide whether something is allowable.

4. **Citations are mandatory.** When the Classifier suggests a grant for a
   transaction, it must reference the basis (budget line item, prior similar
   transaction, scope-of-work keyword). When the Compliance Monitor flags an
   issue, it must cite the rule (e.g., "2 CFR 200.421 — advertising").

5. **Reproducibility.** A report generated for Q3 2025 must be reproducible
   from the same DB state months later. This means: snapshot budget versions,
   indirect rate versions, and allocation methodology versions. Reports
   reference the snapshot ID they were generated from.

6. **No silent fallbacks.** If the Classifier confidence is below threshold,
   the transaction goes to a human review queue — it does not get an arbitrary
   default. If the QB sync fails partway, the partial sync is rolled back.

## What lives where

```
src/grant_compliance/
  main.py                 FastAPI entrypoint
  config.py               Settings (pydantic-settings, reads .env)
  db/
    models.py             SQLAlchemy ORM models — the data contract
    session.py            Engine, session, get_db dependency
  audit/
    log.py                AuditLog writer; append-only enforcement
  quickbooks/
    oauth.py              OAuth2 flow (Intuit production + sandbox)
    client.py             Thin REST client over the QB Online API
    sync.py               Pull transactions, accounts, classes, vendors
  integrations/
    msgraph/              Microsoft Graph: Teams, SharePoint, Outlook
      oauth.py            Azure AD / Entra OAuth (delegated + client_credentials)
      client.py           REST client with paging
      evidence.py         EvidenceCollector — pulls audit-relevant items by grant
  agents/
    base.py               Base Agent class — handles LLM call + audit log
    classifier.py         Transaction → grant tagging proposals
    time_effort.py        Time & effort certification drafts
    compliance.py         Rule-runner over transactions; flags issues
    reporting.py          Funder report draft generator
  compliance/
    rules.py              Rule engine (deterministic checks)
    unallowable_costs.py  2 CFR 200 Subpart E encoded
  api/
    routes/               Thin FastAPI route handlers per resource
    schemas.py            Pydantic request/response models
  utils/
    llm.py                Anthropic SDK wrapper with audit hooks
```

## Coding conventions

- Python 3.11+. Type hints everywhere. `from __future__ import annotations`.
- SQLAlchemy 2.0 style (Mapped, mapped_column, select()).
- All database writes go through a service layer, never directly from a route.
- Money is stored as integer cents (BigInteger) — never Float.
- Dates: store as `Date` for accounting periods, `DateTime(timezone=True)` for
  events. Always UTC in the DB; convert at the API boundary.
- Tests use pytest, an in-memory SQLite, and freeze time with `freezegun`.
- Run `ruff check` and `ruff format` before committing.

## Enforced constraints

These are the rules enforced in **code**, not just in documentation. If you
try to violate one, a test will fail or the code will throw at runtime.
They are not policy suggestions — they are structural guardrails designed
to be hard to bypass by accident.

### Alembic autogenerate must be filtered to `grant_compliance` schema only

The `include_name` callback in `alembic/env.py` enforces this. Removing it
would cause autogenerate to produce DROP statements for wfd-os's `public.*`
tables (students, company_scores, prospect_companies, newsletter_issues,
etc.). If one of those DROPs were applied, it would destroy wfd-os's
production schema.

This was a real near-miss during Step 0 — the first autogenerate run,
before the filter was added, produced a migration full of DROPs for every
wfd-os public table. Do not remove, relax, or bypass this filter.

**Mechanism:**
- `alembic/env.py` defines `_include_name(name, type_, parent_names)` that
  returns True only when `type_ == "schema"` is `grant_compliance`. For
  non-schema objects, it returns True (they're included normally, but only
  within our schema because the schema filter is already applied).
- A prominent `# CRITICAL:` comment sits directly above the callback
  explaining what would happen if it's removed.
- The `alembic/MIGRATION_CHECKLIST.md` file requires reviewing every
  autogenerated migration for cross-schema operations before applying.

### QuickBooks is read-only — enforced at the HTTP client layer

`quickbooks/client.py` defines `QbClient`, whose underlying HTTP transport
is a subclass of `httpx.Client` (`_ReadOnlyHttpxClient`) whose `request()`
method raises `NotImplementedError` for any HTTP verb other than GET.

This was deliberately made architectural (not just documentary) because a
mis-posted journal entry into production QB is a compliance incident. It
changes the org's financial records, triggers auditor questions, and may
misreport expenditures to federal funders. Defense in depth over trust in
convention.

**Mechanism:**
- `_ReadOnlyHttpxClient.request()` raises `NotImplementedError` for any
  non-GET method (POST, PUT, PATCH, DELETE, HEAD, OPTIONS). Runtime guard.
- `QbClient.__init__` instantiates `_ReadOnlyHttpxClient` as `self._http`,
  so every QbClient request routes through the guard.
- `QbClient` may not have methods named `create_*`, `update_*`, `delete_*`,
  `post_*`, `put_*`, `patch_*`, `insert_*`, `upsert_*`, or `save_*`. A
  test (`test_qbclient_has_no_write_method_names` in
  `tests/test_quickbooks_readonly.py`) enforces this — if you add a method
  with one of those prefixes, CI fails before the method ships.

**Adding QB write paths in the future requires ALL of the following:**

- (a) Explicit human approval recorded in a design document.
- (b) A separate `qb_writeback` module — do not add write methods to
  `client.py`.
- (c) A **distinct** QuickBooks user with write permissions (NOT the
  read-only user whose tokens `QbClient` holds). That credential lives
  in a separate encrypted store and is loaded only by the `qb_writeback`
  module.
- (d) Its own approval gate and audit log entries for every write.

## Things you should NOT do

- Do not add a code path that posts journal entries to QuickBooks. The
  constraint is now enforced in code (see "Enforced constraints" above) —
  this bullet remains as a reminder that the intent is not merely
  "not yet"; it's "not here, ever." Write-back belongs in `qb_writeback`.
- Same read-only rule applies to Microsoft Graph: do not add code that
  posts to Teams channels, sends mail, or writes to SharePoint until a
  human-approval gate exists. When added, those go in a separate
  `msgraph_writeback` module. **Note**: MS Graph read-only is currently
  enforced only by convention, not by code. If enforcement becomes
  important, mirror the httpx-subclass pattern used for QuickBooks.
- Do not call the Anthropic API directly from a route handler. All LLM calls
  go through `utils/llm.py` so they get logged and rate-limited.
- Do not store API keys or OAuth tokens in plaintext in the DB. Use the
  `cryptography` package (Fernet) and a key from the environment.
- Do not delete or update audit log rows. Ever. If you think you need to,
  you don't — write a compensating row instead.
- Do not encode allowability decisions in prompts. They go in
  `unallowable_costs.py` as code so they can be reviewed and tested.
- Do not assume QB Class == grant. Confirm with the human first; some orgs
  use Class for program, Location for grant, or vice versa.

## Current status

Scaffold only. Nothing is wired to a real QB instance yet. The OAuth flow
is stubbed; the sync writes to the local DB from a fixture file in dev mode.
The agents have working interfaces and prompts but call a mock LLM by default
(set `LLM_PROVIDER=anthropic` in `.env` to use the real API).

Build order (per the original architecture conversation):
1. ✅ Data layer + scaffolding
2. ⬜ QuickBooks OAuth + read-only sync (real)
3. ⬜ Transaction Classifier + human review queue UI
4. ⬜ Compliance Monitor with full rule library
5. ⬜ Reporting Agent for SF-425 + foundation narrative templates
6. ⬜ Time & Effort Agent
7. ✅ Microsoft Graph integration (Teams/SharePoint/Outlook read-only)
8. ⬜ EvidenceCollector → wire bundles to ComplianceFlag/ReportDraft as supporting docs
9. ⬜ SEFA generator (audit-prep priority for June)
10. ⬜ Audit sample documentation pull endpoint
