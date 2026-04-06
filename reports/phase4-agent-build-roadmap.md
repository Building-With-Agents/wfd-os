# Phase 4: WFD OS Agent Build Roadmap
**Date:** 2026-03-30

---

## Executive Summary

Based on complete discovery of CFA's data ecosystem — 76 SQL tables (recovered), 163 Dataverse custom entities, 1,531 resumes, 5,034 skills with vector embeddings, two Azure OpenAI deployments, 10 Power Apps, 20 chatbots, and a live Next.js React application — this roadmap defines the build sequence, data readiness, and integration plan for the six WFD OS agents.

**Recommended build order:** Market Intelligence → Profile → Matching → Career Services → College Pipeline → Orchestrator

**Fastest Waifinder demo for Texas:** Market Intelligence Agent (the JIE for Borderplex) — data ready, 2-3 week build.

---

## 1. Recommended Build Sequence

### Agent 1 (Build First): Market Intelligence Agent
**Why first:**
- Data is the most complete and cleanest (5,034 skills with embeddings, 2,670 Lightcast jobs, 5,834 Career Bridge records, wage trends, top skills)
- This IS the JIE being built for Workforce Solutions Borderplex — immediate revenue opportunity
- No dependency on other agents
- Fastest path to a Waifinder demo for Texas
- PostgreSQL `talent_finder` database already created (19 days ago) — infrastructure ready

**Build time estimate:** 2-3 weeks to MVP

### Agent 2: Profile Agent
**Why second:**
- Foundational — every other agent needs profile data
- Data exists across two systems (Dataverse: 5,152 contacts, SQL: users + jobseekers)
- Need to unify the dual data sources into a single profile model
- Enables the Matching Agent (needs student profiles to match)

**Build time estimate:** 2-3 weeks

### Agent 3: Matching Agent
**Why third:**
- Depends on Profile Agent (student profiles) and Market Intelligence Agent (job data + skills)
- Core value proposition of Waifinder — skills-based matching
- 5,034 skill embeddings ready to load
- Azure OpenAI (text-embedding-3-small + GPT-4.1 Mini) deployed and ready
- Match schema already designed (19-column JobseekerJobPosting table)
- Gap analysis, elevator pitch, resume generation fields exist — just need activation

**Build time estimate:** 3-4 weeks

### Agent 4: Career Services Agent
**Why fourth:**
- Depends on Profile Agent (student data) and Matching Agent (gap analysis)
- 1,531 resumes in Blob Storage ready for processing
- 6 pathway rating schemas (99 granular skill dimensions) provide assessment framework
- Resume parser entities exist in Dataverse — rebuild with modern AI
- CLTI (Nina Zhao / careerslaunch.org) integration point

**Build time estimate:** 3-4 weeks

### Agent 5: College Pipeline Agent
**Why fifth:**
- Depends on Market Intelligence Agent (demand signals) and Matching Agent (skills taxonomy)
- 729 college programs + 3,940 career programs + 153 edu institutions
- CIP-to-SOC mapping enables program-to-occupation bridging
- Career Bridge data (5,834 records) provides WA state program intelligence
- Lower urgency for initial Waifinder demo

**Build time estimate:** 2-3 weeks

### Agent 6 (Build Last): Orchestrator Agent
**Why last:**
- Depends on all other agents being functional
- Routes requests, coordinates multi-agent workflows
- Replaces Power Automate flows and manual staff workflows
- The "natural language interface" to the entire system
- Can be incrementally built as each agent comes online

**Build time estimate:** 2-3 weeks (incremental)

---

## 2. Data Readiness per Agent

### Market Intelligence Agent
| Data Source | Status | Action Needed |
|------------|--------|---------------|
| SQL `skills` (5,034 + embeddings) | READY | Load into PostgreSQL |
| SQL `job_postings` (1.6 MB) | READY | Load into PostgreSQL |
| SQL `skill_subcategories` | READY | Load as taxonomy |
| SQL CIP/SOC tables | READY | Load as reference data |
| Dataverse `cfa_lightcastjobs` (2,670) | READY | API access working |
| Dataverse `cfa_careerbridgedatas` (5,834) | READY | API access working |
| Dataverse `cfa_toplightcastskills` (150) | READY | API access working |
| Dataverse wage/company/title trends | READY | API access working |
| Azure OpenAI embeddings model | READY | Deployed, key retrieved |
| PostgreSQL `talent_finder` | READY | Server running, need password |

