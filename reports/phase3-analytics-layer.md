# Phase 3: Analytics Layer — Conversational Query Interface Design
**Date:** 2026-03-30

---

## Executive Summary

This report defines the analytics layer for WFD OS — a conversational query interface that enables natural language questions across all CFA data sources. Based on the data discovered in Phase 1, we answer the sample questions from CLAUDE.md and design the query architecture that the Orchestrator Agent will power.

---

## Sample Questions Answered (from CLAUDE.md)

### "What skills gaps are most common across our student base?"

**Data sources:** SQL `jobseeker_has_skills` + `skills` (5,034 with embeddings) + `job_postings` + `_JobPostingSkills`

**Answer from data:**
- 5,034 skills in taxonomy, but only a subset are mapped to students via `jobseeker_has_skills` (64 KB of associations)
- Job postings require skills listed in `_JobPostingSkills` (54 KB)
- **Gap = skills required by job postings that students don't have**
- The gap analysis was designed (`JobseekerJobPosting.gapAnalysis` field) but barely populated
- **Recommendation:** The Matching Agent compares student skill vectors against job posting skill vectors using cosine similarity on the 1536-dim embeddings. Gaps are skills with high job demand but low student coverage.

**Queryable now?** Partially — the data exists but needs the Matching Agent to compute gaps dynamically.

---

### "Which upskilling pathways led to the most placements?"

**Data sources:** SQL `pathways` (6) + `JobPlacement` (empty) + `CaseMgmt` + Dataverse `cfa_studentjourneies` (3,728)

**Answer from data:**
- 6 career pathways defined (Cybersecurity, Design/UX, Data Analytics, IT/Cloud, Software Dev, Professional Skills)
- `JobPlacement` table exists but is **empty** — placements were never formally tracked in SQL
- `CaseMgmt` has some enrollment data with `careerPrepTrack` field
- Dataverse `cfa_studentjourneies` (3,728 records) may contain journey-to-outcome data

**Queryable now?** No — placement tracking was never implemented. This is a critical feature for the Career Services Agent to build.

---

### "Which college programs best match current market demand?"

**Data sources:** SQL `provider_programs` (318 KB) + `cip_to_socc_map` (280 KB) + Dataverse `cfa_collegeprograms` (729) + `cfa_lightcastjobs` (2,670) + `cfa_toplightcastskills` (150)

**Answer from data:**
- 729 college programs mapped to CIP codes
- CIP codes map to SOC occupation codes via `cip_to_socc_map`
- Lightcast job data (2,670 jobs) shows current market demand by occupation
- Top 150 Lightcast skills show what employers are asking for
- **The bridge exists:** CIP → SOC → Job Demand. The College Pipeline Agent can match programs to market demand.

**Queryable now?** Yes — the data pipeline exists. Needs the College Pipeline Agent to run the join and rank programs by demand alignment.

---

### "What skills are employers asking for that no program teaches?"

**Data sources:** SQL `skills` + `_JobPostingSkills` + `provider_programs` + `provider_program_has_skills` (empty)

**Answer from data:**
- Job postings link to skills via `_JobPostingSkills`
- Provider programs exist (318 KB) but `provider_program_has_skills` is **empty** — program-to-skill mapping was never completed
- **The gap:** We know what employers want (from job postings) but can't programmatically compare to what programs teach (because that mapping wasn't done)

**Queryable now?** Partially — job demand skills are clear, but program skill coverage needs the College Pipeline Agent to extract skills from program descriptions using NLP.

---

### "How many student resumes are in blob storage vs. SQL profiles?"

**Answer from data:**
- **Blob Storage:** 1,531 resume PDFs (198.6 MB) in `resume-storage` container
- **SQL profiles:** `jobseekers` table has `hasResume` boolean field
- **Dataverse:** `cfa_resumeuploaded` field is 30% populated (30 of 100 sampled contacts)
- **Dataverse:** 2,139 student detail records

**Queryable now?** Yes — direct counts available.

---

### "When did the Python matching engine last run?"

**Answer from data:**
- **Function App (`cs-copilot-py-w2-26021101`):** Last modified 2026-02-12. Contains only a stub — no actual matching logic.
- **Logic App (`SQLtoDynamics`):** Created 2025-02-17, **never ran** (0 runs in history)
- **Azure OpenAI (`resumeJobMatch`):** Deployed and active with GPT-4.1 Mini + text-embedding-3-small
- **Matching evidence:** `JobseekerJobPosting` table has 30 KB of match data, so matching DID run at some point — likely from the React app's server-side code, not from the Function App.

