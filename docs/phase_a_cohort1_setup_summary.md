# Phase A — Cohort 1 Data Setup Summary

*Date: April 20, 2026*
*Owner: Ritu Bahl + Claude Code (Opus 4.7)*
*Working branch: `feature/finance-cockpit` (worktree: `C:\Users\ritub\Projects\wfd-os\.claude\worktrees\stupefied-tharp-41af25`)*
*Scope: Phase A only — multi-tenant schema scaffolding + Cohort 1 apprentice ingestion + WSB El Paso job pool ingestion + verification. Phase B (matching, gap analysis, narratives) is deferred.*

## Headline

Phase A is complete and clean. The `wfd_os` database now has two named tenants (CFA as the origin tenant, WSB for Workforce Solutions Borderplex), with CFA's existing data intact and WSB populated with the Cohort 1 apprentices + El Paso tech job pool needed for Phase B matching.

| Artifact | Count | State |
|---|---:|---|
| Tenants seeded | 2 | CFA + WSB |
| CFA data (preserved, pre-Phase-A baselines) | 4,727 students · 103 jobs_enriched · 3 applications · 30 gap_analyses · 0 match_narratives | unchanged |
| WSB apprentices (Cohort 1) | **9** | all HIGH-confidence parsed |
| WSB jobs (El Paso tech pool) | **40** | all filtered + deduped |
| Supporting WSB rows | 136 student_skills · 26 student_work_experience · 40 jobs_raw | consistent |
| NULL `tenant_id` rows anywhere | 0 | NOT NULL enforced |
| Pre-existing files modified | 0 | read-only on app code |
| Branches pushed to remote | 0 | all local commits |

Three commits landed on `feature/finance-cockpit` (all local, unpushed):

1. `3b65d8a` — `feat(cohort): ingest 9 Cohort 1 apprentice resumes from SharePoint with WSB tenant tagging`
2. `013c048` — `feat(schema): add tenants table and tenant_id columns for multi-tenant data separation`
3. `0a98a84` — `feat(cohort): ingest El Paso tech jobs for WSB tenant via JSearch`

---

## Task 1 — Multi-tenancy seed

**Migration:** `scripts/014-tenants-seed.sql` (applied; committed as `013c048`).

Created table:

```
tenants (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        TEXT UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
)
```

Seeded:
- **CFA** `85a1557e-25e0-4461-bb6b-fa2067a6fafe` — *Computing for All* (origin customer)
- **WSB** `2be4a5fc-d1cd-40dd-842d-714664fb1c6f` — *Workforce Solutions Borderplex* (Cohort 1 funder)

Added `tenant_id UUID REFERENCES tenants(id)` to **five** tables per spec:
- `students`, `jobs_enriched`, `applications`, `gap_analyses`, `match_narratives`

All 4,860 existing rows backfilled to CFA. Column then made `NOT NULL`. Indexed as `idx_<table>_tenant`.

**Decisions made:**
- Lightest-viable scope: only the 5 tables specified got `tenant_id`. Other tenant-adjacent tables (`employers`, `consulting_engagements`, BD/marketing stack, `wji_*`, etc.) were flagged in the Task 1 report but left untouched for a later multi-tenancy pass.
- `jobs_raw` was **not** given `tenant_id` — Ritu's original spec didn't list it, and `jobs_raw.deployment_id` already provides per-tenant partitioning there. A future `scripts/015-tenant-id-jobs-raw.sql` is possible but was not created.
- UUID IDs chosen for `tenants` to match the existing UUID convention on `students`, `applications`, `gap_analyses`, `match_narratives`.

**Verification:** All 5 tables accept new rows only if `tenant_id` is specified (confirmed by intentional NULL-insert + bogus-UUID-insert test; both rejected).

---

## Task 2 — Cohort 1 apprentice ingestion

**Scripts:** `scripts/phase_a_fetch_sharepoint_resumes.py` + `scripts/phase_a_parse_cohort1_resumes.py` (both committed as `3b65d8a`).

**Source:** SharePoint at `https://computinforall.sharepoint.com/sites/cfatechsectorleadership`, folder `UTEP & Borderplex/Feb 23rd 2026 Cohort Resumes`. Existing `GRAPH_*` credentials authenticated cleanly.

**Files fetched:** 9 PDFs downloaded to `data/cohort1_resumes/` (gitignored — PII).

**Parse approach:** Decision (b) per Ritu — bypass Azure Blob Storage; parse local PDFs directly. Uses the same `EXTRACTION_PROMPT` verbatim as `agents/profile/parse_resumes.py` (Gemini 2.5 Flash with PDF `inline_data`) so Cohort 1 records have the same extraction shape as legacy Dataverse-migrated records.

