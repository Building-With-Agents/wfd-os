# Phase 0 + Phase 1d: Dataverse Discovery Report
**Date:** 2026-03-30
**Instance:** cfahelpdesksandbox.crm.dynamics.com
**Created:** 2021-05-06 (nearly 5 years of data)
**Schema prefix:** new_ (default), cfa_ (custom publisher)

---

## Executive Summary

CFA's Dataverse instance contains **163 custom entities** built specifically for the workforce development platform. The data spans students, employers, jobs, skills, colleges, resume parsing, and market intelligence. This IS the primary data layer — not a secondary sync.

**Key numbers:**
- 5,000+ contacts (students, employers, educators — capped at 5K by Dataverse count)
- 2,139 student detail records
- 1,619 accounts (companies/organizations)
- 513 CFA job postings + 2,670 Lightcast job postings
- 3,940 career programs + 729 college programs
- 5,000+ Career Bridge data records
- 2,962 job applicants
- 3,728 student journey records

---

## Data by WFD OS Agent Domain

### Profile Agent
| Entity | Records | Description |
|--------|---------|-------------|
| contacts | 5,000+ | Students, employers, educators (266 custom fields!) |
| cfa_studentdetails | 2,139 | Extended student profiles |
| cfa_reactportalusers | 314 | Portal login accounts |
| cfa_studentjourneies | 3,728 | Student lifecycle tracking |
| cfa_educationdetails | 8 | Education history |
| cfa_studentworkexperiences | 13 | Work experience |
| accounts | 1,619 | Companies/organizations (22 custom fields) |
| cfa_employerdetails | 187 | Extended employer profiles |
| cfa_companygroups | TBD | Company groupings |
| cfa_companytestimonials | TBD | Employer testimonials |
| cfa_sociallinks | TBD | Social media profiles |

**Contact entity has 266 custom fields including:**
- Demographics: race, ethnicity, gender, disability, veteran status
- Education: college, degree, certifications, levels 1-6
- Career: skills, experience, resume data, job interests
- Platform: portal role, assessment status, enrollment status
- Social: LinkedIn, GitHub, Facebook, Twitter, portfolio URL

### Market Intelligence Agent (JIE)
| Entity | Records | Description |
|--------|---------|-------------|
| cfa_jobs | 513 | CFA-posted job listings |
| cfa_lightcastjobs | 2,670 | Lightcast (external) job data |
| cfa_jobboarddatas | 185 | Job board aggregation data |
| cfa_advertisedwagetrends | 12 | Wage trend analysis |
| cfa_topcompaniespostings | 50 | Top hiring companies |
| cfa_toppostedjobtitles | 50 | Most posted job titles |
| cfa_toplightcastskills | 150 | Most in-demand skills |
| cfa_jobpostingsregionalbreakdowns | 5 | Regional job distribution |
| cfa_topjobpostingindustries | TBD | Industry breakdown |
| cfa_topjobpostingsources | TBD | Source tracking |

### College Pipeline Agent
| Entity | Records | Description |
|--------|---------|-------------|
| cfa_colleges | 3 | College institutions |
| cfa_collegeprograms | 729 | College program profiles |
| cfa_careerprograms | 3,940 | Career training programs |
| cfa_occupations | 29 | Occupation classifications |
| cfa_occupationalprograms | 5 | Occupational pathways |
| cfa_eduinstitutions | 153 | Educational institutions |
| cfa_pathwaies | 6 | Career pathways |
| cfa_courses | 19 | Academic courses |
| cfa_careerbridgedatas | 5,000+ | WA Career Bridge program data |
| cfa_careerbridgeitprograms | TBD | IT-specific programs |
| cfa_careerbridgecipsocs | TBD | CIP/SOC code mappings |

### Matching Agent
| Entity | Records | Description |
|--------|---------|-------------|
| cfa_skills | 9 | Core skills taxonomy |
| cfa_genericskills | 1 | Generic/soft skills |
| cfa_technicalskills | 7 | Technical skills |
| cfa_subskills | 2 | Sub-skill breakdowns |
| cfa_inferredskillses | 614 | AI-inferred skills |
| cfa_resumestojobmains | 0 | Resume-to-job match (empty) |
| cfa_resumestojobmatchs | 0 | Match scores (empty) |
| cfa_recommendedjobs | 0 | Job recommendations (empty) |
| cfa_recommendedresumes | 41 | Resume recommendations |
| cfa_jobapplicants | 2,962 | Application records |
| cfa_favoritejobs | 8 | Saved/favorited jobs |

