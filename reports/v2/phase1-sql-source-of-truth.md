# Phase 1: SQL Database Discovery — Source of Truth Report
**Date:** 2026-04-02
**Source:** BACPAC backup (prod.bacpac, 57.6 MB, exported 2025-11-18)
**Database:** Azure SQL (SQL_Latin1_General_CP1_CI_AS, CompatibilityMode 160)
**Schema provider:** Microsoft.Data.Tools.Schema.Sql.SqlAzureV12DatabaseSchemaProvider
**Status:** Decommissioned — full backup recovered to local BACPAC

---

## Executive Summary

The original SQL database contains **76 tables** managed by Prisma ORM
(Next.js/TypeScript app). It covers five platform layers: students,
employers, jobs, skills/matching, and career services assessments.
The single largest asset is the **skills table** (5,061 rows, 259 MB)
containing skill embeddings (~20K chars each, likely JSON-serialized
float arrays from text-embedding-3-small).

The database has been decommissioned from Azure SQL. A full BACPAC
backup was recovered and the skills table has already been migrated
to local PostgreSQL (`wfd_os.public.skills`, 5,061 rows, 85 MB).

---

## All 76 Tables by Agent Domain

### Profile Agent (Students + Employers) — 15 tables

| Table | Key Columns | Est. Data Size | Purpose |
|-------|-------------|---------------|---------|
| users | id (uuid), first_name, last_name, email, phone, role, avatar_url, created_at | 137 KB | Auth/identity for all user types |
| Account | id, user_id (FK→users), type, provider, provider_account_id, access_token, refresh_token | small | OAuth accounts (NextAuth) |
| Authenticator | userId (FK→users), credentialId, credentialPublicKey, counter | small | WebAuthn credentials |
| Session | id, sessionToken, userId (FK→users), expires | small | Active sessions |
| VerificationToken | identifier, token, expires | small | Email verification tokens |
| jobseekers | id (uuid), user_id (FK→users), city, state, zipcode, education_level, years_experience, bio, resume_url, is_featured, status | 146 KB | Student profiles |
| jobseekers_private_data | id, jobseeker_id (FK→jobseekers), ssn, dob, gender, ethnicity, veteran_status, disability_status | 27 KB | PII (sensitive) |
| jobseekers_education | id, jobseeker_id (FK→jobseekers), institution, degree, field_of_study, start_date, end_date, gpa | 64 KB | Education history |
| project_experiences | id, jobseeker_id (FK→jobseekers), title, description, start_date, end_date, url | 88 KB | Portfolio/projects |
| project_has_skills | project_id (FK→project_experiences), skill_id (FK→skills) | 20 KB | Skills per project |
| work_experiences | id, jobseeker_id (FK→jobseekers), company, title, description, start_date, end_date, is_current | 304 KB | Work history |
| social_media_platforms | id, name, base_url | 2 KB | Platform definitions |
| employers | id (uuid), user_id (FK→users), company_id (FK→companies), title, linkedin_url | 5 KB | Employer user profiles |
| companies | id (uuid), name, industry_sector_id, website, description, logo_url, size, city, state, zipcode | 73 KB | Company/org records |
| company_addresses | id, company_id (FK→companies), address_line_1, city, state, zipcode, is_primary | 9 KB | Company locations |

### Market Intelligence Agent (JIE) — 6 tables

| Table | Key Columns | Est. Data Size | Purpose |
|-------|-------------|---------------|---------|
| job_postings | id (uuid), employer_id (FK→employers), title, description, city, state, zipcode, salary_min, salary_max, employment_type, remote_option, status, created_at, expires_at | 1.5 MB | Job listings |
| _JobPostingSkills | A (job_posting_id), B (skill_id) | 54 KB | M2M: job ↔ skill |
| JobseekerJobPosting | id, jobseeker_id, job_posting_id, status, applied_at | 30 KB | Applications/matches |
| bookmarked_jobseekers | id, employer_id, jobseeker_id | <1 KB | Employer bookmarks |
| events | id, name, description, date, location, organizer, url, image_url | 673 KB | Career events |
| events_on_users | event_id, user_id | 4 KB | Event attendance |

