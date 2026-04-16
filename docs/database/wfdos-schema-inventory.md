# wfd-os schema inventory

**Purpose:** catalog every Postgres table referenced by wfd-os service code. This is input for designing the canonical schema — not the schema itself. Tables listed here are what the code **expects** to exist; they may or may not be defined anywhere today.

**Status:** Survey only. Column shapes are not fully enumerated; gap analysis against the real Azure `talent_finder` DB (which has JIE `dbo.*` tables but no wfd-os `public.*` tables) is open work.

**How it was built:** Python regex sweep of all `agents/*.py`, `agents/**/*.py`, `scripts/*.py` for SQL strings (triple-quoted + long single-quoted), extracting table names from `SELECT ... FROM`, `JOIN`, `INSERT INTO`, `UPDATE`, `DELETE FROM`, `CREATE TABLE`, `ALTER TABLE`. CTEs filtered out. False-positive SQL-keywords (`set`, `inquiry`, `posted`, `student`) also filtered. See `scripts/scan-schema.py` (future tool) to regenerate.

**Next step** (when Gary has bandwidth): for each table, define the canonical column set. Source priorities:

1. INSERT column lists in the code (most explicit — what the code writes).
2. SELECT column references (what the code reads).
3. Dynamics CRM field shape for `students`, `colleges`, etc. (if migration tagging applies).
4. Migrated data from `pg_dump`s if Gary has them.

---

## Inventory (34 tables)

Grouped by functional domain for easier mental model. Each entry lists: which services read/write it, operations, representative files.

### Students + career services