### Career Services Agent
| Entity | Records | Description |
|--------|---------|-------------|
| cfa_mainresumeparsers | 8 | Resume parsing results |
| cfa_resumeskills | 0 | Extracted resume skills (empty) |
| cfa_resumepositions | 0 | Extracted positions (empty) |
| cfa_resumetaxonomies | 0 | Resume taxonomies (empty) |
| cfa_resumequalities | 0 | Resume quality scores (empty) |
| cfa_resumefindings | 0 | Resume findings (empty) |
| cfa_certificates | TBD | Certifications tracking |
| cfa_interviewquestions | TBD | Interview prep questions |
| cfa_interviewquestionresponses | TBD | Interview responses |

**Note:** Resume parsing entities exist but are mostly empty — the matching/parsing engine appears to have been built but minimally used.

### Orchestrator Agent
| Entity | Records | Description |
|--------|---------|-------------|
| cfa_formsubmissions | TBD | Form submissions |
| cfa_portalmessages | TBD | Portal messaging |
| cfa_messages | TBD | Internal messages |
| cfa_studentcommunicationses | TBD | Student communications |
| cfa_attendancev2s | TBD | Attendance tracking |
| cfa_zoommeetings | TBD | Zoom meeting records |
| cfa_zoommeetingparticipants | TBD | Meeting participants |
| cfa_discourseusers | TBD | Discourse forum users |
| cfa_discoursecategories | TBD | Discourse categories |

---

## Solutions History (CFA-Built)
| Solution | Version | Installed |
|----------|---------|-----------|
| CFA Core | v1.0.0.1 | 2021-05-07 |
| JobScoring | v1.0 | 2021-07-02 |
| Power BI in Dynamics (Demo) | v1.0.0.0 | 2021-05-17 |
| CFA Education Portal - Migration | v1.0.0.2 | 2023-02-28 |
| CFA Core - PreApp | v1.0.0.0 | 2024-07-28 |
| CFA Core - Higher Ed | v1.0.0.1 | 2024-09-01 |
| Employer Signaling | v1.0.0.0 | 2024-08-29 |
| Discourse Integration | v1.0.0.0 | 2024-12-03 |
| Talent Finder React Portal | v1.0.0.0 | 2024-12-19 |
| Talent Finder React Portal 2 | v1.0.0.0 | 2025-02-27 |
| Career Prep | v1.0.0.0 | 2025-08-04 |
| CFA HD to CFA Dev Migration | v1.0.0.0 | 2025-06-24 |

---

## Key Findings

1. **Dataverse IS the primary database** — not a secondary sync. The 163 custom entities cover every layer of the WFD OS.

2. **The matching engine was built but barely used** — Resume-to-job match tables exist but are empty. The skills taxonomy has only 9 entries. This is the biggest opportunity for WFD OS agents.

3. **Market intelligence data exists** — Lightcast jobs (2,670), Career Bridge data (5,000+), wage trends, top skills, top companies. The JIE has a foundation.

4. **Resume parsing was started** — Sovren/resume parser entities exist with detailed sub-tables (skills, positions, taxonomies, quality scores), but only 8 records processed.

5. **Student journey tracking is rich** — 3,728 journey records across 2,139 students shows the lifecycle was being tracked.

6. **Contact count is capped at 5,000** — The actual total is likely much higher. Need to paginate to get true count.

7. **Two Dynamics instances exist:**
   - `cfahelpdesksandbox` — THE production data (created 2021-05-06)
   - `cfadev` — New empty instance (created 2026-01-29)

---

## Dynamics CRM Instances

| Instance | URL | Created | Records | Status |
|----------|-----|---------|---------|--------|
| cfahelpdesksandbox | cfahelpdesksandbox.crm.dynamics.com | 2021-05-06 | Active data | **PRIMARY** |
| cfadev | cfadev.crm.dynamics.com | 2026-01-29 | Empty | New/Dev |

---

## Next Steps

1. **Get true contact count** (paginate past 5,000 limit)
2. **Get record counts for remaining TBD entities**
3. **Sample data from key entities** (jobs, student details, employer details)
4. **Map entity relationships** (FK connections between tables)
5. **Proceed to Phase 1** — SQL database discovery (need connection string)
6. **Proceed to Phase 1b** — Azure Python endpoint discovery (need URL)
7. **Proceed to Phase 1c** — Blob Storage discovery (need connection string)
