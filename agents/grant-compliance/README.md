# Grant Compliance System

A grant-accounting and federal-compliance assistant that sits **on top of QuickBooks**.
It proposes grant tagging for transactions, drafts time & effort certifications,
runs 2 CFR 200 compliance checks, and generates funder-report drafts — always
with a human in the loop and a full audit trail.

> **If you're an AI assistant working on this codebase, read `CLAUDE.md` first.**

## Quickstart

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY if you want real LLM calls.
# Leave LLM_PROVIDER=mock for offline development.

# 3. Initialize the database with seed data
python scripts/init_db.py
python scripts/seed_dev_data.py

# 4. Run the API
uvicorn grant_compliance.main:app --reload

# 5. Open the docs
open http://localhost:8000/docs
```

## What it does

| Agent | Job | Status |
|---|---|---|
| Transaction Classifier | Proposes grant/class tagging for new QB transactions | Skeleton |
| Time & Effort | Drafts monthly certifications for federal grant employees | Skeleton |
| Compliance Monitor | Flags unallowable costs, period violations, budget overruns | Rule engine ready |
| Reporting | Generates SF-425 and foundation report drafts | Skeleton |

## What it deliberately does NOT do

- Post journal entries back to QuickBooks (read-only for now)
- Auto-approve allocations or send reports to funders
- Make allowability determinations via LLM (those are coded rules)

## Architecture

```
QuickBooks Online ──► sync ──► local DB ──► agents ──► human review ──► reports
                                              │
                                              └──► audit_log (append-only)
```

See `CLAUDE.md` for principles and `docs/architecture.md` (TBD) for diagrams.

## Project layout

```
src/grant_compliance/   Application code
tests/                   Pytest suite
scripts/                 One-off scripts (init_db, seed)
alembic/                 DB migrations
```

## Regulatory references

- 2 CFR 200 — Uniform Guidance: https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200
- SF-425 (Federal Financial Report): https://www.grants.gov/forms/sf-424-family