**Results:**

| # | Name | Confidence | Skills | Work entries | Source file |
|---|---|---:|---:|---:|---|
| 1 | Angel Coronel | 1.0 | 35 | 5 | `Angel Coronel Res FT SWE.pdf` |
| 2 | Bryan Perez | 1.0 | 70 | 2 | `Bryan Resume 2025.pdf` |
| 3 | EMILIO ANTONIO BRIONES | 0.9 | 33 | 4 | `Emilio Antonio Briones.pdf` |
| 4 | Enrique Calleros | 1.0 | 42 | 3 | `Enrique Calleros Resume (6) (1).pdf` |
| 5 | Fabian Ornelas | 1.0 | 41 | 2 | `Fabian_Ornelas_Resume_2025.pdf` |
| 6 | FATIMA BARRON | 1.0 | 90 | 3 | `Fatima Barron.pdf` |
| 7 | Juan Reyes | 1.0 | 73 | 3 | `Juan Reyes.pdf` |
| 8 | Nestor Escobedo | 0.9 | 28 | 1 | `Nestor Escobedo.pdf` |
| 9 | Ricardo Acosta Arambula | 1.0 | 16 | 3 | `Ricardo Acosta Arambula - Student resume.pdf` |

All 9 inserted as new `students` rows with:
- `tenant_id` = WSB
- `cohort_id` = `cohort-1-feb-2026`
- `source_system` = `cohort-1-sharepoint-2026-02-23`
- `resume_parsed` = TRUE
- `showcase_active` = FALSE (per spec — not in showcase until quality verified)
- `pipeline_status` = `enrolled`
- `data_quality` derived from confidence (`complete` for all 9)
- Skills matched against the existing taxonomy: 136 rows inserted into `student_skills`
- Work history: 26 rows into `student_work_experience`
- Local resume path recorded in `legacy_data.resume_local_path` (not in `resume_blob_path`, since files are not in blob storage)

**Flags raised for Ritu's spot-check:**

1. **9 apprentices, not 8.** `CLAUDE.md` lists Cohort 1 as 8 people; SharePoint had 9. Ritu kept all 9; Ricardo Acosta Arambula pending Alma/Gary confirmation.
2. **Angel Coronel's location = "New York, NY" + PhD CUNY (2028)** per resume extraction. Phone is El Paso (915). Ritu to review resume separately.
3. **Fatima Barron's education = M.S. Cybersecurity, Georgia Tech.** Phone is El Paso (915). Likely GaTech online program. Ritu to review.
4. **Names in all-caps** for Emilio and Fatima (resume header artifacts). No normalization applied per Ritu's instruction ("data accurately reflects what's on the resumes").
5. **Missing location** for Enrique, Fabian, Nestor — Gemini was conservative; UTEP emails imply El Paso. No default-populated.

All preserved in DB as parsed.

**Decisions made:**
- Local-file parser bypasses `link_resumes.py` (which matches by Dataverse `original_record_id`) and `parse_resumes.py`'s blob-download flow. New apprentices don't have Dataverse provenance, so linking-by-contactid doesn't apply.
- Per Ritu's call, PDFs are **gitignored** (PII); digest JSON (`data/cohort1_ingestion_digest.json`) also gitignored for consistency.

---

## Task 3 — El Paso tech job ingestion (JSearch)

**Script:** `scripts/phase_a_ingest_elpaso_jobs.py` (committed as `0a98a84`). Reuses `agents/market-intelligence/ingest/jsearch.py`'s API shape without modifying it; does its own tenant-aware inserts into `jobs_enriched` + `jobs_raw`.

**Why a new script rather than reusing `runner.py`:** the existing `runner.py` inserts into `job_listings` (Vegas-era table). The Phase A spec targets `jobs_enriched` (post-migration-013 with structured location columns). Both tables coexist for now — no cleanup attempted.

**Queries run** (6 queries, each with `num_pages=1`, `date_posted=month`):
1. `software developer in El Paso, TX`
2. `data analyst in El Paso, TX`
3. `IT support in El Paso, TX`
4. `AI engineer in El Paso, TX`
5. `web developer in El Paso, TX`
6. `information technology in El Paso, TX`