| Table | Ops | Files | Notes |
|---|---|---|---|
| `students` | SELECT, INSERT, UPDATE, JOIN | 13 files — `agents/portal/{student,showcase,college,wji}_api.py`, `agents/assistant/employer_agent.py`, `agents/career-services/gap_analysis.py`, `agents/profile/parse_resumes.py`, `scripts/002-migrate-dataverse.py` | Master student record. Written by Profile Agent (resume parse) + Dataverse migration. Read by every portal + assistant. |
| `student_skills` | SELECT, INSERT, JOIN | 9 files — same portals + assistants + career-services | Junction to `skills`. Duplicate skill-lookup queries in `student_api.py` and `showcase_api.py` (noted in #22). |
| `student_education` | SELECT | `agents/portal/showcase_api.py` | One row per school attended. |
| `student_work_experience` | SELECT, INSERT | `agents/portal/showcase_api.py`, `agents/profile/parse_resumes.py` | Written by resume parse. |
| `student_journeys` | SELECT, INSERT | `agents/portal/student_api.py`, `scripts/002-migrate-dataverse.py` | Stage-by-stage journey tracking (per CLAUDE.md — intake → assessment → training → ojt → showcase → placement). |
| `gap_analyses` | SELECT, INSERT, DELETE | 5 files — `agents/career-services/gap_analysis.py`, `agents/portal/{student,showcase,college}_api.py` | Output of the skill-gap calculation. |
| `career_pathway_assessments` | INSERT | `scripts/005-migrate-bacpac-reference.py` | Migrated from legacy SQL BACPAC. |

### Skills + reference data

| Table | Ops | Files | Notes |
|---|---|---|---|
| `skills` | SELECT, JOIN | 9 files — most portal APIs, `agents/market-intelligence/tools/semantic_skills.py`, `agents/college-pipeline/map_programs_to_skills.py` | Shared skill taxonomy. `embedding_vector` column referenced (pgvector). |
| `cip_codes` | SELECT, INSERT, DELETE | `scripts/005*-migrate-bacpac-reference.py`, `scripts/005b-parse-cip-soc-bcp.py`, `scripts/005c-fix-cip-soc.py` | Classification of Instructional Programs (CIP). Reference data. |
| `soc_codes` | SELECT, INSERT, DELETE | same 3 scripts as `cip_codes` | Standard Occupational Classification (SOC). Reference data. |

### Colleges + programs

| Table | Ops | Files | Notes |
|---|---|---|---|
| `colleges` | INSERT | `scripts/005-migrate-bacpac-reference.py` | Institutions. Migrated from BACPAC. |
| `college_partners` | SELECT | `agents/portal/college_api.py` | Subset of `colleges`? Or distinct table for the College Partner Portal (#16). |
| `college_programs` | SELECT, INSERT, JOIN | `agents/college-pipeline/map_programs_to_skills.py`, `scripts/002-migrate-dataverse.py` | Program offerings per college. |
| `program_skills` | SELECT, INSERT, DELETE | `agents/college-pipeline/map_programs_to_skills.py` | Junction: programs → skills mapping. |

### Employers + jobs

| Table | Ops | Files | Notes |
|---|---|---|---|
| `employers` | SELECT, INSERT | `agents/portal/student_api.py`, `agents/reporting/api.py`, `scripts/002-migrate-dataverse.py` | Employer master record. `(SELECT count(*) FROM employers) as total_employers` in reporting. |
| `job_listings` | SELECT, INSERT, UPDATE, JOIN | 11 files — reaches into `agents/assistant/student_agent.py`, `agents/career-services/gap_analysis.py`, `agents/market-intelligence/ingest/*` | Consumed by JIE pipeline + wfd-os assistants. **Candidate for JIE API boundary** (#17, JIE#160) — wfd-os should read this via HTTP client, not DB. |

### Consulting pipeline (engagements)

| Table | Ops | Files | Notes |
|---|---|---|---|
| `project_inquiries` | SELECT, INSERT, UPDATE, DELETE | `agents/apollo/api.py`, `agents/portal/consulting_api.py` | Inbound consulting prospects. Apollo CRM webhooks write; consulting-api reads + updates. |
| `consulting_engagements` | SELECT, INSERT, UPDATE | `agents/portal/consulting_api.py` | Converted project_inquiries → engagement. |
| `engagement_team` | SELECT | `agents/portal/consulting_api.py` | Who's on the engagement (staff + apprentices). |
| `engagement_milestones` | SELECT | `agents/portal/consulting_api.py` | Phase markers. |
| `engagement_deliverables` | SELECT | `agents/portal/consulting_api.py` | What's being produced. |
| `engagement_updates` | SELECT, INSERT | `agents/portal/consulting_api.py` | Client-facing update log (posted to SharePoint + Teams). |

### Marketing + apollo

| Table | Ops | Files | Notes |
|---|---|---|---|
| `marketing_content` | SELECT, INSERT, UPDATE | `agents/marketing/api.py` | Content lifecycle (draft → published). |
| `apollo_webhook_events` | SELECT, INSERT, UPDATE | `agents/apollo/api.py` | Inbound webhooks from Apollo CRM. |

### Workforce Justice Initiative (WJI — grant reporting)

| Table | Ops | Files | Notes |
|---|---|---|---|
| `wji_placements` | SELECT, INSERT | `agents/portal/wji_api.py` | WSAC placement reports. |
| `wji_payments` | SELECT, INSERT | `agents/portal/wji_api.py` | QuickBooks payment reconciliation. |
| `wji_upload_batches` | SELECT, INSERT, UPDATE, DELETE | `agents/portal/wji_api.py` | Upload-job tracking (SharePoint file ingestion). |

### Agent runtime

| Table | Ops | Files | Notes |
|---|---|---|---|
| `agent_conversations` | SELECT, INSERT | `agents/assistant/base.py` | Chat session persistence for the 6 assistants. Upserted via `ON CONFLICT (session_id) DO UPDATE`. **Candidate for refactor** (#26 — session persistence moves to `wfdos_common.db`). |
| `audit_log` | CREATE TABLE | `agents/market-intelligence/ingest/` | Pipeline audit entries. |
| `pipeline_metrics` | CREATE TABLE | `agents/market-intelligence/ingest/` | Pipeline run metrics. |

---

## Gaps + observations

- **30+ tables, no published schema.** No `migrations/` directory, no Alembic, no SQL file of `CREATE TABLE` definitions. Schema lives implicitly in whatever local DB Gary has wfd-os pointed at.
- **Schema-to-code drift is invisible.** Columns referenced in SQL are the only "spec". A rename or drop breaks services silently.
- **Cross-table assumptions:** several JOINs imply foreign-key shapes (`student_skills.skill_id → skills.id`, `student_skills.student_id → students.id`, `college_programs.college_id → colleges.id`, etc.). None of these are verified by the code — they assume the schema is set up correctly externally.
- **`job_listings`:** the 11-file usage is the largest fan-in. Per the product-architecture decision (2026-04-14 Decision 5), this should be consumed via JIE's HTTP API (JIE#160), not via direct DB reads. Until that lands, it's a shared-DB coupling.
- **JIE mirror mismatch:** Azure `talent_finder` on `pg-jobintel-cfa-dev` contains only JIE's `dbo.*` schema. None of the 30 wfd-os tables above exist there. Gary runs wfd-os against a separate DB that isn't shared. That's the DB this inventory is trying to help formalize.

---

## Local dev DB setup

See `docker-compose.dev.yml` at repo root:

```bash
docker-compose -f docker-compose.dev.yml up -d
```

Brings up a dedicated `wfdos-postgres` container:

- Image: `pgvector/pgvector:pg16` (matches JIE for consistency + supports `skills.embedding_vector`)
- Port: **5434** (5432 = JIE mirror, 5433 = langfuse-db — both already in use on Gary's machine)
- User: `wfdos`
- Password: `wfdos_local_dev` (local-dev literal; NOT a secret to protect)
- Database: `wfdos`
- `vector` extension auto-enabled via init script

`.env` for local dev against this container:

```
PG_HOST=localhost
PG_PORT=5434
PG_USER=wfdos
PG_PASSWORD=wfdos_local_dev
PG_DATABASE=wfdos
DATABASE_URL=postgresql://wfdos:wfdos_local_dev@localhost:5434/wfdos
```

---

## Related issues

- **#22** — multi-tenant SQLAlchemy engine factory in `wfdos_common.db`. The engine factory will need to know the schema shape formalized here.
- **#17** — JIE integration boundary. `job_listings` moves from shared-DB coupling to HTTP API once JIE#160 ships.
- **#16** — white-label runtime config. Per-client DBs each have this schema.
- **#26** — Agent ABC. `agent_conversations` session persistence moves out of `agents/assistant/base.py` into `wfdos_common.db`.

---

## What still needs to happen (open)

1. **Full column survey per table.** This doc lists tables only. Column lists per `INSERT` / `SELECT` haven't been normalized.
2. **Define the canonical schema.** Decide on the columns + types + constraints + indexes per table. Single source of truth (migrations directory or SQL file in this repo).
3. **Reconcile against real data.** Dump the real wfd-os-data DB (wherever Gary has it), compare to this inventory, note drift.
4. **Bootstrap the local dev DB.** Once the canonical schema is defined, add a seed / init script so `docker-compose up` gives a dev a usable DB.

Tracked in a new follow-up issue (opened alongside this doc's PR).
