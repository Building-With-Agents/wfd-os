# WFD OS — Discovery Phase Complete (v2)
**Date:** 2026-04-02
**Prepared for:** Ritu Bahl, Executive Director, Computing for All

---

## What Was Done

Full re-discovery aligned to CLAUDE.md v4, with live verification
of all data sources. All reports regenerated with current data.

| Phase | Report | Status |
|-------|--------|--------|
| Phase 1 | SQL Source of Truth | Complete — 76 tables mapped |
| Phase 1b | Python Codebase | Complete — stub only, nothing to reuse |
| Phase 1c | Blob Storage | Complete — 1,515 resumes, no models |
| Phase 1d | Dataverse Deep | Complete — 163 entities, live counts |
| Phase 1e | Career Services | Complete — schemas exist, barely used |
| Phase 1f | Job Ingestion | Complete — no pipeline, static data |
| Phase 1g | College Intelligence | Complete — CIP/SOC crosswalk ready |
| Phase 1h | Talent Showcase | Complete — minimal engagement data |
| Phase 1i | Matching Engine | Complete — embeddings reusable |
| Phase 1j/k/l | React/Flows/Apps | Complete — all being replaced |
| Phase 2 | Schema Profiling | Complete — target schema designed |

---

## The Full Picture

### What Exists (Live, Verified)

| Layer | Source | Volume |
|-------|--------|--------|
| **Students** | Dataverse contacts (266 custom fields) | 5,000+ records |
| **Student Details** | Dataverse cfa_studentdetails | 2,139 records |
| **Employers** | Dataverse accounts | 1,619 records |
| **Employer Details** | Dataverse cfa_employerdetails | 187 records |
| **Student Journeys** | Dataverse cfa_studentjourneies | 3,728 records |
| **Lightcast Jobs** | Dataverse cfa_lightcastjobs | 2,670 records |
| **College Programs** | Dataverse cfa_collegeprograms | 729 records |
| **Career Programs** | Dataverse cfa_careerprograms | 3,940 records |
| **Skills Taxonomy** | Local PostgreSQL (from BACPAC) | 5,061 with embeddings |
| **Resumes** | Azure Blob Storage | 1,515 PDFs (198 MB) |
| **CIP/SOC Taxonomy** | BACPAC | Full crosswalk |
| **Career Assessments** | BACPAC (6 schemas, 99 dims) | Minimal data |
| **Portal Users** | Dataverse cfa_reactportalusers | 314 records |
| **Azure OpenAI** | resumejobmatch.openai.azure.com | GPT-4.1 Mini + embeddings |

### What Does NOT Exist

| Expected | Reality |
|----------|---------|
| Automated job ingestion pipeline | Never built |
| Matching/similarity engine | Designed but never coded |
| Gap analysis computation | Framework only, no logic |
| Resume parsing at scale | 15 OCR experiments, 1,500 unprocessed |
| Placement outcome tracking | Not implemented |
| Employer engagement analytics | Bookmark feature only |
| Power Automate business logic | SQLtoDynamics flow — never ran |
| Python AI endpoint | Stub with TODO placeholder |

---

## Infrastructure

| Resource | Status |
|----------|--------|
| Local PostgreSQL 18.3 | Running, wfd_os database with skills table |
| Dataverse (cfahelpdesksandbox) | Live, API access working |
| Azure Blob Storage | Live, SDK access working |
| Azure OpenAI | Live, keys in .env |
| WFD-OS App Registration | System Admin in both Dynamics instances |
| .env credentials | All verified and working |

---

## What's Ready for Migration

| Data | Source | Records | Readiness |
|------|--------|---------|-----------|
| Skills taxonomy | Already in local PG | 5,061 | **DONE** (needs pgvector upgrade) |
| Contacts → students | Dataverse API | 5,000+ | **READY** |
| Accounts → employers | Dataverse API | 1,619 | **READY** |
| Student details (merge) | Dataverse API | 2,139 | **READY** |
| Lightcast jobs | Dataverse API | 2,670 | **READY** |
| Student journeys | Dataverse API | 3,728 | **READY** |
| College programs | Dataverse API | 729 | **READY** |
| Career programs | Dataverse API | 3,940 | **READY** |
| CIP/SOC taxonomy | BACPAC (needs parsing) | ~10K+ | **NEEDS WORK** |
| Career assessments | BACPAC (needs parsing) | Minimal | LOW PRIORITY |
| Resume parsing | Blob Storage → Claude API | 1,515 | **AFTER MIGRATION** |

---

## Reports Location

All v2 reports: `C:\Users\ritub\projects\wfd-os\reports\v2\`

| File | Content |
|------|---------|
| phase1-sql-source-of-truth.md | 76 SQL tables, agent mapping, ERD |
| phase1b-python-codebase.md | Function app analysis (stub) |
| phase1c-blob-storage.md | 4 containers, 1,515 resumes |
| phase1d-dataverse-deep.md | 163 entities, live counts, field analysis |
| phase1e-career-services.md | Assessments, case mgmt, gap analysis |
| phase1f-job-ingestion.md | Job sources, no pipeline |
| phase1g-college-intelligence.md | Programs, CIP/SOC crosswalk |
| phase1h-talent-showcase.md | Showcase data, engagement gaps |
| phase1i-matching-engine.md | Embeddings, no matching code |
| phase1jkl-apps-flows-react.md | React app, Power Automate, Power Apps |
| phase2-schema-profiling.md | Target PostgreSQL schema design |
| **MASTER-SUMMARY-v2.md** | **This file** |

---

## Recommended Next Steps

1. **Review this discovery** — confirm completeness before migration
2. **Run field population audit** — sample 500 Dataverse contacts to
   identify dead fields before schema finalization
3. **Review PostgreSQL schema** with Gary
4. **Begin migration** — Dataverse → local PostgreSQL (testing)
5. **Install pgvector** — convert skill embeddings to vector format
6. **Resume parsing pipeline** — after student records are migrated

---

*Discovery complete. Awaiting Ritu's review before migration begins.*
