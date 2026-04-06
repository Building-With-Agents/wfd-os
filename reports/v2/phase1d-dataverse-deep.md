# Phase 1d: Dataverse Deep Discovery — Dataverse Deep Report
**Date:** 2026-04-02
**Instance:** cfahelpdesksandbox.crm.dynamics.com
**Created:** 2021-05-06 (nearly 5 years of data)
**Schema prefixes:** new_ (default), cfa_ (CFA custom publisher)
**Total custom entities:** 163 CFA-specific entities
**Total contact attributes:** 753 (including 266 custom fields)

---

## Executive Summary

CFA's Dynamics/Dataverse instance is the **primary operational data store**
for the workforce development platform. It contains 5,000+ contacts
(students, employers, educators), 1,619 company accounts, 2,670 Lightcast
job postings, 729 college programs, and 3,940 career programs.

The contact entity alone has **266 custom fields** covering demographics,
education (6 certification levels), skills, career data, platform status,
and social media. This is substantially richer than the SQL database,
which was primarily the React app's data store.

**Key finding:** Dataverse is the primary source for migration to PostgreSQL,
not the SQL/BACPAC. The SQL database is supplementary (skills taxonomy,
career assessments, CIP/SOC mappings).

---

## Live Record Counts (Verified 2026-04-02)

| Entity | Entity Set | Records | Agent Owner |
|--------|-----------|---------|-------------|
| Contacts | contacts | **5,000+** | Profile Agent |
| Student Details | cfa_studentdetails | **2,139** | Profile Agent |
| Accounts (Companies) | accounts | **1,619** | Profile Agent |
| Employer Details | cfa_employerdetails | **187** | Profile Agent |
| Student Journeys | cfa_studentjourneies | **3,728** | Profile Agent |
| React Portal Users | cfa_reactportalusers | **314** | Profile Agent |
| Lightcast Jobs | cfa_lightcastjobs | **2,670** | Market Intelligence |
| College Programs | cfa_collegeprograms | **729** | College Pipeline |
| Career Programs | cfa_careerprograms | **3,940** | College Pipeline |
| Education Details | cfa_educationdetails | **8** | Profile Agent |
| Student Work Experiences | cfa_studentworkexperiences | **13** | Profile Agent |

**Note:** Contacts count is capped at 5,000 by Dataverse page limits.
Actual count may be higher (5,152 per earlier discovery).

**Not found:** `cfa_cfajobpostings` entity set returned 404 — CFA's own
job postings may use a different entity name or be stored differently.

---

## Data by Agent Domain

### Profile Agent — Primary Domain

**Contacts (5,000+ records, 266 custom fields):**

The contact entity is massively customized. Key field groups:

| Category | Example Fields | Coverage |
|----------|---------------|----------|
| Demographics | race, ethnicity, gender, disability, veteran_status | Present |
| Education | college, degree, certifications (levels 1-6) | Present |
| Career | skills, experience, resume_data, job_interests | Present |
| Platform | portal_role, assessment_status, enrollment_status | Present |
| Social | linkedin, github, facebook, twitter, portfolio_url | Present |
| Journey | intake_date, cohort, track, placement_status | Present |
| Assessment | gap_score, readiness_level | Present |

**Student Details (2,139 records):**
Extended student profiles beyond the contact record. Likely contains
CFA-specific enrollment data, cohort assignments, and training progress.

**Employer Details (187 records):**
Extended employer profiles — industry, hiring preferences, engagement
history. Small but high-value dataset.

**Student Journeys (3,728 records):**
Lifecycle tracking records — multiple journey entries per student
(3,728 journeys / 2,139 students ≈ 1.7 journey records per student).
Tracks stage transitions through the pipeline.

**React Portal Users (314 records):**
Students/employers who created portal accounts in the React app.
Small subset of total contacts — most contacts never activated portal.

### Market Intelligence Agent

**Lightcast Jobs (2,670 records):**
External job postings ingested from Lightcast (formerly Emsi/Burning Glass).
Contains job titles, descriptions, skills required, locations, wages.
This is the seed data for the JIE/Borderplex deployment.

**CFA Job Postings:** Entity set not found under expected name.
May need to query all entity definitions to locate the correct name.
The SQL database has 513 job_postings in the BACPAC — these may be
the CFA-created postings that live in a differently-named entity.

### College Pipeline Agent

