# Phase 2: Schema Profiling Report
**Date:** 2026-03-30
**Method:** BCP file analysis (SQL) + 100-record sampling (Dataverse)

---

## Executive Summary

Across both SQL (76 tables) and Dataverse (163 custom entities), CFA has significant schema bloat — particularly on the Contact entity with **145 dead fields out of 266 custom fields (55% dead)**. The SQL database is cleaner but has 27 empty tables out of 76 (35% unused). This report identifies what to keep, what to drop, and the clean schema per WFD OS agent.

---

## SQL Database (BACPAC) — 76 Tables

### Data Status
| Category | Tables | Notes |
|----------|--------|-------|
| **With data** | 49 | Active tables with records |
| **Empty** | 27 | Created but never populated |
| **Total** | 76 | |

### Empty Tables (Candidates for Removal)
These tables were designed but never used:
- **Auth/Identity:** Account, Session, Authenticator, VerificationToken (B2C handled auth instead)
- **Profile:** company_social_links, company_testimonials, volunteers, volunteer_has_skills, educators, cfa_admin
- **College Pipeline:** provider_program_has_skills, ProviderTestimonials, edu_addresses, TraineeDetail
- **Matching:** JobseekerJobPostingSkillMatch, EmployerJobRoleFeedBack, pathway_has_skills, pathway_subcategories, bookmarked_jobseekers (near-empty)
- **Career Services:** JobPlacement, Meeting, OtherPriorityPopulations, sa_questions, sa_possible_answers, self_assessments, proj_based_tech_assessments
- **Reference:** socc2018_to_cip2020_map

### Tables by Agent with Data Health

#### Profile Agent — 12 tables (7 with data)
| Table | Columns | Size | Health |
|-------|---------|------|--------|
| users | 17 | 137 KB | GOOD — core user records |
| jobseekers | 25 | 146 KB | GOOD — student profiles |
| jobseekers_private_data | 13 | 27 KB | GOOD — demographics |
| companies | 20 | 73 KB | GOOD — employer profiles |
| work_experiences | 13 | 304 KB | GOOD — richest profile data |
| project_experiences | 12 | 88 KB | GOOD — portfolio data |
| certificates | 13 | 43 KB | GOOD — certification tracking |
| employers | 9 | 5 KB | THIN — few employer users |
| company_addresses | 5 | 9 KB | THIN — basic location data |

#### Market Intelligence Agent — 13 tables (11 with data)
| Table | Columns | Size | Health |
|-------|---------|------|--------|
| skills | 8 | 260 MB | EXCELLENT — full taxonomy + embeddings |
| job_postings | 34 | 1.6 MB | GOOD — real job data |
| cip | 5 | 2 MB | GOOD — education classification |
| postal_geo_data | 7 | 2.9 MB | GOOD — geographic reference |
| cip_to_socc_map | 4 | 280 KB | GOOD — edu-to-occupation bridge |
| socc + variants | 3-7 | 275 KB | GOOD — occupation codes |
| skill_subcategories | 5 | 8 KB | GOOD — taxonomy structure |

#### College Pipeline Agent — 3 tables with data
| Table | Columns | Size | Health |
|-------|---------|------|--------|
| provider_programs | 26 | 318 KB | GOOD — program details |
| programs | 4 | 76 KB | GOOD — program directory |
| edu_providers | 19 | 59 KB | GOOD — institution profiles |

#### Matching Agent — 4 tables with data
| Table | Columns | Size | Health |
|-------|---------|------|--------|
| JobRole | 13 | 301 KB | GOOD — job role definitions with AI impact |
| jobseeker_has_skills | 4 | 64 KB | GOOD — student-skill links |
| JobRoleSkill | 9 | 61 KB | GOOD — role-skill requirements |
| JobseekerJobPosting | 19 | 30 KB | THIN — few matches run |

#### Career Services Agent — 8 tables with data
| Table | Columns | Size | Health |
|-------|---------|------|--------|
| CareerPrepAssessment | 12 | 23 KB | MODERATE — assessment data |
| BrandingRating | 20 | 3 KB | THIN — few assessments |
| DurableSkillsRating | 22 | 3 KB | THIN — few assessments |
| CaseMgmt | 10 | 4 KB | THIN — few cases tracked |
| SoftwareDevRating | 18 | 1 KB | THIN |
| CybersecurityRating | 15 | 1 KB | THIN |
| ITCloudRating | 18 | 1 KB | THIN |
| DataAnalyticsRating | 18 | 0.3 KB | THIN |

---

## Dataverse (Contact Entity) — 266 Custom Fields

### Population Analysis (100-record sample)

| Category | Fields | Percentage |
|----------|--------|------------|
| **Well populated (>50%)** | 1 | 0.4% |
| **Moderately populated (5-50%)** | 25 | 9.4% |
| **Dead fields (<5%)** | 145 | 54.5% |
| **Virtual/computed (skip)** | ~95 | 35.7% |

### Well Populated Fields (>50%)
- `cfa_cfacontacttype` (93%) — Contact Type (Student, Employer, Educator, etc.)

### Key Populated Fields (5-50%)
| Field | Population | Agent Owner |
|-------|-----------|-------------|
| cfa_race | 45% | Profile |
| cfa_volunteer | 41% | Profile |
| cfa_collegenametext | 39% | College Pipeline |
| cfa_jobapplicant | 36% | Matching |
| cfa_areaofinterest | 33% | Profile |
| cfa_resumeuploaded | 30% | Career Services |
| cfa_howdidyouhear | 27% | Profile |
| cfa_studenttype | 27% | Profile |
| cfa_enrollmentstatus | 15% | Profile |
| cfa_cfaemail | 12% | Profile |
| cfa_cfastudentid | 12% | Profile |
| cfa_cohort | 12% | Profile |
| cfa_workforceboard | 12% | Profile |
| cfa_previouseducation | 12% | College Pipeline |