### Profile Agent
| Data Source | Status | Action Needed |
|------------|--------|---------------|
| Dataverse `contacts` (5,152) | READY | API access working |
| Dataverse `accounts` (1,619) | READY | API access working |
| Dataverse `cfa_studentdetails` (2,139) | READY | API access working |
| Dataverse `cfa_employerdetails` (187) | READY | API access working |
| SQL `users` + `jobseekers` | RECOVERABLE | Load from BACPAC |
| SQL `companies` + `employers` | RECOVERABLE | Load from BACPAC |
| Blob Storage resumes (1,531) | READY | Connection string retrieved |
| Blob Storage images (104) | READY | Connection string retrieved |
| Azure AD B2C directories (3) | EXISTS | Need B2C admin access |

### Matching Agent
| Data Source | Status | Action Needed |
|------------|--------|---------------|
| SQL `skills` with 1536-dim embeddings | READY | Load into vector DB |
| SQL `JobRole` + `JobRoleSkill` | READY | Load from BACPAC |
| SQL `jobseeker_has_skills` | READY | Load from BACPAC |
| SQL `JobseekerJobPosting` (match schema) | READY | Use as schema template |
| Azure OpenAI `embeddings-te3small` | READY | Deployed, key retrieved |
| Azure OpenAI `chat-gpt41mini` | READY | For gap analysis/pitches |
| Dataverse `cfa_inferredskillses` (614) | READY | API access working |

### Career Services Agent
| Data Source | Status | Action Needed |
|------------|--------|---------------|
| SQL 6 Rating tables (99 skill dims) | READY | Load from BACPAC |
| SQL `CareerPrepAssessment` | READY | Load from BACPAC |
| SQL `CaseMgmt` + `CaseMgmtNotes` | READY | Load from BACPAC |
| Blob Storage resumes (1,531 PDFs) | READY | Connection string retrieved |
| Dataverse `cfa_mainresumeparsers` (8) | MINIMAL | Rebuild parser with AI |
| Dataverse resume skill entities | EMPTY | Build fresh with agent |
| CLTI integration | NOT STARTED | External dependency |

### College Pipeline Agent
| Data Source | Status | Action Needed |
|------------|--------|---------------|
| Dataverse `cfa_collegeprograms` (729) | READY | API access working |
| Dataverse `cfa_careerprograms` (3,940) | READY | API access working |
| Dataverse `cfa_eduinstitutions` (153) | READY | API access working |
| Dataverse `cfa_careerbridgedatas` (5,834) | READY | API access working |
| SQL `provider_programs` (26 cols) | READY | Load from BACPAC |
| SQL CIP/SOC mapping tables | READY | Load from BACPAC |

### Orchestrator Agent
| Data Source | Status | Action Needed |
|------------|--------|---------------|
| All agent APIs | DEPENDS | Build agents first |
| Logic App `SQLtoDynamics` definition | REFERENCE | Use as workflow template |
| Power Automate webhook | REFERENCE | Replace with agent routing |
| Events/communications data | READY | From SQL + Dataverse |

---

## 3. Reuse vs. Rebuild Assessment

### Reuse Immediately
| Asset | Value | Agent |
|-------|-------|-------|
| 5,034 skill embeddings (260 MB) | Skills taxonomy with vectors | Matching |
| Lightcast Open Skills IDs | Industry-standard skill identifiers | Market Intelligence |
| 1,531 resume PDFs | Career services asset | Career Services |
| 6 pathway rating schemas (99 dims) | Assessment framework | Career Services |
| CIP/SOC mapping tables | Education-to-occupation bridge | College Pipeline |
| Career Bridge data (5,834 records) | WA state program intelligence | College Pipeline |
| Azure OpenAI deployments | GPT-4.1 Mini + embeddings model | All agents |
| Dataverse entity model (163 entities) | Proven data structure | All agents |
| Job posting schema (34 columns) | Comprehensive job model | Market Intelligence |

### Rebuild as Agent Logic
| Component | Original | Agent Rebuild |
|-----------|----------|---------------|
| Matching algorithm | Next.js server-side (Prisma) | Matching Agent tool (Python + OpenAI) |
| Gap analysis | GPT field in match result | Career Services Agent with structured output |
| Resume parsing | Sovren/Dataverse (8 records) | Career Services Agent with GPT-4.1 document analysis |
| Elevator pitch generation | GPT field (barely used) | Matching Agent auto-generation |
| Resume tailoring | GPT field (barely used) | Career Services Agent tool |
| Job ingestion pipeline | Unknown (Lightcast data exists) | Market Intelligence Agent automated ingestion |
| SQL-to-Dynamics sync | Logic App (never ran) | Orchestrator Agent data sync |
| Portal authentication | Azure AD B2C + Next.js | Agent interface with B2C |
| Employer notifications | Office 365 via Logic App | Orchestrator Agent communications |

