# Phase 5: Enrichment — SharePoint & Document Correlation
**Date:** 2026-03-30

---

## Executive Summary

CFA has **50+ SharePoint sites** with operational documents, employer engagement materials, candidate matching files, WJI data reports, and Waifinder strategy documents. The Career Services site alone contains **3.5 GB** of documents. Key finds include manual candidate-to-employer matching documents (13 employer folders), WJI labor market data, and the active Waifinder/Borderplex client folders.

---

## SharePoint Sites Relevant to WFD OS

### Tier 1: Directly WFD OS Related

| Site | URL | Storage | Relevance |
|------|-----|---------|-----------|
| **Career Services** | /sites/CareerServices | 3,565 MB | Career Services Agent — employer matching, job placement tracking, talent portal docs |
| **wAIFinder** | /sites/wAIFinder | 8.9 MB | Waifinder strategy, Borderplex client folder, CFA 2.0 business plan |
| **CFA - Waifinder** | /sites/CFAWaifinder | 1.4 MB | Waifinder project planning |
| **Employer Engagement** | /sites/EmployerEngagement | 225 MB | Profile Agent — employer relationship documents, events |
| **CFA Clients** | /sites/CFAClients | 2.2 MB | Client relationship data |
| **Building with Agents** | /sites/BuildingwithAgents | 1.4 MB | Agent architecture planning |

### Tier 2: Supporting Context

| Site | Relevance |
|------|-----------|
| CFA Operations (HR / Finance) | Grant agent already connected |
| WJI GJC Grant Project | Grant funding context for WJI |
| WJI Project Management | WJI delivery tracking |
| CFA Tech Sector Leadership | Industry partnership context |
| CFA Marketing | Marketing assets for Waifinder |
| CFA Board | Board-level strategy documents |
| AI Integrations Test | AI development testing |
| CFA Advisory Board Team | Advisory input |
| CFA Grants-DOL WANTO 2025 | Federal grant context |

---

## Key Document Discoveries

### 1. Preliminary Candidate Matching (Manual Process)
**Location:** Career Services / Job Placement / Preliminary Candidate Matching
**Files:** 13 employer-specific matching documents

| Employer | Size | Last Modified |
|----------|------|---------------|
| Aditi | 664 KB | 2025-07-30 |
| AI House | 223 KB | 2025-07-30 |
| Airbus | 156 KB | 2025-07-30 |
| Axon | 169 KB | 2025-10-07 |
| Brooksource | 110 KB | 2025-07-30 |
| ExtraHop | 255 KB | 2025-07-31 |
| Highspot | 320 KB | 2025-07-30 |
| Quadrant Technologies | 264 KB | 2025-08-18 |
| Sabey | 208 KB | 2025-09-09 |
| Seattle Art Museum | 128 KB | 2025-10-13 |
| TEKsystems | 642 KB | 2025-07-30 |
| WaFD Bank | 113 KB | 2025-08-07 |
| YuPro | 110 KB | 2025-09-05 |

**Insight:** This is the manual process that the Matching Agent will automate. Each file likely contains candidate profiles matched to employer requirements — the exact workflow the agent replaces.

### 2. WJI Labor Market Data
**Location:** Career Services / All / WJI Data

| Document | Size | Purpose |
|----------|------|---------|
| Coalition Employer Placements.xlsx | 83 KB | Placement tracking data |
| Portal Jobseekers - Coalition Members.xlsx | 104 KB | Active jobseeker roster |
| Provider Program Details.xlsx | 32 KB | Training program inventory |
| TP Provider Programs, Pathways, Roles, & Skills.xlsx | 34 KB | Program-to-skill mapping |
| Entry-Level Tech Labor Market Landscape (WA State) | 2.1 MB | State-level market analysis |
| Entry-Level Tech Labor Market (By Region) | 1.2 MB | Regional market breakdown |
| WJI Data Highlights.docx | 25 KB | Key data insights summary |

**Insight:** The "TP Provider Programs, Pathways, Roles, & Skills.xlsx" is the missing program-to-skill mapping that the `provider_program_has_skills` SQL table was supposed to contain but was empty. This spreadsheet likely has the data.

### 3. Waifinder Client Folders (Active — Updated Today)
**Location:** wAIFinder / Clients

| Client | Last Updated |
|--------|-------------|
| **WorkforceSolutionsBorderplex** | 2026-03-30 (TODAY) |
| CFA | 2026-03-30 (TODAY) |
| Testco | 2026-03-30 (TODAY) |

**Insight:** Borderplex is an active client. The folder was updated today, confirming this is a live engagement.

### 4. CFA 2.0 Strategy Documents
**Location:** wAIFinder / CFA 2.0

| Document | Size | Purpose |
|----------|------|---------|
| cfa-business-plan.docx | 29 KB | CFA business strategy |
| cfa-financial-model.xlsx | 27 KB | Financial projections |
| cfa-project-catalog.pdf | 34 KB | Project portfolio |
| cfa-strategy-v10.html | 179 KB | Strategy document v10 |
| ICPs/ | — | Ideal Customer Profiles |
| Marketing/ | 522 KB | Marketing materials |
| CFA Website/ | 55 KB | Website planning |

### 5. Dynamics Integration Documentation
**Location:** Career Services / Talent Portal
- **Dynamics Employer & Candidate Tracking + Integrations.docx** — Documents the integration between the Talent Portal and Dynamics CRM
- **Talent Portal Feedback & Action Points.docx** — User feedback on the portal
- **WATech Website Feedback.docx** — Website UX feedback (2.9 MB)

---

## Correlation with WFD OS Agents

### Profile Agent
- **Employer Engagement site** (225 MB): employer relationship documents, event materials
- **Candidate matching files**: manual profiles that should become automated agent profiles
- **Coalition Employer Placements.xlsx**: historical placement data missing from SQL

### Market Intelligence Agent
- **Entry-Level Tech Labor Market presentations**: regional demand analysis for WA state
- **WJI Data Highlights**: curated market insights

### College Pipeline Agent
- **TP Provider Programs, Pathways, Roles, & Skills.xlsx**: the program-to-skill mapping data
- **Provider Program Details.xlsx**: program inventory supplement

### Matching Agent
- **13 employer matching folders**: the manual matching process to automate
- **Portal Jobseekers - Coalition Members.xlsx**: active talent pool

### Career Services Agent
- **Career Services site** (3.5 GB): complete career services document library
- **Career Prep folder**: program documentation
- **Job Placement folder**: placement tracking documents

### Orchestrator Agent
- **Waifinder strategy docs**: system design context
- **Borderplex client folder**: active deployment context

---

## Recommendations

1. **Ingest the WJI Excel files** — Coalition Employer Placements.xlsx and Provider Programs spreadsheets contain data that fills gaps in the SQL/Dataverse records (especially the program-to-skill mapping)

2. **Use candidate matching docs as training data** — The 13 employer-specific matching files represent human expert matching decisions. These can train/validate the Matching Agent.

3. **Download the labor market presentations** — The WA state and regional market analysis slides contain curated insights for the Market Intelligence Agent.

4. **Monitor the Borderplex folder** — Active engagement materials; the Market Intelligence Agent should align with this client's needs.

5. **Archive Career Services docs** — 3.5 GB of operational documents can be indexed for RAG by the Career Services Agent (the RAGRecordManager table was empty — this is the content to fill it).