**Filter rules applied** (post-adjustment):
- **Location:** job must be in El Paso (regex match on city/state/country/description) OR in the Borderplex-metro city list (El Paso County TX + Doña Ana County NM). Remote jobs are kept only if their description explicitly mentions El Paso.
- **Security clearance:** reject if description or highlights match patterns like `active clearance`, `top secret`, `TS/SCI`, `secret clearance`, `DoD clearance`.
- **Senior experience:** reject if structured `required_experience_in_months >= 120` OR description mentions "10+ years of experience" (and similar patterns).
- **Senior leadership titles:** reject if title matches `^|\b(Head of|Director of|VP |Chief |Principal )`. Added per Ritu's post-first-run instruction.

**Deduplication:**
- In-run: hash of normalized (title, company, location) + JSearch's own `job_id`.
- DB-level: skip insert if `(deployment_id, job_id)` already exists in `jobs_enriched`.

**First run (pre-adjustment):** 56 fetched, 52 after in-run dedup, 40 inserted, 12 rejected (8 clearance, 1 senior 10+ yrs, 3 non-El-Paso metro: Canutillo TX, Chamberino NM, Clint TX).

**Adjustment pass (`--reconcile` flag):**
- **DELETEd 2 rows:** `Head of Information Technology` and `Head of Information Technology Architecture` (both @ Confidential). Both failed the new senior-leadership-title rule.
- **Re-fetched all 6 queries** from JSearch (into disk cache so future adjustments cost zero API calls). **Inserted 2 new jobs** that passed the relaxed Borderplex filter:
  - `#144 Data Insights Analyst - Dashboards & Growth @ SONIMUS LLC` (El Paso, TX)
  - `#145 Tier 1 Technical Support Specialist @ Excellent Networks Inc` (El Paso, TX)

**Deviation to flag:** Ritu's adjustment message assumed "cached raw data" and expected the 3 specific Borderplex-metro jobs (Canutillo, Chamberino, Clint) to come back. Two issues:
1. **No cache existed** for the first run (raw payloads were discarded after filtering). Re-fetching was necessary. Cost: 6 API calls (now ~32 remaining on JSearch free tier).
2. **The 3 specific Borderplex-metro jobs dropped off JSearch's current-month window** between the first fetch and the reconcile. Fresh fetch yielded 2 new El Paso-proper jobs instead (SONIMUS + Excellent Networks).

Net effect: **40 jobs final**, not the ~41 Ritu projected. Different composition (+2 new El Paso-proper tech roles instead of +3 Borderplex-metro civilian-IT roles), same net count as the original first run.

**Caching added:** Raw JSearch payloads now written to `data/cohort1_jobs_raw_cache/<query>.json` on every fetch. Future filter adjustments honor the cache (zero API cost) unless `--refresh-cache` is passed. 6 cache files produced: `software_developer.json`, `data_analyst.json`, `it_support.json`, `ai_engineer.json`, `web_developer.json`, `information_technology.json`. Total 52 unique raw jobs across them. Cache dir is gitignored.

**Final WSB job pool (40):** 30 Full-time, 6 Contractor, 2 Full-time+part-time, 1 mixed, 1 unclassified. 1 fully-remote (GD IT bilingual customer support, explicitly El-Paso-relevant per description). All Texas except that remote one which has null state. Zero senior-title residuals. Representative sample:

| # | Title | Company | Location |
|---|---|---|---|
| #104 | Software Developer II | CITY OF EL PASO, TX | El Paso, Texas |
| #105 | Software Developer II - C#.NET & SQL Specialist | City of El Paso | El Paso, Texas |
| #106 | C++ - Software Engineer, AI | G2i Inc. | El Paso, Texas |
| #107 | Ruby - Software Engineer, AI | G2i Inc. | El Paso, Texas |
| #108 | Flexible Hours: Software Engineer Staff-El Paso | Walmart | El Paso, Texas |
| #137 | Software Engineer, Backend/Full Stack | Quest Diagnostics | El Paso, Texas |
| #138 | React Developer (Entry Level) | Outcoder iO | El Paso, Texas |
| #134 | Remote Analytics Engineer & AI Trainer | DataAnnotation | El Paso, Texas |
| #144 | Data Insights Analyst - Dashboards & Growth | SONIMUS LLC | El Paso, Texas |
| #145 | Tier 1 Technical Support Specialist | Excellent Networks Inc | El Paso, Texas |

Full digest: `data/cohort1_jobs_ingestion_digest.json` (gitignored).

