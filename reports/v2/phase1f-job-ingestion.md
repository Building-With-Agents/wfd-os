# Phase 1f: External Job Listings Ingestion Discovery
**Date:** 2026-04-02

---

## Job Listing Sources Found

### 1. Lightcast Jobs (Dataverse) — 2,670 records
- Entity: `cfa_lightcastjobs`
- Source: Lightcast (formerly Emsi/Burning Glass) labor market data
- Contains: job titles, descriptions, skills, locations, wages, SOC codes
- Status: Static dataset — no evidence of ongoing ingestion pipeline

### 2. CFA Job Postings (SQL) — in BACPAC
- Table: `job_postings` (1.5 MB in BACPAC)
- Contains: employer_id, title, description, location, salary range, employment type
- Linked to: `_JobPostingSkills` (M2M with skills taxonomy)
- Status: Decommissioned with SQL database

### 3. CFA Job Postings (Dataverse) — not found
- Entity `cfa_cfajobpostings` returned 404
- CFA's own postings may use a different entity name
- May need full entity enumeration to locate

### 4. Lightcast Excel Export (local)
- File: `C:/Users/ritub/projects/wfd-os/lightcast-jobs-export.xlsx`
- Likely a manual export from Lightcast for analysis
- May contain additional data not in Dataverse

## Ingestion Pipeline Status

| Component | Status |
|-----------|--------|
| Automated ingestion | **None found** |
| Scheduled pipeline | **None found** |
| Python ingestion code | **Not in function app** (stub only) |
| Raw data files in Blob | **None** |
| Last ingestion run | **Unknown** |

**Assessment:** There was no automated job ingestion pipeline. The 2,670
Lightcast jobs were likely a one-time bulk import. Job postings in SQL
were created through the React app by employers.

## Normalization

- Skills were manually linked to jobs via `_JobPostingSkills` table
- No automated skills extraction from job descriptions was found
- The skills taxonomy (5,061 skills with embeddings) exists but was
  not automatically applied to incoming listings

## Volume and Freshness

| Dataset | Records | Last Activity |
|---------|---------|---------------|
| Lightcast jobs | 2,670 | Unknown (static import) |
| SQL job postings | Est. hundreds | Pre-2025-11-18 (BACPAC date) |
| Active ingestion | 0 | No pipeline exists |

---

## Summary for Market Intelligence Agent Build

| Asset | Status | Action |
|-------|--------|--------|
| 2,670 Lightcast jobs in Dataverse | Ready to migrate | Migrate to PostgreSQL |
| SQL job postings (BACPAC) | Ready to extract | Parse BCP or re-query |
| Lightcast Excel export | Available | Analyze for additional data |
| Skills taxonomy (5,061) | Migrated to PG | Use for job-skill linking |
| Automated ingestion | Does not exist | Build as Market Intelligence Agent |
| JSearch API integration | Not started | Priority for JIE/Borderplex |