**Queryable now?** Yes — the answer is the matching ran from the React app (Next.js server), not from a standalone Python endpoint.

---

### "Which students are 30-60 days away from being job-ready?"

**Data sources:** SQL `CareerPrepAssessment` + `CaseMgmt` + all 6 Rating tables + Dataverse `cfa_studentjourneies`

**Answer from data:**
- `CaseMgmt` has `prepStartDate`, `prepExpectedEndDate`, `prepActualEndDate` fields
- Career Prep assessments track readiness by pathway
- 6 pathway-specific rating tables score students on 13-22 skills each
- **The calculation:** Students with `prepExpectedEndDate` 30-60 days out AND incomplete pathway ratings = "almost job-ready"

**Queryable now?** Partially — the data exists but needs the Career Services Agent to compute readiness scores.

---

### "Which employers browsed the showcase but never hired?"

**Data sources:** SQL `bookmarked_jobseekers` + `JobseekerJobPosting` + `JobPlacement` (empty)

**Answer from data:**
- `bookmarked_jobseekers` tracks employer bookmarks (near-empty — 0.2 KB)
- `JobseekerJobPosting.employerClickedConnect` tracks employer interest
- `JobPlacement` (hire tracking) is **empty**
- Dataverse `cfa_employerfeedbacks` may have engagement data

**Queryable now?** No — employer engagement tracking was minimal. The Profile Agent + Matching Agent need to build this pipeline.

---

## Analytics Architecture for WFD OS

### Query Flow
```
[User Question (natural language)]
        ↓
[Orchestrator Agent]
  ├── Classifies intent
  ├── Routes to domain agent(s)
  └── Aggregates responses
        ↓
[Domain Agent(s)]
  ├── Profile Agent → Dataverse contacts, SQL users/jobseekers
  ├── Market Intelligence → SQL skills/jobs, Dataverse lightcast
  ├── College Pipeline → SQL programs, Dataverse colleges
  ├── Matching Agent → SQL embeddings, match scores
  └── Career Services → SQL ratings, Blob resumes
        ↓
[Formatted Response with Citations]
```

### Data Access Layer per Agent
| Agent | Primary Source | Secondary Source | API |
|-------|---------------|-----------------|-----|
| Profile | Dataverse (contacts, accounts) | SQL (users, jobseekers) | Dataverse Web API |
| Market Intelligence | SQL (skills, job_postings) | Dataverse (cfa_lightcastjobs) | PostgreSQL + Dataverse |
| College Pipeline | Dataverse (cfa_collegeprograms) | SQL (provider_programs, CIP/SOC) | Dataverse + SQL |
| Matching | SQL (skills embeddings) | Azure OpenAI (new embeddings) | SQL + OpenAI API |
| Career Services | SQL (ratings, assessments) | Blob Storage (resumes) | SQL + Blob API |
| Orchestrator | All of the above | Power Automate replacement | Multi-agent routing |

### Query Capabilities by Phase

#### Available Now (data exists, needs agent to query)
1. Student/employer profile lookups
2. Skills taxonomy browsing (5,034 skills)
3. Job posting search and filtering
4. College program search by CIP/SOC code
5. Resume count and storage stats
6. Market demand signals (top skills, companies, wages)
7. Student journey history
8. Career Bridge program data

#### Requires Agent Build (data + logic needed)
1. Dynamic skills gap analysis (Matching Agent)
2. Resume-to-job matching scores (Matching Agent + OpenAI)
3. Program-to-market alignment (College Pipeline Agent)
4. Career readiness scoring (Career Services Agent)
5. Upskilling pathway recommendations (Career Services Agent)
6. Employer engagement analytics (Profile Agent + Matching Agent)
7. Placement outcome tracking (Career Services Agent — needs new data capture)

---

## Key Insight

The analytics layer doesn't need a separate data warehouse or ETL pipeline. The WFD OS agents ARE the analytics layer — each agent owns its domain data and can answer questions about it. The Orchestrator Agent routes questions and combines answers. This is simpler, cheaper, and more powerful than a traditional BI stack.