**Decisions made:**
- `deployment_id = 'wsb-elpaso-cohort1'` on all WSB jobs (parallel to existing `cfa-seattle-bd`, `waifinder-national`).
- `region = 'El Paso, TX'`.
- Inserted into both `jobs_raw` (full payload preserved for re-enrichment) and `jobs_enriched` (structured view for matching).
- `source` indicator on `jobs_raw.source = 'jsearch'`. `jobs_enriched` has no `source` column; `(deployment_id, job_id)` serves as the composite source key.
- Added "fort bliss" to the Borderplex TX city list for future correctness (Fort Bliss is in El Paso County); today's one Fort Bliss job required Secret clearance and was correctly rejected on that basis regardless.

---

## Task 4 — Data separation verification

All checks passed.

```
TENANT ROW COUNTS (after Phase A):
  students             [OK] CFA= 4,727   [OK] WSB=    9   (expect CFA=4727, WSB=9)
  jobs_enriched        [OK] CFA=   103   [OK] WSB=   40   (expect CFA=103, WSB=40)
  applications         [OK] CFA=     3   [OK] WSB=    0   (expect CFA=3, WSB=0)
  gap_analyses         [OK] CFA=    30   [OK] WSB=    0   (expect CFA=30, WSB=0)
  match_narratives     [OK] CFA=     0   [OK] WSB=    0   (expect CFA=0, WSB=0)

NULL tenant_id check: 0 across all 5 tables.

CFA DATA INTEGRITY (vs pre-Phase-A baselines):
  All 5 tables match baseline exactly. Zero drift.

WSB APPRENTICES:
  9 total. cohort_id='cohort-1-feb-2026' on all 9. parse confidence 0.9-1.0.
  showcase_active=FALSE on all 9.

WSB JOBS:
  40 total. 0 senior-title residuals.

SUPPORTING TABLES (derived tenancy via FK):
  WSB student_skills:        136 rows
  WSB student_work_experience: 26 rows
  WSB jobs_raw (wsb-elpaso-cohort1): 40 rows
```

CFA's data is fully intact (no contamination, no loss). WSB contains only what Tasks 2 and 3 ingested.

---

## State of data ready for Phase B

Phase B (matching, gap analysis, narrative generation) can run against the following WSB-scoped dataset:

**Apprentice candidates** — 9 rows in `students WHERE tenant_id = '2be4a5fc-d1cd-40dd-842d-714664fb1c6f'`:
- `cohort_id = 'cohort-1-feb-2026'` is the group filter
- Parsed resumes, 0.9–1.0 confidence
- Skills matched to taxonomy (`student_skills`)
- Work history (`student_work_experience`)
- Full resume extractions in `legacy_data.resume_parsed_data`

**Job pool** — 40 rows in `jobs_enriched WHERE tenant_id = WSB UUID AND deployment_id = 'wsb-elpaso-cohort1'`:
- All El Paso metro (mostly El Paso proper, some Borderplex-neighboring per relaxed filter)
- Full `job_description`, `job_highlights`
- Structured location fields (city/state/country/is_remote/lat/lng)
- Raw JSearch payload preserved in `jobs_raw` for re-enrichment

**Empty but schema-ready for Phase B writes:**
- `gap_analyses` (WSB = 0 rows) — ready to receive per-apprentice gap analyses
- `match_narratives` (WSB = 0 rows) — ready to receive per-(student, job) narratives; schema has `verdict_line`, `narrative_text`, `match_strengths`, `match_gaps`, `calibration_label`, `cosine_similarity`, `input_hash`
- `applications` (WSB = 0 rows) — ready to receive application records if Phase B triggers them

**Embeddings infrastructure already in place** (from Sleepy-wiles migrations 011-013):
- Polymorphic `embeddings` table (VECTOR(1536), HNSW cosine)
- Covers both students and jobs_enriched via `entity_type`+`entity_id`
- Currently 249 embedding rows (CFA data); WSB embeddings for Cohort 1 apprentices + 40 jobs need to be generated during Phase B.

**Phase B will need to specify the tenant scope** in every query. The `tenant_id` column is NOT NULL everywhere, but the API layer does not enforce tenant filtering. Phase B code must include `WHERE tenant_id = %s` on every read and every write.

---

## Issues encountered during Phase A and how they were resolved