### Skills & Matching Agent — 6 tables

| Table | Key Columns | Est. Data Size | Purpose |
|-------|-------------|---------------|---------|
| skills | id (uuid), skill_subcategory_id, skill_name, skill_info_url, embedding (text ~20K chars), skill_type, created_at | **259 MB** | **5,061 skills with embeddings** |
| skill_subcategories | id, name, technology_area_id | 8 KB | Skill groupings |
| technology_areas | id, name | 1 KB | Top-level categories (Cybersecurity, Data Science, etc.) |
| jobseeker_has_skills | jobseeker_id, skill_id | 64 KB | Student ↔ skill mapping |
| JobRole | id, title, description, pathway_id | 301 KB | Defined job roles |
| JobRoleSkill | job_role_id, skill_id, importance_level | 61 KB | Required skills per role |

### Career Services Agent — 9 tables

| Table | Key Columns | Est. Data Size | Purpose |
|-------|-------------|---------------|---------|
| CaseMgmt | id, student_id, advisor_id, status, created_at | 4 KB | Case management records |
| CaseMgmtNotes | id, case_id, category, notes (HTML), created_at | <1 KB | Case notes |
| CareerPrepAssessment | id, student_id, pathway, rating_scores (JSON) | 23 KB | Career readiness assessments |
| BrandingRating | id, student_id, scores across ~18 dimensions | 3 KB | Personal branding assessment |
| CybersecurityRating | id, student_id, scores across ~18 dimensions | <1 KB | Cybersecurity pathway |
| DataAnalyticsRating | id, student_id, scores | <1 KB | Data analytics pathway |
| DurableSkillsRating | id, student_id, scores | 3 KB | Durable/soft skills |
| ITCloudRating | id, student_id, scores | <1 KB | IT/Cloud pathway |
| SoftwareDevRating | id, student_id, scores | 1 KB | Software dev pathway |

**Six rating schemas = 6 career pathways covering ~99 skill dimensions total**

### College Pipeline Agent — 7 tables

| Table | Key Columns | Est. Data Size | Purpose |
|-------|-------------|---------------|---------|
| edu_providers | id (uuid), name, website, city, state, type | 59 KB | Educational institutions |
| programs | id, name, description, duration, delivery_mode, credential_type | 76 KB | Academic programs |
| provider_programs | provider_id (FK→edu_providers), program_id (FK→programs) | 318 KB | Institution ↔ program |
| cip | id, code, title, definition | 2.0 MB | CIP taxonomy (Classification of Instructional Programs) |
| socc | id, code, title | 131 KB | SOC codes (current) |
| socc_2010 | id, code, title | 72 KB | SOC codes (2010 version) |
| socc_2018 | id, code, title | 74 KB | SOC codes (2018 version) |
| cip_to_socc_map | cip_id, socc_id | 280 KB | CIP ↔ SOC crosswalk |

### Reference / System — 8 tables

| Table | Key Columns | Est. Data Size | Purpose |
|-------|-------------|---------------|---------|
| pathways | id, name, description | 11 KB | Career pathways |
| PathwayTraining | pathway_id, training_id | 11 KB | Pathway ↔ training |
| Training | id, name, provider, url, cost, duration | 63 KB | Training resources |
| JobRoleTraining | job_role_id, training_id | 18 KB | Role ↔ training |
| industry_sectors | id, name | 2 KB | Industry taxonomy |
| postal_geo_data | zipcode, city, state, county, lat, lon | 2.8 MB | Geo lookup |
| certificates | id, name, issuer, url | 43 KB | Certifications catalog |
| RAGRecordManager | id, hash_key | <1 KB | RAG pipeline tracking |
| _prisma_migrations | id, migration_name, started_at, applied_steps_count | 25 KB | Schema migration history |