### Dead Fields — 145 fields at 0% population
These include abandoned features, deprecated fields (many labeled "do not use"), one-off imports, and fields from early prototypes that were never adopted.

**Categories of dead fields:**
- **Deprecated (labeled "do not use"):** ~15 fields
- **Employer-specific on contact:** ~10 fields (employer data moved to Account entity)
- **Form-specific:** ~12 fields (form submissions moved to cfa_formsubmission entity)
- **Assessment pipeline:** ~8 fields (assessment moved to separate entities)
- **Social media:** ~5 fields (0% populated — users don't share social profiles)
- **Donation tracking:** ~4 fields (wrong entity — should be on Account)
- **Legacy imports:** ~10 fields (one-time data migration artifacts)

---

## Clean Schema Recommendation per Agent

### Profile Agent — Clean Schema
**From SQL:** users, jobseekers, jobseekers_private_data, companies, employers, work_experiences, project_experiences, certificates, company_addresses
**From Dataverse:** contacts (keep 26 fields: contactid, firstname, lastname, emailaddress1, birthdate, gendercode, cfa_cfacontacttype, cfa_race, cfa_ethnicity, cfa_volunteer, cfa_collegenametext, cfa_areaofinterest, cfa_resumeuploaded, cfa_studenttype, cfa_enrollmentstatus, cfa_cfaemail, cfa_cfastudentid, cfa_cohort, cfa_workforceboard, cfa_previouseducation, cfa_exitdate, cfa_github, cfa_linkedin, cfa_portfoliourl, cfa_defaultstudentresumeid, cfa_cfacontacttype), accounts (keep 22 custom fields), cfa_studentdetails, cfa_employerdetails, cfa_reactportalusers
**Drop:** 145 dead contact fields, empty SQL auth tables

### Market Intelligence Agent — Clean Schema
**From SQL:** skills (with embeddings), job_postings, skill_subcategories, technology_areas, industry_sectors, _JobPostingSkills, socc/cip tables, postal_geo_data
**From Dataverse:** cfa_jobs, cfa_lightcastjobs, cfa_jobboarddatas, cfa_advertisedwagetrends, cfa_topcompaniespostings, cfa_toppostedjobtitles, cfa_toplightcastskills, cfa_jobpostingsregionalbreakdowns, cfa_careerbridgedatas
**Drop:** Nothing — this domain is clean

### College Pipeline Agent — Clean Schema
**From SQL:** edu_providers, provider_programs, programs, cip, cip_to_socc_map
**From Dataverse:** cfa_colleges, cfa_collegeprograms, cfa_careerprograms, cfa_occupations, cfa_eduinstitutions, cfa_pathwaies, cfa_courses, cfa_careerbridgeitprograms, cfa_careerbridgecipsocs
**Drop:** Empty SQL tables (edu_addresses, ProviderTestimonials, TraineeDetail, provider_program_has_skills)

### Matching Agent — Clean Schema
**From SQL:** skills (embeddings), JobRole, JobRoleSkill, jobseeker_has_skills, JobseekerJobPosting, JobseekerJobPostingSkillMatch (rebuild)
**From Dataverse:** cfa_skills, cfa_inferredskillses, cfa_recommendedresumes, cfa_recommendedjobs, cfa_resumestojobmains, cfa_jobapplicants
**Drop:** Empty pathway_has_skills, pathway_subcategories, EmployerJobRoleFeedBack (rebuild as agent feature)

### Career Services Agent — Clean Schema
**From SQL:** CareerPrepAssessment, CaseMgmt, CaseMgmtNotes, all 6 Rating tables, pathways, Training
**From Dataverse:** cfa_mainresumeparsers, cfa_resumeskills (rebuild), cfa_interviewquestions, cfa_certificates
**From Blob Storage:** resume-storage (1,531 PDFs), image-storage (104 images)
**Drop:** Empty self_assessment tables, empty resume parser sub-tables (rebuild with agent)

### Orchestrator Agent — Clean Schema
**From SQL:** events, events_on_users, Training, JobRoleTraining, PathwayTraining
**From Dataverse:** cfa_formsubmissions, cfa_portalmessages, cfa_messages, cfa_studentcommunicationses, cfa_zoommeetings
**Integration:** Replace SQLtoDynamics Logic App with agent-to-agent sync
**Drop:** _prisma_migrations (framework artifact)

---

## Recommendations

1. **Do NOT migrate dead fields** — 145 dead fields on Contact alone. Start fresh with the 26 essential fields.
2. **Merge SQL + Dataverse** — The same entities exist in both systems with different schemas. The Matching Agent should use SQL skills (with embeddings) as the canonical source.
3. **Consolidate duplicate data** — Contact (Dataverse) + users/jobseekers (SQL) represent the same people. Unify on a single profile per person.
4. **Drop deprecated tables** — 27 empty SQL tables and numerous "do not use" fields can be excluded from the agent data model.
5. **Preserve the valuable** — The 260 MB of skill embeddings, 1,531 resumes, 5,034-skill Lightcast taxonomy, and 76-table SQL schema represent years of work worth keeping.