1. **SharePoint tenant URL typo.** Ritu provided `computingforall.sharepoint.com`; actual tenant is `computinforall.sharepoint.com` (missing a `g`). Corrected at the hostname constant in the fetch script. Site URL path (`sites/cfatechsectorleadership`) was correct.
2. **`None + str` TypeError** in first-run filter (null-safety bug on JSearch fields that can be None rather than missing). Patched with `or ""` pattern. Cost: one crashed run that fetched but didn't insert — no data impact, just a redo.
3. **Windows cp1252 console UnicodeEncodeError on emoji-containing job titles** (🏆 etc.). Two crashes from this, both after the actual inserts had committed. Fixed by adding `_ascii()` helper to all print statements. No data impact, just incomplete console output + crashed digest-write on one run (recovered by hand).
4. **No cached raw data** when Ritu asked for a filter re-run. Her instruction assumed cached raw data existed; I hadn't cached. Resolved by re-fetching (6 API calls) and adding cache-first behavior to the script so future adjustments cost zero calls.
5. **The 3 specific Borderplex-metro jobs (Canutillo/Chamberino/Clint) dropped out of JSearch's current-month window** between first fetch and reconcile. Accepted the delta — final count 40 instead of expected 41, composition slightly different.

---

## Decisions Ritu should know about

| Decision | Rationale |
|---|---|
| Only 5 tables got `tenant_id` | Spec said "lightest viable." Other tenant-adjacent tables flagged but untouched. |
| UUID IDs for `tenants` | Matches existing UUID convention on related tables. |
| `jobs_raw` did not get `tenant_id` | Spec didn't list it; `deployment_id` already provides per-tenant partitioning. |
| Local-parse bypass for apprentice resumes | Decision (b) per Ritu. Resumes never went into Azure Blob Storage. `resume_blob_path` is NULL on WSB students; path recorded in `legacy_data.resume_local_path`. |
| All 9 apprentices kept (including Ricardo) | Ritu's call — reversible later if Alma/Gary flag him as not Cohort 1. |
| Title-casing preserved | Ritu's call — "data accurately reflects what's on the resumes." EMILIO and FATIMA stay uppercase. |
| `deployment_id = 'wsb-elpaso-cohort1'` on WSB jobs | New deployment (parallel to `cfa-seattle-bd` and `waifinder-national`). Partitions CFA Coalition jobs from Borderplex Cohort 1 jobs within the WSB tenant. |
| Conservative El-Paso-only filter in first run, relaxed to Borderplex metro in reconcile pass | Ritu's adjustment. Now includes El Paso County TX cities + Doña Ana County NM cities. Fort Bliss included in case a non-clearance role appears later. |
| Senior-title exclusion added post-hoc | Ritu's adjustment. Removes Head of / Director of / VP / Chief / Principal roles from the pool; above apprentice fit. |
| Raw payload caching baked into ingest script | Protects future filter iterations from unnecessary API spend. |
| Digest JSONs kept gitignored | Consistent with the resume-digest pattern; avoids tracking bulky API snapshots in version control. |
| No push to remote | Ritu's explicit instruction. Three commits are local on `feature/finance-cockpit`: `3b65d8a`, `013c048`, `0a98a84`. |
| Phase 2G in-flight work (match_narrative.py, migration 012, etc.) left alone | Constraint: only Phase A files committed. Other modifications on this branch remain uncommitted for Ritu to handle separately. |

---

## Files produced this session

**Committed (on `feature/finance-cockpit`, not pushed):**
- `scripts/014-tenants-seed.sql` *(commit `013c048`)*
- `scripts/phase_a_fetch_sharepoint_resumes.py` *(commit `3b65d8a`)*
- `scripts/phase_a_parse_cohort1_resumes.py` *(commit `3b65d8a`)*
- `scripts/phase_a_ingest_elpaso_jobs.py` *(commit `0a98a84`)*
- `.gitignore` *(updated in both `3b65d8a` and `0a98a84`)*

**Gitignored (local only):**
- `data/cohort1_resumes/` — 9 apprentice PDFs (PII)
- `data/cohort1_ingestion_digest.json` — per-apprentice extraction summary (PII)
- `data/cohort1_jobs_raw_cache/` — 6 JSON files (raw JSearch payloads per query; lets future filter adjustments run offline)
- `data/cohort1_jobs_ingestion_digest.json` — per-job ingestion summary (non-PII; kept gitignored for consistency)

**Other (main-folder docs):**
- `docs/phase_a_cohort1_setup_summary.md` — this file.

---

## What's ready for Phase B

- Tenant isolation is in place at the schema level.
- 9 WSB apprentices ingested with clean skills + work history.
- 40 WSB jobs in the El Paso metro pool, pre-filtered for cohort fit.
- Supporting data (student_skills, student_work_experience, jobs_raw) populated.
- Cache layer ready for any further filter tweaks at zero API cost.
- Phase B can start whenever Ritu gives the go-ahead.

*End of Phase A summary.*