### Build Fresh
| Component | Reason | Agent |
|-----------|--------|-------|
| Placement tracking | `JobPlacement` table was empty | Career Services Agent |
| Employer engagement analytics | Bookmarks/feedback barely used | Profile + Matching Agents |
| Program-to-skill mapping | `provider_program_has_skills` empty | College Pipeline Agent |
| RAG pipeline | `RAGRecordManager` was empty | Career Services Agent |
| Multi-agent orchestration | Didn't exist before | Orchestrator Agent |
| Self-assessments | `sa_questions` etc. empty | Career Services Agent |

---

## 4. Integration Points Between Agents

```
[Market Intelligence Agent]
  ├── Provides: skills taxonomy, job demand signals, wage data
  ├── Consumed by: Matching Agent, College Pipeline Agent, Career Services Agent
  └── Updates: continuously via Lightcast + job ingestion

[Profile Agent]
  ├── Provides: unified student/employer profiles
  ├── Consumed by: Matching Agent, Career Services Agent, Orchestrator
  └── Updates: on user profile changes, resume uploads

[Matching Agent]
  ├── Provides: match scores, gap analysis, recommendations
  ├── Consumed by: Career Services Agent, Orchestrator
  ├── Depends on: Profile Agent (profiles), Market Intelligence (skills/jobs)
  └── Updates: on new jobs, profile changes, skill updates

[Career Services Agent]
  ├── Provides: readiness scores, upskilling plans, resume optimization
  ├── Consumed by: Matching Agent (re-score after upskilling), Orchestrator
  ├── Depends on: Profile Agent, Matching Agent (gaps)
  └── External: CLTI (careerslaunch.org) integration

[College Pipeline Agent]
  ├── Provides: program recommendations, talent pipeline forecasts
  ├── Consumed by: Orchestrator, Matching Agent
  ├── Depends on: Market Intelligence (demand), Matching Agent (skills taxonomy)
  └── Updates: on new program data, enrollment changes

[Orchestrator Agent]
  ├── Provides: unified query interface, workflow coordination
  ├── Consumed by: all user types (students, employers, staff, workforce boards)
  └── Depends on: all other agents
```

---

## 5. Where CLTI Fits

**CLTI (Nina Zhao / careerslaunch.org)** is an external career services capability layer.

- **Agent:** Career Services Agent
- **Integration point:** After the Matching Agent identifies gaps, the Career Services Agent can route students to CLTI for:
  - Interview preparation
  - Resume optimization (beyond AI generation)
  - Career coaching sessions
  - Skills gap closure programs
- **Data flow:** Career Services Agent sends student profile + gap analysis → CLTI provides coaching → outcomes feed back to Profile Agent → Matching Agent re-scores

---

## 6. Where JIE/Borderplex Fits

**JIE (Job Intelligence Engine) for Workforce Solutions Borderplex** IS the Market Intelligence Agent.

- **Deployment 001:** Borderplex (El Paso, TX region)
- **Data foundation:** 5,034 skills, 2,670 Lightcast jobs, CIP/SOC mappings, Career Bridge data
- **PostgreSQL `talent_finder`:** Already provisioned in Azure (created 2026-03-11)
- **Unique value for Borderplex:**
  - Real-time job demand signals for the border region
  - Skills gap analysis: what employers want vs. what programs teach
  - Talent pipeline forecasting: who's graduating with what skills, when
  - Wage trend analysis by occupation and region

**This is the fastest path to revenue.** The Market Intelligence Agent can be demonstrated to Borderplex within 2-3 weeks.

---

## 7. Which Agent Delivers the Fastest Waifinder Demo for Texas?

**Market Intelligence Agent — unequivocally.**

### Why:
1. **Data is ready today** — 5,034 skills with embeddings, Lightcast job data, Career Bridge, CIP/SOC mappings
2. **Infrastructure exists** — PostgreSQL server running, Azure OpenAI deployed
3. **No dependencies** — doesn't need other agents to function
4. **Direct revenue opportunity** — Borderplex is waiting for the JIE
5. **Compelling demo** — "What are employers asking for right now in El Paso?" is a powerful question to answer live

### Demo Scenario (2-3 weeks):
1. Load skill embeddings + Lightcast data into `talent_finder` PostgreSQL
2. Build Market Intelligence Agent with tools:
   - `search_jobs(query, region, skills)` — semantic job search
   - `get_demand_signals(region, timeframe)` — top skills, companies, wages
   - `compare_program_to_market(program_id)` — program alignment score
   - `forecast_demand(skill, region)` — demand trend prediction