---

## Key Relationships (Foreign Keys)

```
users ─────────────────┬──→ Account (user_id)
                       ├──→ Session (userId)
                       ├──→ Authenticator (userId)
                       ├──→ jobseekers (user_id)
                       └──→ employers (user_id)

jobseekers ────────────┬──→ jobseekers_private_data (jobseeker_id)
                       ├──→ jobseekers_education (jobseeker_id)
                       ├──→ project_experiences (jobseeker_id)
                       ├──→ work_experiences (jobseeker_id)
                       ├──→ jobseeker_has_skills (jobseeker_id)
                       ├──→ JobseekerJobPosting (jobseeker_id)
                       └──→ bookmarked_jobseekers (jobseeker_id)

employers ─────────────┬──→ companies (company_id)
                       └──→ job_postings (employer_id)

skills ────────────────┬──→ _JobPostingSkills (B)
                       ├──→ jobseeker_has_skills (skill_id)
                       ├──→ project_has_skills (skill_id)
                       ├──→ JobRoleSkill (skill_id)
                       └──→ skill_subcategories (skill_subcategory_id)

skill_subcategories ───→ technology_areas (technology_area_id)

edu_providers ─────────→ provider_programs (provider_id)
programs ──────────────→ provider_programs (program_id)
cip ───────────────────→ cip_to_socc_map (cip_id)
socc ──────────────────→ cip_to_socc_map (socc_id)
```

---

## Current Migration Status

| Table | Migrated to Local PG? | Notes |
|-------|----------------------|-------|
| skills | **YES** — 5,061 rows, 85 MB | Embeddings stored as text (~20K chars each) |
| All other 75 tables | **NO** | Data in BACPAC BCP format only |

---

## Data Freshness

- **BACPAC export date:** 2025-11-18
- **Database status:** Decommissioned from Azure SQL
- **Prisma migrations:** Present, indicating active development through the app lifecycle
- **Most recent data:** Unknown without parsing BCP files, but the system was dormant per CLAUDE.md

---

## Critical Findings

1. **Skills embeddings are the crown jewel.** 5,061 skills with ~20K-char embeddings each (259 MB). Already migrated to local PG. These are likely JSON-serialized float arrays from `text-embedding-3-small` (1536 dimensions).

2. **Six career pathway rating schemas** (BrandingRating, CybersecurityRating, DataAnalyticsRating, DurableSkillsRating, ITCloudRating, SoftwareDevRating) — covering 99 skill dimensions. Very low row counts suggest these were barely used.

3. **CIP-to-SOC crosswalk** is fully built — maps educational programs to occupational codes. Valuable for the College Pipeline Agent.

4. **RAGRecordManager** exists but has minimal data — the RAG pipeline was designed but barely activated.

5. **jobseekers_private_data** contains PII (SSN, DOB, gender, ethnicity, veteran status). Must be handled with encryption in any migration.

6. **The database was Prisma-managed** (Next.js app). All tables use UUID primary keys and follow Prisma naming conventions.

---

## Agent Ownership Summary

| Agent | Tables Owned | Primary Value |
|-------|-------------|---------------|
| Profile Agent | 15 tables | Student profiles, employer records, auth |
| Market Intelligence Agent | 6 tables | Job postings, applications, events |
| Matching Agent | 6 tables | Skills taxonomy, embeddings, role-skill mapping |
| Career Services Agent | 9 tables | Assessments, case management, 6 rating schemas |
| College Pipeline Agent | 7 tables | Institutions, programs, CIP/SOC taxonomy |
| System/Reference | 8 tables | Pathways, training, geo, migrations |

---

*Source: recovered-code/bacpac/extracted/model.xml (76 tables)*
*Local PG: wfd_os.public.skills (5,061 rows migrated)*