**College Programs (729 records):**
Educational program profiles from colleges and institutions.
Includes skills mapping, credential types, delivery modes.

**Career Programs (3,940 records):**
Career Bridge data — Washington state career/training program listings.
Substantially larger than college programs. Likely includes
community programs, workforce board training, and continuing ed.

### Career Services Agent

Career services data is primarily in the SQL database (6 rating schemas,
case management). Dataverse likely contains the contact-level fields
tracking career services engagement (assessment_status, readiness_level)
on the contact entity.

---

## 163 CFA Custom Entities

The Dataverse instance contains 163 custom entities with `cfa_` prefix.
Key entities beyond those counted above include:

| Category | Likely Entities | Purpose |
|----------|----------------|---------|
| Student pipeline | cfa_studentdetails, cfa_studentjourneies, cfa_studentworkexperiences | Lifecycle tracking |
| Employer | cfa_employerdetails, cfa_companytestimonials, cfa_companygroups | Employer management |
| Jobs | cfa_lightcastjobs, cfa_cfajobpostings (name TBD) | Job listings |
| Education | cfa_collegeprograms, cfa_careerprograms, cfa_educationdetails | Program data |
| Platform | cfa_reactportalusers, cfa_sociallinks | Portal/social |
| Skills | Skills taxonomy entities | Skills mapping |
| Career Bridge | Career Bridge data entities | WA state data |

**Full entity list:** Available via `scripts/dataverse_discovery.py` output.

---

## Contact Entity Field Analysis (753 attributes)

The contact entity has **753 total attributes** — 266 are CFA custom fields.
This is the richest data structure in the entire ecosystem.

**Migration strategy for contacts:**
1. Map the 266 custom fields to the WFD OS PostgreSQL schema
2. Identify which fields are populated (Phase 2 schema profiling)
3. Dead fields (<5% populated) → do not migrate
4. Active fields → map to appropriate PostgreSQL columns
5. Fields with no WFD OS equivalent → store in JSONB overflow column

---

## Dynamics Instance Comparison

| Instance | URL | Status | Data |
|----------|-----|--------|------|
| cfahelpdesksandbox | cfahelpdesksandbox.crm.dynamics.com | **Production** | 5 years, all WFD OS data |
| cfadev | cfadev.crm.dynamics.com | Development | New/empty or minimal |

**Proceed with cfahelpdesksandbox for all migration.**

---

## Data Quality Observations

1. **Education details barely used** — only 8 records vs. 2,139 students.
   Education data likely lives on the contact entity's custom fields
   (college, degree, certification levels 1-6) rather than the
   dedicated education details entity.

2. **Work experience barely used** — only 13 records vs. 2,139 students.
   Same pattern: work history likely in contact custom fields or
   unextracted from resumes in Blob Storage.

3. **Student journeys are rich** — 3,728 records showing pipeline
   stage transitions. Critical for understanding historical flow.

4. **Portal adoption was low** — 314 portal users / 5,000+ contacts
   = ~6% activation rate. Most students never used the self-service portal.

5. **Contacts may exceed 5,000** — Dataverse count API caps at 5,000.
   Earlier discovery found 5,152. Need paginated fetch for exact count.

---

## Migration Priority

| Priority | Data Source | Records | Target |
|----------|-----------|---------|--------|
| **1 — Critical** | contacts (all fields) | 5,000+ | students + employers tables |
| **2 — Critical** | cfa_studentdetails | 2,139 | students table (extended) |
| **3 — High** | accounts | 1,619 | employers table |
| **4 — High** | cfa_lightcastjobs | 2,670 | job_listings table |
| **5 — High** | cfa_studentjourneies | 3,728 | student_journeys table |
| **6 — Medium** | cfa_collegeprograms | 729 | college_programs table |
| **7 — Medium** | cfa_careerprograms | 3,940 | career_programs table |
| **8 — Medium** | cfa_employerdetails | 187 | employers table (extended) |
| **9 — Low** | cfa_reactportalusers | 314 | portal_users table |
| **10 — Low** | cfa_educationdetails | 8 | student_education table |
| **11 — Low** | cfa_studentworkexperiences | 13 | student_work_experiences table |

---

*Source: Live Dataverse Web API query (cfahelpdesksandbox.crm.dynamics.com)*
*Script: scripts/dataverse_discovery.py*
*Auth: WFD-OS App Registration (068d383c), System Administrator*