3. Natural language interface: "Show me the top 10 skills employers in El Paso need that local programs don't teach"
4. Dashboard: regional demand heatmap, skills gap visualization, wage trends

---

## 8. Timeline Summary

| Week | Milestone |
|------|-----------|
| **1-2** | Market Intelligence Agent MVP (JIE for Borderplex) |
| **3** | Market Intelligence Agent demo to Borderplex |
| **3-5** | Profile Agent (unified student/employer profiles) |
| **5-8** | Matching Agent (skills matching + gap analysis) |
| **8-11** | Career Services Agent (resume parsing + readiness scoring) |
| **11-13** | College Pipeline Agent (program-to-market alignment) |
| **13-15** | Orchestrator Agent (multi-agent coordination) |
| **16** | Full Waifinder platform demo |

### Critical Path
Market Intelligence (wk 1-3) → Profile (wk 3-5) → Matching (wk 5-8) → Career Services (wk 8-11)

The College Pipeline and Orchestrator agents can be built in parallel with Career Services.

---

## 9. Technical Architecture Recommendation

### Per-Agent Stack
- **Language:** Python 3.11+
- **Framework:** Claude Agent SDK or custom agent framework
- **LLM:** Claude (orchestration + reasoning) + Azure OpenAI (embeddings + domain-specific)
- **Database:** PostgreSQL (talent_finder) for structured data + vector search
- **Blob Storage:** Azure Blob (resumes, images)
- **CRM:** Dataverse Web API (read/write profiles)
- **Auth:** Azure AD B2C (user authentication)
- **Hosting:** Azure Functions (serverless) or Azure Container Apps

### Data Architecture
```
[PostgreSQL: talent_finder]
  ├── skills (5,034 + vector embeddings)
  ├── job_postings (from SQL backup + live ingestion)
  ├── match_results (new — agent-generated)
  ├── readiness_scores (new — agent-generated)
  └── analytics_cache (new — pre-computed insights)

[Dataverse: cfahelpdesksandbox]
  ├── contacts (student/employer profiles — source of truth for CRM)
  ├── cfa_* entities (163 custom entities — operational data)
  └── Activity history (emails, tasks, journeys)

[Azure Blob Storage: careerservicesstorage]
  ├── resume-storage/ (1,531 PDFs)
  ├── image-storage/ (104 avatars)
  └── agent-outputs/ (new — generated reports, tailored resumes)

[Azure OpenAI: resumeJobMatch]
  ├── embeddings-te3small (vector generation)
  └── chat-gpt41mini (reasoning, generation)
```

---

## 10. Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| PostgreSQL password unknown | Can't access talent_finder DB | Reset password via Azure Portal or CLI |
| VM source code not recovered | Missing React app matching logic | Schema + BACPAC provide sufficient understanding |
| Azure Sponsorship subscriptions inaccessible | May have additional resources | Ask CFA IT admin for access |
| CLTI integration timeline | Career Services Agent delayed | Build agent without CLTI first, add integration later |
| B2C token migration | Users may need to re-authenticate | Support gradual migration with both old and new auth |
| Dataverse API rate limits | High-volume queries throttled | Cache frequently accessed data in PostgreSQL |
| Embedding model version mismatch | Old ada-002 vs new te3-small | Re-embed with te3-small for consistency (batch job) |

---

## Appendix: Complete Asset Inventory

### Credentials (stored in .env)
- Azure Tenant ID, WFD-OS Client ID/Secret
- Dataverse API access (both instances)
- Blob Storage connection string + key
- Azure OpenAI endpoint + key
- PostgreSQL host/user (need password)

### Data Volumes
- 5,152 contacts (Dataverse)
- 1,619 accounts (Dataverse)
- 5,034 skills with embeddings (SQL backup)
- 2,670 Lightcast jobs (Dataverse)
- 5,834 Career Bridge records (Dataverse)
- 3,940 career programs (Dataverse)
- 729 college programs (Dataverse)
- 1,531 resumes (Blob Storage)
- 76 SQL tables (BACPAC backup)
- 163 custom Dataverse entities

### Infrastructure
- 2 Dynamics CRM instances
- 3 Azure Blob Storage accounts
- 2 Azure OpenAI resources (4 model deployments)
- 1 PostgreSQL server
- 1 Ubuntu VM (Next.js app)
- 1 Function App (Python stub)
- 1 Logic App (SQL→Dynamics)
- 3 Azure AD B2C directories
- 1 Azure Communication Services (email)
- 4 Azure subscriptions (2 accessible)
- 40 model-driven apps, 2 portals, 20 chatbots
