# Waifinder — Workforce Development Operating System
## Product Overview
**Computing for All | March 2026**

---

## What Is Waifinder?

Waifinder is an AI-powered workforce development platform built by Computing for All (CFA). It connects four groups who have never been able to easily work together — **students, employers, colleges, and workforce boards** — through a set of intelligent agents that match talent to opportunity, identify skill gaps, and track career outcomes in real time.

The product domain is already registered: **thewaifinder.com**

---

## The Problem It Solves

Workforce development is broken in a predictable way:

- **Students** don't know which skills to build or which employers are hiring
- **Employers** can't find entry-level tech talent efficiently and don't know what colleges are producing
- **Colleges** don't know if their programs align with what employers actually need
- **Workforce boards** fund programs but have no real-time visibility into outcomes

CFA has spent five years collecting data on all four of these groups — 5,152 student profiles, 1,619 employer accounts, 729 college programs, 5,034 skills mapped to the labor market — but the intelligence layer to make sense of it was never fully activated. Waifinder activates it.

---

## What Waifinder Does

Waifinder answers the questions that workforce development professionals ask every day but can't currently answer quickly:

> *"Who are the top 10 students ready to interview for cloud engineering roles this month?"*

> *"What skills are employers in El Paso asking for that local programs don't teach?"*

> *"Which of our students are 30–60 days away from being job-ready?"*

> *"Show me every employer who browsed our talent showcase but never made a hire."*

> *"Which college programs have the best track record of placing graduates in tech jobs?"*

It does this through six specialized AI agents that each own a domain of the workforce development system.

---

## The Six Agents

### 1. Market Intelligence Agent
**What it does:** Tracks real-time labor market demand — what skills employers are posting for, which companies are hiring, what wages look like, and how demand is shifting by region and occupation.

**Why it matters:** Workforce boards and training programs are making multi-year investments based on outdated labor market data. This agent delivers live signals.

**First deployment:** Workforce Solutions Borderplex (El Paso, TX) — an active client. This is the Job Intelligence Engine (JIE) being built for the Texas border region.

---

### 2. Profile Agent
**What it does:** Maintains living, unified profiles for students and employers — pulling together data from the CRM, the career services portal, resume files, and the talent showcase into a single view of each person or company.

**Why it matters:** Student data currently lives in at least three separate systems (SQL database, Dynamics CRM, Azure Blob Storage resumes) with no unified record. The Profile Agent creates a single source of truth.

---

### 3. Matching Agent
**What it does:** Runs skills-based matching between students and job opportunities using AI embeddings. Computes a match score, identifies skill gaps, and generates a plain-language explanation of why a student is or isn't a strong fit for a role.

**Why it matters:** CFA was doing this matching manually — staff were building individual candidate documents for each employer (13 employer matching folders were found in SharePoint, each built by hand). This agent automates that process and scales it.

---

### 4. Career Services Agent
**What it does:** Takes the gap analysis from the Matching Agent and turns it into an action plan — an upskilling roadmap, a tailored resume, interview preparation, and a readiness score that updates as the student progresses.

**Why it matters:** 1,531 student resumes are sitting in storage, never analyzed at scale. Six career pathway assessment schemas (covering 99 skill dimensions) were built but barely used. This agent puts them to work.

---

### 5. College Pipeline Agent
**What it does:** Maps college and training programs to labor market demand — showing which programs produce graduates with the skills employers need, and which programs have alignment gaps.

**Why it matters:** Workforce boards fund training programs. They need to know which investments are paying off. This agent provides program-by-program demand alignment scoring.

---

### 6. Orchestrator Agent
**What it does:** The conversational front door to the entire system. A student, employer, staff member, or workforce board can ask a question in plain language, and the Orchestrator routes it to the right agents, gathers the answers, and responds.

**Why it matters:** This is what makes Waifinder feel like a single intelligent platform rather than a collection of disconnected tools.

---

## What's Already Built

CFA built a substantial workforce platform over five years that was never fully activated. Everything discovered is available to Waifinder:

| Asset | Volume | Status |
|-------|--------|--------|
| Student profiles | 5,152 contacts | Ready in Dynamics CRM |
| Employer accounts | 1,619 companies | Ready in Dynamics CRM |
| Skills taxonomy | 5,034 skills with AI embeddings | Ready (recovered from SQL backup) |
| External job listings | 2,670 Lightcast jobs | Ready in Dynamics CRM |
| College programs | 729 programs + 3,940 career programs | Ready in Dynamics CRM |
| Student resumes | 1,531 PDF files | Ready in Azure Blob Storage |
| AI models | GPT-4.1 Mini + text-embedding-3-small | Deployed in Azure OpenAI |
| Email infrastructure | Azure Communication Services | Live on thewaifinder.com |
| Career pathway assessments | 6 pathways, 99 skill dimensions | Ready in SQL backup |
| Labor market research | WA state + regional market reports | Ready in SharePoint |
| Manual matching files | 13 employer folders | Ready as training data |

---

## What's Being Built

The agents themselves — the intelligence layer that turns this data into answers and actions. Each agent is a Python service that connects to the existing data, uses Claude and Azure OpenAI for reasoning, and exposes a natural language interface.

**Build sequence (15 weeks):**

| Weeks | Agent | Key Deliverable |
|-------|-------|----------------|
| 1–3 | Market Intelligence | Live demo for Borderplex (El Paso) |
| 3–5 | Profile Agent | Unified student/employer profiles |
| 5–8 | Matching Agent | Automated skills matching + gap analysis |
| 8–11 | Career Services Agent | Readiness scoring + upskilling plans |
| 11–13 | College Pipeline Agent | Program-to-market alignment |
| 13–15 | Orchestrator Agent | Full platform, conversational interface |
| 16 | Full Waifinder demo | Launch-ready platform |

---

## Who It's For

**Primary customers (workforce boards):**
Organizations like Workforce Solutions Borderplex that fund and coordinate workforce development across a region. They pay for labor market intelligence, program alignment data, and talent pipeline visibility.

**Secondary users (within the platform):**
- **Students** — job matching, career coaching, resume optimization
- **Employers** — talent search, pipeline requests, candidate matching
- **Colleges** — program alignment scoring, talent pipeline visibility
- **CFA staff** — case management, coaching, outcome tracking

---

## Why Now

Three things came together that make this the right moment:

1. **The data exists.** Five years of CFA operations produced a rich dataset that has never been fully activated. The AI infrastructure (embeddings, models) is already deployed.

2. **The first client is waiting.** Workforce Solutions Borderplex is an active engagement. The Market Intelligence Agent can be demonstrated in 2–3 weeks using data that is ready today.

3. **The technology is ready.** Modern AI agents can do what would have required years of custom engineering in 2020. The Matching Agent alone — which required a full embedding pipeline and custom matching engine before — can now be built in weeks using Claude and Azure OpenAI.

---

## Technical Foundation

- **Language:** Python 3.11
- **AI:** Claude (reasoning + orchestration) + Azure OpenAI (embeddings + domain-specific)
- **Database:** PostgreSQL `talent_finder` (running in Azure) + Dynamics CRM
- **Storage:** Azure Blob Storage (resumes, documents)
- **Auth:** Azure AD B2C
- **Infrastructure:** Azure (already provisioned)
- **Domain:** thewaifinder.com (already registered, email configured)
