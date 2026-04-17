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

## Things you should NOT do

- Do not add a code path that posts journal entries to QuickBooks. Read-only
  for now. When write-back is added later, it goes through a separate
  `qb_writeback` module with its own approval gate.
- Same rule applies to Microsoft Graph: read-only. Do not add code that posts
  to Teams channels, sends mail, or writes to SharePoint until a human-approval
  gate exists. When added, those go in a separate `msgraph_writeback` module.
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
