# Phase 1j/1k/1l: React App, Flows & Power Apps Discovery
**Date:** 2026-03-30

---

## Phase 1j: React Application

### VM: WatechProd-v2
- **Public IP:** 20.106.201.34
- **OS:** Ubuntu 22.04 (nginx/1.18.0)
- **VM Size:** Standard_B2s
- **Ports Open:** SSH (22), HTTP (80), HTTPS (443)

### Live App
- **URL:** https://20.106.201.34 (HTTPS serves Next.js app)
- **Title:** "Tech Workforce Coalition"
- **Framework:** Next.js (React SSR)
- **ORM:** Prisma (confirmed from _prisma_migrations in SQL backup)
- **Auth:** Azure AD B2C (3 directories: prod, staging, dev)
- **Status:** Only homepage responds; all other routes return 404
  - Likely requires authentication or the full app routes are behind B2C login
- **Source code:** On the VM filesystem (would need SSH access to pull)

### React App Database Schema (from BACPAC — 76 tables)
Built with Prisma ORM connecting to Azure SQL. Key user journeys:
- **Student:** register → profile → skills → resume upload → career prep assessment → job matching → gap analysis → placement
- **Employer:** register → company profile → job postings → talent showcase → bookmark → connect
- **Educator:** register → edu provider profile → programs → skills mapping

---

## Phase 1k: Power Automate / Logic App Flows

### Logic App: SQLtoDynamics
- **State:** Enabled
- **Created:** 2025-02-17
- **Last Run:** Never (0 runs in history)
- **Trigger:** "When an item is created (V2)" — SQL trigger
- **Actions:**
  1. Get rows from SQL (V2)
  2. Initialize variable
  3. Send email via Office 365
- **Connections:** SQL ("ReactPortalSqlProd"), Office 365
- **Purpose:** Was designed to sync new SQL records to Dynamics CRM and send email notifications
- **Status:** Built but never executed — the SQL-to-Dynamics sync was set up but never triggered

### Power Automate Webhook (from scoping agent)
- **URL:** `defaulta3c7a25740f243a993738bb5fc6862.f7.environment.api.powerplatform.com`
- **Flow ID:** 2212cfe841c946b1b441926b9d2e1b95
- **Purpose:** Scoping notification automation

### Assessment: Flows for Orchestrator Agent
The Logic App represents the intended business logic layer that the **Orchestrator Agent** will replace:
- SQL → Dynamics sync becomes agent-to-agent data flow
- Email notifications become agent-initiated communications
- The trigger pattern (event-driven) maps to agent orchestration

---

## Phase 1l: Power Apps Discovery

### Model-Driven Apps (40 total)

#### CFA-Built Apps (Active)
| App | Internal Name | Last Modified | Purpose |
|-----|--------------|---------------|---------|
| **CFA Admin (Model Driven)** | new_CFAAdmin | 2025-10-01 | Staff admin interface |
| **Career Prep** | new_CareerPrep | 2025-09-23 | Career preparation tracking |
| **Talent Portal** | cfatf_TalentFinder | 2025-09-19 | Talent finder/showcase |
| **CFA Career Services** | new_CFACareerServices | 2025-08-18 | Career services management |
| **CFA Higher Ed** | cfa_CFAHigherEd | 2024-11-26 | Higher education portal |
| **Lightcast Data** | cfa_LightcastData | 2024-09-26 | Labor market data viewer |
| **Discourse App** | cfa_DiscourseApp | 2024-12-09 | Forum integration |
| **CFA Dev** | cfa_CFADev | 2025-01-12 | Development/testing |
| **Project Admin App** | cfa_ProjectAdminApp | 2021-06-27 | Project management |
| **TF RP (Do not use)** | tf_TalentFinderReactPortal | 2025-03-10 | Deprecated React portal config |

#### Microsoft D365 Apps (Pre-built)
- Customer Service Hub, Sales Hub, Omnichannel, Copilot Service
- Nonprofit Hub, Fundraising, Constituents, Case Management
- Volunteer Management, Project Mgt. & Program Design

### Power Pages / Portal Websites (2)
| Portal | Domain | Status |
|--------|--------|--------|
| **CFA Jobs** (cfajobs) | cfajobs3.powerappsportals.com | Active |
| **CFA Forms** (cfaforms) | cfaforms.powerappsportals.com | Active |

### Web Roles (Portal Access Control)
- Authenticated Users (active on both portals)
- Administrators (active on both portals)
- Anonymous Users (active on both portals)

### Chatbots / Copilot Studio Bots (20 active)

#### CFA-Built Bots
| Bot | Purpose |
|-----|---------|
| **Profile Analyzer** | Analyzes student/contact profiles |
| **CFA Jobs 4 bot** | Job search assistant |
| **CFA Students bot** | Student support chatbot |
| **Analyze Contacts** | Contact analysis automation |
| **CFA Forms bot** | Form completion assistant |
| **Talent Assistant** | Talent matching/showcase bot |
| **Test Agent** | Testing (created 2026-01-22) |

#### D365 / Microsoft Bots
- Customer Service Operations Agent, Onboarding Agent
- D365 Sales agents (Stakeholder Research, Email Validation, Engage, Rating Generator, Close Agent)
- Quality Evaluation Agent, Knowledge Harvest
- Copilot in Dynamics 365 Sales

---

## Summary: What Gets Replaced by WFD OS Agents

| Current System | WFD OS Agent Replacement |
|----------------|--------------------------|
| CFA Admin (Model Driven) | Orchestrator Agent interface |
| Career Prep app | Career Services Agent |
| Talent Portal app | Matching Agent + Profile Agent |
| CFA Career Services app | Career Services Agent |
| CFA Higher Ed app | College Pipeline Agent |
| Lightcast Data app | Market Intelligence Agent |
| CFA Jobs portal | Market Intelligence Agent |
| CFA Forms portal | Orchestrator Agent |
| Profile Analyzer bot | Profile Agent |
| CFA Jobs bot | Market Intelligence Agent |
| CFA Students bot | Orchestrator Agent |
| Talent Assistant bot | Matching Agent |
| SQLtoDynamics Logic App | Orchestrator Agent sync |
| React App (Next.js) | Agent-first interfaces |
