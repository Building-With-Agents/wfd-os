# JIE ↔ wfd-os Postgres reconciliation

**Status:** TODO — blocks running wfd-os end-to-end against the JIE Postgres
on `localhost:5432` (Gary's source-of-truth dev DB). Captured 2026-04-20
during the phase-5 live smoke.

## TL;DR

Gary wants a **single** local Postgres (JIE's `postgres-server` container,
port 5432) to host **both** JIE's `dbo.*` schema and wfd-os's `public.*`
schema. They don't collide at the SQL layer (different Postgres schemas),
but:

1. **Port 3000 conflict** — JIE's `langfuse-server` container binds
   `localhost:3000`, which is the port wfd-os's Next.js portal
   (`portal/student`) also wants.
2. **wfd-os schema isn't loaded** into JIE's `postgres-server` —
   wfd-os's `docker/postgres-init/*.sql` only runs on an *empty* Postgres
   data volume. JIE's volume already has data, so the init scripts are
   skipped.
3. Several wfd-os tables **semantically overlap** with JIE's `dbo.*`
   tables (students vs. jobseekers, skills vs. skills, employers vs.
   employers). Reconciling those is a column-level design call, not a
   merge — see the mapping below.

## Port 3000 conflict

### Current state

```text
$ docker ps --format '{{.Names}}\t{{.Ports}}'
langfuse-server  0.0.0.0:3000->3000/tcp, [::]:3000->3000/tcp
postgres-server  0.0.0.0:5432->5432/tcp, [::]:5432->5432/tcp
langfuse-db      0.0.0.0:5433->5432/tcp
redis-server     0.0.0.0:6379->6379/tcp
...
```

`langfuse-server` is holding `:3000`. wfd-os portal `next dev` auto-
increments when 3000 is taken, which on Gary's box landed on `:6000`
(Next.js rejects — reserved for X11) and crashed the portal:

```
Bad port: "6000" is reserved for x11
portal.1 stopped (rc=1)
```

### Fix (in JIE, not wfd-os)

The `watechcoalition/docker-compose.yml` service `langfuse` at
`job-intelligence-engine/docker-compose.yml:162-163` already parameterizes:

```yaml
ports:
  - "${LANGFUSE_PORT:-3000}:3000"
```

Action: set `LANGFUSE_PORT=3030` (or any unused port — `3030` matches the
existing internal `langfuse-worker` health port) in JIE's `.env`, then:

```bash
cd ../job-intelligence-engine
docker compose up -d langfuse
```

Also update:

- `NEXTAUTH_URL` in that service (line 166) — auto-derived from
  `${LANGFUSE_PORT:-3000}` so no yaml edit needed, just restart.
- Any docs / shortcuts pointing at `http://localhost:3000` for Langfuse.

**Do NOT** change the wfd-os portal port. The `settings.platform.portal_base_url`
default + every CORS allowlist + the magic-link email link all assume
`http://localhost:3000`. Keeping that fixed is cheaper than changing every
reference.

## Schema reconciliation

### No namespace collision

- JIE schema: `dbo.*` (explicit Postgres schema named `dbo`, from the
  legacy SQL Server migration)
- wfd-os schema: `public.*` (default Postgres schema)

Both can coexist in the same database — `SELECT * FROM dbo.jobseekers`
and `SELECT * FROM students` address different tables.

### wfd-os schema must be loaded manually

wfd-os's `docker/postgres-init/10-schema.sql` runs only on a fresh
Postgres data volume (Docker's `initdb.d` contract). JIE's
`postgres-server` volume (`postgres_data`) already has JIE's data from
prior boots, so that hook never fires.

**Action:** run the wfd-os schema against JIE's postgres-server once:

```bash
# From wfd-os repo root, with JIE's postgres-server up:
docker exec -i postgres-server psql \
  -U "${POSTGRES_USER:-postgres}" \
  -d "${POSTGRES_DB:-talent_finder}" \
  < docker/postgres-init/00-extensions.sql

docker exec -i postgres-server psql \
  -U "${POSTGRES_USER:-postgres}" \
  -d "${POSTGRES_DB:-talent_finder}" \
  < docker/postgres-init/10-schema.sql
```

Verify: `\dt public.*` should list the 35 wfd-os tables; `\dt dbo.*`
should still list the JIE tables untouched.

**Then** update wfd-os `.env` to:

```bash
PG_HOST=localhost
PG_PORT=5432
PG_USER=postgres          # whatever JIE's postgres-server uses
PG_PASSWORD=<JIE's POSTGRES_PASSWORD>
PG_DATABASE=talent_finder # JIE's POSTGRES_DB (not wfdos)
```

### Tables wfd-os needs (36 total in `public`)

#### A. Entirely new to JIE — no dbo equivalent

These are wfd-os's own product concepts; JIE has nothing comparable. They
just need to be created in `public.*`:

- `agent_conversations` — conversational-agent session memory
- `apollo_webhook_events` — Apollo.io lead-signal inbox
- `audit_log` — generic audit trail (not JIE's `_prisma_migrations`)
- `career_pathway_assessments`
- `career_services_interactions`
- `college_partners`
- `college_programs`
- `colleges`
- `consulting_engagements` — Waifinder client delivery
- `engagement_deliverables` — Waifinder
- `engagement_milestones` — Waifinder
- `engagement_team` — Waifinder
- `engagement_updates` — Waifinder
- `gap_analyses` — skills-gap output
- `marketing_content`
- `pipeline_metrics`
- `program_skills`
- `project_inquiries` — consulting intake
- `qa_feedback` — LaborPulse thumbs-up/down
- `student_journeys` — the 7-stage journey model
- `wji_payments` — WJI/WSAC grant
- `wji_placements` — WJI/WSAC grant
- `wji_upload_batches` — WJI/WSAC grant

#### B. Overlapping name or concept with a JIE `dbo.*` table

These may want column-level alignment. Until that design call is made,
wfd-os's `public.*` copy coexists with JIE's `dbo.*`:

| wfd-os `public.*`            | JIE `dbo.*`                          | Notes |
|------------------------------|--------------------------------------|-------|
| `students`                   | `jobseekers`                         | Different lifecycle (CFA training vs. open jobseeker pool). Keep both for now. |
| `student_skills`             | `jobseeker_has_skills`               | Same shape, different table name. |
| `student_education`          | `jobseekers_education`               | Same shape. |
| `student_work_experience`    | `work_experiences`                   | Similar. |
| `skills`                     | `skills`                             | JIE's is schema-qualified `dbo.skills`; wfd-os's is `public.skills`. Collision-free but *two sources of truth* — flag for alignment. |
| `employers`                  | `employers`                          | Same — two sources. |
| `job_listings`               | `job_postings`                       | Different names, same concept. |
| `job_listing_skills`         | `_jobpostingskills`                  | Same. |
| `job_roles`                  | `jobrole`                            | Same. |
| `job_role_skills`            | `jobroleskill`                       | Same. |
| `cip_codes`                  | `cip`                                | CIP taxonomy. |
| `soc_codes`                  | `socc`, `socc_2010`, `socc_2018`     | JIE tracks multiple SOC vintages. |
| `cip_soc_crosswalk`          | `cip_to_socc_map`, `socc2018_to_cip2020_map` | Different directions. |

#### C. JIE-only tables wfd-os never touches

Leave as-is in `dbo.*`. Includes:
`_prisma_migrations`, `account`, `authenticator`, `session`,
`verificationtoken`, Langfuse-like auth tables, plus all the pipeline
audit tables from `~/.claude/CLAUDE.md` (`raw_ingested_jobs`,
`job_ingestion_runs`, `normalized_jobs`, `normalization_quarantine`,
`extracted_intelligence`, `llm_audit_log`) — **never touch, never drop,
per Gary's global CLAUDE.md protection rule**.

(Note: the pipeline-audit tables aren't in the committed schema.sql —
they live in JIE's Alembic / prisma migrations and may not show up in
`dbo.*`. Verify with `\dt` before planning any reconciliation.)

## Open questions — deferred design calls

1. **Shared `skills` and `employers`?** Two sources of truth is the
   current state; aligning means picking one schema and migrating the
   other. Large change; park until after Phase 5 merge.
2. **Students ↔ jobseekers promotion?** A CFA student who graduates
   might become a jobseeker in JIE's world. Is `dbo.jobseekers` the
   public-facing talent showcase, with `students` as the in-training
   subset? Needs product input from Ritu.
3. **CIP / SOC taxonomy**: keep two copies (one per system) or pick one
   canonical location? JIE has more SOC vintages; wfd-os's schema
   assumes a single version. If merged, wfd-os agents need to handle
   the vintage dimension.

## Phase-5 smoke impact

Until the steps above are done, two live smoke sections can't run
against this local Postgres:

- §3b (not-found envelope) — queries `students` table, which doesn't
  exist in JIE's `dbo.*` or in wfd-os's `public.*` yet.
- §13e (qa_feedback insert) — requires `public.qa_feedback`.

The rest of the phase-5 smoke is DB-independent and passes without this
work (see `docs/refactor/phase-5-exit-report.md`).

## Recommendation — flatten JIE `dbo.*` → `public.*` *first*

The `dbo.*` schema in JIE is a legacy artifact from the MS SQL Server
migration, not a deliberate design. Flattening to `public.*` before
running this reconciliation simplifies the end-state: one Postgres,
one schema, no namespace bookkeeping.

### Mechanically easy

- `ALTER TABLE dbo.foo SET SCHEMA public;` per table — metadata-only
  DDL, no data copy, preserves FKs / indexes / sequences. 72 tables ×
  seconds each = couple minutes of SQL.

### Code sweep — moderate

- `grep -r "dbo\." job-intelligence-engine/` — every raw SQL string,
  SQLAlchemy model `__table_args__`, Prisma `@@schema("dbo")`, Alembic
  migration, fixture export. Probably 50–200 refs; 2–3 hours of
  careful find/replace + review.
- Prisma codegen is the most likely footgun — regenerate client after
  removing `@@schema("dbo")`.

### The real blocker — name collisions with wfd-os

Once JIE is `public.*`, these can't coexist as-is:

| JIE (after flatten)  | wfd-os `public.*` | Collision type                              |
|----------------------|-------------------|---------------------------------------------|
| `skills`             | `skills`          | Same name — maybe different columns         |
| `employers`          | `employers`       | Same                                        |
| `job_postings`       | `job_listings`    | Different names, same concept               |
| `jobseekers`         | `students`        | Different names, overlapping concept        |

Flattening **forces the "which schema wins" design call** this doc
defers. Don't flatten without resolving the four rows above.

### Before flatten-day

1. **Export fixtures first** — non-negotiable per `~/.claude/CLAUDE.md`
   "Job Intelligence Engine — Database Protection Rules":
   ```bash
   python scripts/pg-seed-data/export_fixtures.py --scope all
   ```
2. Resolve the 4 name collisions (column-by-column diff, pick a
   canonical source or rename).
3. Test the flatten + code sweep on a fixture-seeded staging copy
   before touching Gary's dev DB.

### Estimated effort

- **1 day** if the 4 collisions are already resolved and fixtures
  exported.
- **3–5 days** if the product calls need Ritu's input (jobseekers ↔
  students lifecycle in particular).

### Post-flatten, this doc collapses to

"Copy the 23 wfd-os-only tables (Section A above) into JIE's Postgres
`public.*`, point `PG_HOST=localhost:5432`, re-run phase-5 §3b + §13e."

### Scope note

**Do this as a standalone JIE PR, not inside Phase 5.** The stacked-
branch exit gate is about wfd-os refactor acceptance; a JIE schema
migration is its own blast radius with its own rollback path. Merging
them conflates reviews.

## Related

- `docker-compose.dev.yml` — wfd-os's *own* Postgres container (port
  5434, `wfdos` user, `wfdos` DB). Used as a **fallback** when JIE's
  stack isn't up. Superseded by this reconciliation once the
  one-Postgres plan ships.
- `docs/database/wfdos-schema-inventory.md` — per-table inventory with
  status and owning agent.
- `~/.claude/CLAUDE.md` — "Job Intelligence Engine — Database
  Protection Rules" (no truncate / no destructive ops on JIE audit
  tables).
