# Phase 1j/1k/1l: React App, Power Automate, Power Apps Discovery
**Date:** 2026-04-02

---

## Phase 1j: React Application

### What We Know

| Fact | Detail |
|------|--------|
| Framework | Next.js (TypeScript) |
| ORM | Prisma (manages SQL schema) |
| Hosting | Ubuntu 22.04 VM (WatechProd-v2) |
| Auth | NextAuth (OAuth providers) + WebAuthn |
| Brand | "Tech Workforce Coalition" / WA Tech Coalition |
| Database | Azure SQL (now decommissioned) |
| Status | Running on VM but database disconnected |

### User Journeys (Inferred from Schema)

**Student journey:**
1. Register → users table (NextAuth)
2. Create profile → jobseekers table
3. Add education → jobseekers_education
4. Add work experience → work_experiences
5. Add projects → project_experiences + project_has_skills
6. Add skills → jobseeker_has_skills
7. Upload resume → Blob Storage (resume-storage)
8. Browse jobs → job_postings
9. Apply to jobs → JobseekerJobPosting
10. Featured in showcase → is_featured flag

**Employer journey:**
1. Register → users table
2. Company profile → companies + company_addresses
3. Employer profile → employers table
4. Post jobs → job_postings + _JobPostingSkills
5. Browse talent → jobseekers (showcase)
6. Bookmark candidates → bookmarked_jobseekers

**College journey:**
- Minimal direct integration
- Programs data (edu_providers, programs, provider_programs) was likely admin-managed

### Source Code Recovery

The React app source code has NOT been recovered. It runs on the
WatechProd-v2 VM in Azure. Recovery would require SSH access to the VM.

**Relevance to WFD OS:** The existing React app is the foundation for
the three portals (Student, Employer, College Partner). Understanding
its routes, components, and API endpoints would accelerate portal
modernization. However, the portals will be rebuilt to connect to
PostgreSQL rather than the decommissioned SQL database.

---

## Phase 1k: Power Automate Flows

### Discovery Status

Power Automate flows were not queried via API in this session.
Previous discovery (March 30) found:

| Finding | Detail |
|---------|--------|
| Logic App found | "SQLtoDynamics" — built but never executed |
| Purpose | Sync SQL database records to Dynamics CRM |
| Status | Never ran — zero execution history |
| Other flows | Not fully enumerated |

### Implication for WFD OS

Power Automate flows are being **replaced entirely** by the
Orchestrator Agent. No flows need to be preserved or replicated.
The flow definitions serve only as reference for understanding
intended business logic.

**Key flow to understand:** SQLtoDynamics attempted to sync data
from SQL → Dynamics. In WFD OS, the flow is reversed: Dynamics →
PostgreSQL (one-time migration), then PostgreSQL is system of record.

---

## Phase 1l: Power Apps

### Discovery Status

Power Apps were not queried via API in this session.
Previous discovery (March 30) found:

| Category | Count |
|----------|-------|
| CFA custom apps | 10 |
| Portal apps | 2 |
| Chatbots | 20 |
| Model-driven apps | 40 |

### Implication for WFD OS

All Power Apps are being **replaced** by:
- The three web portals (Student, Employer, College Partner)
- Agent interfaces (natural language via Orchestrator Agent)
- CFA staff dashboard (built on PostgreSQL data)

Power Apps provided internal staff UX for managing Dynamics data.
In WFD OS, staff interact through agent commands and purpose-built
dashboards rather than generic CRM forms.

**No Power Apps logic needs to be preserved.** The data they managed
is migrated from Dataverse; the UX is rebuilt as portals and agents.

---

## Combined Summary

| Legacy System | WFD OS Replacement | Migration Need |
|--------------|-------------------|----------------|
| React app (Next.js) | Modernized portals on PostgreSQL | Recover source for reference |
| Power Automate flows | Orchestrator Agent | Reference only |
| Power Apps | Agent interfaces + dashboards | Reference only |
| Copilot Studio connector | Direct agent interfaces | Not needed |
| SQLtoDynamics Logic App | Reversed: Dynamics → PostgreSQL | One-time migration |
