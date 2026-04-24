# Coalition / Workforce — Audience View (v2)

*Date: April 20, 2026*
*Owner: Claude Code (read-only recon)*
*Version: 2 — substantive revision of v1 (`docs/coalition_workforce_audience_view.md`, preserved unchanged for reference)*
*Scope: Coalition/Workforce component of wfd-os, organized by audience served.*
*Status: AUTHORITATIVE as a read-only description of current code. Observations only — no reorganization proposals, no recommendations for immediate action.*

This version incorporates corrections and additions supplied by Ritu on
April 20, 2026. The broad shape of v1 is preserved. Major restructures
in this version:

- **New Section 4 (Funders)** — split out from v1's "Partners." Distinct audience with their own surfaces.
- **New Section 7 (Waifinder as operator)** — separate from "Consulting component." Covers Waifinder's *use* of the platform.
- **Section 1 (Intermediary staff) reframed.** The Recruiting Workbench's primary user is **Waifinder's placement staff**, not the intermediary customer's staff. This is a managed-service model, not SaaS-first, for now.
- **Section 2 (Students) reframed** as students / apprentices / trainees — broader, covering both legacy Coalition records and active Cohort 1 apprentices.
- **Dinah clarified** — historical Coalition case manager, laid off when strategy shifted. Coalition contracted AIEngage for placement verification. No current case-manager persona at Coalition.
- **Funder dashboard located.** Not one surface but three: `/coalition/client?token=wsb-001` (Borderplex-adapted client portal), `agents/reporting/dashboard/` (standalone Vite app for Alma), and the Finance cockpit's generated outputs for ESD (Andrew Clemons / Jenny). See §4.

Source branches inspected:
- **`feature/finance-cockpit`** — active Coalition/Workforce branch (Finance cockpit, Recruiting workbench, embeddings). Worktree at `C:\Users\ritub\Projects\wfd-os\.claude\worktrees\stupefied-tharp-41af25`.
- **`integrate/grant-compliance-scaffold`** + its uncommitted working tree in the main folder.
- **`claude/sleepy-wiles-f9fc04`** — the one-commit lifeboat for migrations 011–013.

The Vegas-era `development` baseline is treated as current only where it remains unreplaced by the branches above.

---

## Section 0 — What changed from v1

For readers who already saw v1, the material corrections:

| v1 said | v2 says (correction) |
|---|---|
| Recruiting Workbench is a Coalition-staff surface (unnamed placement specialist, possibly Leslie) | Recruiting Workbench is a **Waifinder-staff** surface. Waifinder runs placement as a managed service to intermediary customers (Borderplex today). Currently Ritu does this work, possibly with help. |
| Dinah not mentioned | Dinah was Coalition's **case manager** historically. Role was eliminated when Coalition pivoted away from direct employer engagement to tracking/verifying unreported provider placements for K8341 reporting. Verification work was contracted to **AIEngage** (found in Finance cockpit data as a CFA Contractor with $245K budget; credited with 256 recovered placements in Q1 2026 via LinkedIn outreach). |
| "WJI reporting is produced for funders but they don't use the platform directly" | **Incorrect.** Funders have real platform surfaces. Borderplex (Alma) has two: a client portal at `/coalition/client?token=wsb-001` and a standalone Vite dashboard at `agents/reporting/dashboard/`. ESD (Andrew Clemons + Jenny) has generated monthly outputs from the Finance cockpit. WJI is one of several funder-facing artifacts. |
| "Compliance / Quinn — designed only, no code" (from Phase 1 draft) | **Still wrong.** `agents/grant-compliance/` on `integrate/...` **is** Quinn, partially built (62 files, Alembic, QuickBooks OAuth, four agents, rule engine functional). |
| "Jessica module" is the Recruiting Workbench | Preserved from v1: architecture doc misnomer. Jessica is Waifinder's **Marketing specialist** (Consulting). The recruiting workbench serves Waifinder's placement staff (unnamed). |
| Borderplex lumped as a partner | Borderplex is a **customer-and-funder**: a workforce board funding Cohort 1 apprentices + a consulting client running an engagement with Waifinder. The relationship is integrated, not two separate tracks. |

The rest of v1 is preserved where still accurate.

---

## Section 1 — Intermediary staff (primary users)

Coalition/Workforce is built for intermediary staff. The **intermediary customer** is an organization whose job is connecting people with jobs while being accountable to funders: workforce boards, community colleges with career services, 501(c)(3) placement organizations, re-entry programs, training providers. CFA's Coalition program is the origin customer.

**What's important for v2:** staff roles divide into two buckets —

- **(A)** Staff who work *at* the intermediary (Krista, Bethany at CFA Coalition today)
- **(B)** Staff who work *at Waifinder*, providing services to the intermediary under contract (Ritu running placement matching today; future dedicated placement specialist)

The platform serves both buckets. Section 1 is about (A). Section 7 — new in v2 — covers (B).

### 1.1 Grant compliance / finance ops — **Krista** (CFA Coalition)

Unchanged from v1 except for cross-references. Preserved here for completeness.

**Persona note:** `agents/assistant/staff_agent.py` line 29 — "If user is krista (Finance): Lead with financial briefing — outstanding invoices, payroll status, grant burn rate."

**UI surfaces (on `feature/finance-cockpit`):**

| Route | File | State |
|---|---|---|
| `/internal/finance` | `portal/student/app/internal/finance/page.tsx` (+ `cockpit-client.tsx`) | **Built.** Server-component wrapper parallel-fetches `/cockpit/status` + `/cockpit/hero` + `/cockpit/decisions` from :8013. Rich cockpit UI: hero tiles, decisions list, per-tab content (Decisions / Providers / Transactions / Reporting / Audit / High Priority), polymorphic drill. |
| `/internal/finance/operations` | `portal/student/app/internal/finance/operations/page.tsx` (+ `finance-client.tsx`) | **Skeleton + cross-branch coupling** — frontend expects grant-compliance backend at `http://localhost:8000/api/grant-compliance/*`. Backend is `agents/grant-compliance/` which lives on `integrate/grant-compliance-scaffold`, not on this branch. |

**Backend services:**

| Service | File | Port | State |
|---|---|---|---|
| Finance cockpit API | `agents/finance/cockpit_api.py` | :8013 | **Built.** Routes: `/cockpit/status`, `/cockpit/hero`, `/cockpit/decisions`, `/cockpit/tabs/{tab_id}`, `/cockpit/drills/{key}`, `/cockpit/refresh`, `/health`. Data from Excel fixtures. |
| Excel data source | `agents/finance/data_source.py` | — | **Built.** Wraps `design/cockpit_data.py::extract_all`. QB switch is a one-line change. |
| HTML generators | `agents/finance/design/generate_cockpit.py`, `cockpit_template.html`, `CFA_Cockpit.html` | — | **Built** (design-time artifacts). |

**Data dependencies:**
- Excel fixtures in `agents/finance/design/fixtures/` (gitignored): `GJC Contractors 2024`, `K8341 GJC CFA WTWC Exh B`, `K8341_Cost_Per_Placement`, `K8341_Provider_Reconciliation_v3_3-27`, `WJI TWC Candidate Tracking`.
- Postgres tables relevant to Krista but not yet wired in: `wji_payments` (10 rows), `wji_placements` (7 rows), `wji_upload_batches`.

**Gaps / pain points (unchanged from v1):**
1. Excel is the source of truth. No persistence of cockpit state to Postgres; no audit trail.
2. `operations/` sub-page cross-branch-broken — finance frontend needs the grant-compliance backend that lives on a different branch.
3. No write-back from `/wji` dashboard into cockpit.
4. No connection from placements-in-recruiting to placements-in-finance.

**Generalizability:** Every intermediary customer will have a Krista-equivalent role (someone who owns grant compliance + finance). The cockpit is currently K8341-specific in its fixture data but the shell is generalizable. Provider names (WTIA, ESD 112, NCESD, Ada, Vets2Tech, Apprenti, Per Scholas, etc.) and grant metrics (730 PIP threshold, $4.875M budget) are all wired as fixture data, not hard-coded in UI.

### 1.2 Grants / provider operations — **Bethany** (CFA Coalition)

Unchanged framing from v1. New in v2: clarification that `agents/grant-compliance/` is Bethany's actual backend, and is probably what the architecture doc means by "Compliance / Quinn."

**Persona note:** `agents/assistant/staff_agent.py` line 31 — "If user is bethany (Grants): Lead with grant briefing — placement count toward 730 PIP threshold, provider status, ESD deadlines."

**UI surfaces:**

| Route | File | State |
|---|---|---|
| `/wji` | `portal/student/app/wji/page.tsx` | **Built** (Vegas-era). 556-line Excel-upload UI + summary stats. Used by grant partners (uploaders) and by Bethany (reviewer) — **mixed audience, no staff-specific partitioned view**. |

No staff-specific workbench for Bethany beyond this plus the staff agent's role-aware briefing.

**Backend services:**

| Service | File | Port | State |
|---|---|---|---|
| WJI grant dashboard API | `agents/portal/wji_api.py` | :8007 | **Built.** 6 routes. |
| Grant file ingestion (SharePoint) | `agents/grant/api.py` + `agents/grant/{database,ingestion,queries,reconciliation}/` | unknown port | **Built** (Vegas-era). Separate from `wji_api.py`. Handles SharePoint-sourced grant documents + reconciliation of partner submissions. |
| **`agents/grant-compliance/`** — 62 files on `integrate/grant-compliance-scaffold` only | 62 files | :8000 (per README, not running on main folder today) | **Partially built.** Functions: Transaction Classifier (skeleton), Time & Effort (skeleton), Compliance Monitor (**rule engine ready**), Reporting (skeleton). 8 API route modules: allocations, compliance, grants, qb_oauth, reports, time_effort, transactions. QuickBooks OAuth live (sandbox sync working per `integrate/...` commit `50f5c20`). MS Graph evidence integration. |

**Data dependencies:**
- `wji_placements` (7 rows), `wji_payments` (10 rows), `wji_upload_batches`.
- `grant-compliance` has its own Alembic-managed schema within the same Postgres database: grants, allocations, transactions, time certifications, compliance flags, report drafts, QB OAuth tokens.
- Excel baselines — Partner_Data_Outcomes_Summary.xlsx, K8341_Provider_Reconciliation_v3_3-27.xlsx (per `CFA_GRANT_CONTEXT.md`).

**Is grant-compliance what becomes Quinn?** Flagging this explicitly per v2 prompt:

- The architecture doc describes **"Compliance / Quinn — AI assistant for federal grant compliance management. Agent that helps staff handle provider subawards, grant documentation, compliance workflows. Scoped narrowly to K8341 initially. Status: Designed (design conversations held, not yet built)."**
- `agents/grant-compliance/README.md` describes: **"A grant-accounting and federal-compliance assistant that sits on top of QuickBooks. It proposes grant tagging for transactions, drafts time & effort certifications, runs 2 CFR 200 compliance checks, and generates funder-report drafts — always with a human in the loop and a full audit trail."**
- These descriptions map 1:1. Both are K8341-scoped; both target provider subawards (allocations, transactions routes); both deal with compliance workflows; both promise human-in-the-loop with audit trail.
- **Conclusion: `agents/grant-compliance/` is the Quinn module as partially built.** The Phase 1 draft's "designed only" was incorrect as of April 17 (the scaffold import commit `98999f8`).

**Gaps / pain points (unchanged from v1 + one new):**
1. Bethany has no dedicated UI; she uses `/wji` (shared with partners) + agent briefing.
2. Grant-compliance app is orphaned on a disjoint-history branch, never pushed.
3. 730 PIP threshold is in the agent's briefing template but not a cockpit metric.
4. Two overlapping grant subsystems (`agents/grant/` and `agents/grant-compliance/`) with no cross-references. *New observation:* the two serve overlapping workflows for the same staff person (Bethany) but do not yet share data or UI.

### 1.3 Historical — **Dinah** (CFA Coalition, role eliminated)

**Persona note:** v2 context: Dinah was Coalition's case manager. CFA Coalition's original strategy involved direct employer engagement. That strategy did not work. Coalition pivoted to **tracking and verifying unreported provider placements** for K8341 reporting — the provider "recovery" work (finding placements already made that hadn't been reported up the chain). Dinah's case-manager role was not needed for the new strategy and she was laid off.

**What evidence is in the code:**

- **No `Dinah` references anywhere in code or docs** — consistent with her having left before any code named her.
- `agents/finance/design/cockpit_data.py` references **AI Engage** (an external contractor) in the **CFA Contractors** category with a **$245,000 budget for "Recovery Operation"** (line 256). Line 936 note: *"AI Engage attributed with 256 placements recovered in Q1 2026 via LinkedIn outreach."* This is the work that replaced Dinah's role — outsourced verification of unreported provider placements.
- `agents/finance/design/cockpit_data.py` line 27: `"CFA CONTRACTORS — incl AI Engage": "cfa_contractors"` (budget category mapping).
- `agents/finance/design/cockpit_data.py` line 329: `"Recovery Operation — AI Engage + Pete & Kelly Vargo"` — named combined drill entry.

**Implication for Coalition/Workforce audience:** CFA Coalition today has **no case manager on staff**. The two active CFA Coalition staff personas in code are Krista (Finance/Compliance) and Bethany (Grants/Providers). Case-management-equivalent work is either (a) handled by Waifinder's placement operation for Borderplex-funded apprentices, or (b) contracted to AIEngage for provider-recovery verification. There is no internal case-manager cockpit needed today, though future intermediary customers with a classic case-management model might want one.

The wtc `CaseMgmt` + `CaseMgmtNotes` models noted in the Phase 1 draft still exist in wtc but have no forward-port on any wfd-os branch. v2 treats this as **intentionally deferred**, not overlooked.

### 1.4 Operations / leadership — **Ritu, Gary**

**Persona notes:** `staff_agent.py` lines 25, 27 — Ritu (CEO): "big picture in 60 seconds." Gary (Tech Lead): "cohort briefing, who's stuck, sprint status."

**UI surfaces:**

| Route | File | State | Notes |
|---|---|---|---|
| `/internal` (root) | `portal/student/app/internal/page.tsx` | **Built — wrong audience.** Consulting Inquiries triage view (Jason BD). Does not serve leadership. |
| CEO/leadership dashboard | N/A | **Not built.** Conversational-only via staff agent. |
| Cohort/sprint briefing | N/A | **Not built.** Gary's cohort view is agent-only. |

**Backend:**

| Service | File | Notes |
|---|---|---|
| Staff agent (role-aware) | `agents/assistant/staff_agent.py` | **Built.** Role-aware via `?user=` query. Tools: `_get_grant_summary`, `_get_consulting_pipeline`, `_get_cohort_status`, `_get_placement_summary`, `_get_recent_inquiries`, `_draft_update`. |

**Gaps (unchanged from v1):**
1. Leadership view is conversational-only. No visual cockpit.
2. `/internal` root renders Consulting Inquiries (Jason) instead of a leadership or cross-cockpit landing.

### 1.5 Named staff with no role description — **Leslie**

**Still unknown.** Listed in `CLAUDE.md` line 407 as a staff agent user; not in `staff_agent.py`'s role-briefing template. No UI, no backend, no briefing. v2 carries v1's flag forward — Leslie's role in the platform is undefined in code.

### 1.6 Summary — intermediary staff

| Role | Person | Org | Primary UI | Primary backend | State |
|---|---|---|---|---|---|
| Grant compliance / finance ops | Krista | CFA Coalition | `/internal/finance` | `finance/cockpit_api.py` :8013 | Built; Excel-sourced |
| Grants / provider ops | Bethany | CFA Coalition | `/wji` (shared with partners) | `portal/wji_api.py` :8007 + `grant/api.py` + `grant-compliance/` :8000 | Built (WJI); grant-compliance orphaned on branch |
| Case management (historical) | Dinah | CFA Coalition | — (role eliminated; work contracted to AIEngage) | — | Not built; intentionally deferred |
| Operations / leadership | Ritu, Gary | CFA / Waifinder | — (staff agent only; `/internal` root miscast) | `assistant/staff_agent.py` :8009 | Conversational only |
| Unknown | Leslie | unclear | — | — | Undefined |

Note: the Recruiting Workbench — which looks like an intermediary-staff surface by its location at `/internal/recruiting/` — is covered in §7 (Waifinder as operator), since its actual user is Waifinder's placement staff, not the intermediary's own team.

---

## Section 2 — Students / apprentices / trainees (secondary users)

v2 broadens "students" to reflect three distinct populations:

- **Coalition students (legacy)** — 4,727 records migrated from Dataverse into Postgres. Mostly dormant: 3% have parsed resumes, 0% are showcase-eligible, 86% have `pipeline_status='unknown'`. These are the historical CFA Coalition pipeline.
- **Cohort 1 apprentices** — active, in training at Waifinder today. Funded by Borderplex. Actively doing curriculum + OJT on consulting engagements. Named in the code's demo fixtures (Angel Rodriguez, Fabian Martinez; more in CLAUDE.md: Bryan, Emilio, Juan, Enrique, Fatima, Nestor). Currently NOT tracked via the `students` table — tracked via `engagement_team` with `is_apprentice=true` on the Borderplex engagement `wsb-001`.
- **Future cohorts** from other workforce customers — architecturally anticipated. Not yet represented in code.

### 2.1 Student-facing portal

Unchanged from v1. `portal/student/app/student/page.tsx`, `student_api.py` on :8001, 8 dashboard components under `components/dashboard/`.

Serves Coalition students (legacy) primarily. **Does not currently serve Cohort 1 apprentices**: apprentices don't have `students.id` records; their progression is tracked only via engagement team membership. A Cohort 1 apprentice cannot log into `/student?id=<their-uuid>` and see their own journey.

### 2.2 Cohort / apprentice tracking — **partially built, data-model-gapped**

**Where apprentice data lives today:**

- `consulting_engagements.cohort_id` — VARCHAR(100) column on the engagements table. Links an engagement to a cohort. (Row count not verified.)
- `engagement_team` table — has `is_apprentice` boolean. Rows look like `{member_name, role, is_apprentice, skills, avatar_initials, engagement_id}`.
- `agents/portal/consulting_api.py` lines 227, 295–296 — queries `engagement_team`, returns `{team: [non-apprentices], apprentices: [apprentices]}` via two separated lists.
- `students.cohort_id` — column exists (`scripts/001-create-schema.sql` line 48). But NOT populated for Cohort 1 apprentices (who are not in `students`).

**Where apprentice data is NOT yet:**

- No `apprentices` or `cohort_members` dedicated table.
- No training-milestone tracking. `students.training_milestones_completed` column exists per CLAUDE.md but isn't populated.
- No OJT hours tracking. `staff_agent.py` line 83 explicitly says: *"source: 'static (OJT tracking not yet built)' ... 'note: OJT timesheet tracking not yet in WFD OS. Ask Gary for current sprint status.'"*
- No cohort-level cohort progress dashboard for internal staff (see §7.3).
- `portal/student/app/coalition/client/client-view.tsx` lines 497–525 — the **Funded Participants** section that displays apprentice readiness (Angel at 85%, Fabian at 82%) has these values **hardcoded** in the React component, not pulled from a database. A demo-time stub.

**Implication:** Cohort 1 apprentices are visible in the Borderplex client portal as funded participants, but the data is hand-written in the page. Real cohort tracking infrastructure does not yet exist.

### 2.3 Public arrival / intake

`portal/student/app/careers/page.tsx` — 282-line landing + intake form. Built (Vegas-era). Primary audience: Coalition students. Does not handle the "paste a job + upload resume + get instant gap analysis" public-arrival flow that the architecture doc describes; that remains designed-only.

### 2.4 Gap analysis (student-visible)

Backend + student-dashboard preview built (unchanged from v1). Full detail page not built.

### 2.5 Match narratives (student-visible)

**Not built** on any of v2's in-scope branches. Table exists with 0 rows.

### 2.6 Upskilling / learning resource discovery

**Designed only.** Unchanged.

### 2.7 Summary — student/apprentice/trainee audience

Three populations, uneven serving:

| Population | Primary surface | State |
|---|---|---|
| Coalition students (4,727 legacy) | `/student?id=<uuid>` | UI built; data mostly dormant (3% parsed, 0% showcase-active) |
| Cohort 1 apprentices (Angel, Fabian, etc.) | `/coalition/client?token=wsb-001` (as seen by Alma, not by the apprentice) | Displayed as hardcoded demo data in client portal; no self-serve portal |
| Future cohorts | — | Designed in architecture doc only |

---

## Section 3 — Employers (secondary users)

v2 integrates the prompt's framing: employer-audience is broader than v1 suggested. Includes:

- **SMB clients of Waifinder's consulting** who become placement destinations. Alma's 4 SMB introductions in the Borderplex region fit here.
- **The 19 districts** whose open jobs Alma shared with Waifinder.
- **Generic employers** discovering candidates via the Talent Showcase.
- **Consulting clients (Borderplex, future)** who end engagements with the option to hire the apprentice(s) who worked on their project — the integrated model.

### 3.1 Talent showcase

Unchanged from v1. `portal/student/app/showcase/page.tsx` (404 lines), `showcase_api.py` on :8002. Functionally built; catalog is essentially empty (0 students with `showcase_active=true`, 151 with `resume_parsed=true`, 71 with `completeness >= 0.7`).

**Honest assessment:** Works for Coalition students in principle. Does not currently surface Cohort 1 apprentices (they are not in `students` with showcase eligibility flags). An employer browsing the showcase today cannot find Angel or Fabian.

### 3.2 `/for-employers` landing

Unchanged. Marketing page, no interactive employer account.

### 3.3 Employer-as-consulting-client placement path

*New in v2.* The integrated business model has a flow the Coalition code has to support but doesn't cleanly yet:

- Borderplex engages Waifinder for a fixed-price consulting engagement (`consulting_engagements` row, `wsb-001`).
- Apprentices are assigned to the engagement team (`engagement_team.is_apprentice=true`).
- Near engagement end, the client has the option to hire an apprentice who has been embedded in their transformation.

**Code visibility:** The Borderplex client portal (`/coalition/client?token=wsb-001`) surfaces this in two places:
- **"Your talent pipeline"** card (lines 449–485 of `client-view.tsx`) — "The engineers on your project are available to hire when complete." With a CTA "Interested in hiring from your team?" that opens a mailto to the CFA lead.
- **"Your Funded Participants"** card for Borderplex-funded participants (lines 492–527) — "Available for placement anywhere in the US."

**Limitation:** The mailto-based handoff to `ritu@computingforall.org` is literally a human handoff. There is no programmatic flow to convert engagement→placement, no shortlist, no offer tracking, no placement fee automation. The integration is visible in the UI but unserved by the data model.

### 3.4 Employer-facing messaging

**None.** `agents/portal/email.py` is used by Scoping, not employer outreach.

### 3.5 Employer agent

`agents/assistant/employer_agent.py` provides a conversational surface on `/showcase` and `/for-employers`. Tools per CLAUDE.md: `search_candidates`, `get_candidate_profile`, `get_proof_of_work`, `submit_consulting_inquiry`, `get_case_study`. Routes an interested employer toward either a candidate match or a consulting inquiry — i.e., deliberately blurs hiring and consulting as adjacent paths.

### 3.6 Summary — employer audience

Employers have **browse + chat**, no account, no workflow. The integrated consulting→placement path is visible but functionally manual. SMB-introductions-from-Alma are not explicitly tracked as a distinct pipeline in any table I can find; they appear to flow via the general consulting inquiries path (`project_inquiries` table, 8 rows).

---

## Section 4 — Funders (new section, formerly in v1 Partners)

Funders are a distinct audience. They fund the work and expect outcomes visibility. They do not operate the platform the way staff do.

Primary named funder users:
- **Andrew Clemons** (ESD Contract Manager, `Andrew.Clemons@esd.wa.gov`) — K8341 oversight, attends the April 18 PIP meeting.
- **Jenny** at ESD — mentioned in Finance cockpit `activity-feed.tsx` line 10: *"Generated April monthly placement dashboard for Andrew & Jenny."* Full title not in code.
- **Alma** at Workforce Solutions Borderplex (`alma@wsborderplex.com` per `agents/scoping/runner.py`) — funds Cohort 1 apprentices; primary contact for the Borderplex engagement.

### 4.1 The Borderplex client portal (`/coalition/client?token=wsb-001`) — Alma's surface

**UI surface:** `portal/student/app/coalition/client/page.tsx` + `client-view.tsx` (719 lines). Server-component wrapper fetches engagement data + SharePoint documents.

**Backend:** `agents/portal/consulting_api.py` endpoints at lines 195 (`/api/consulting/client/{client_id}`) and 317 (`/api/consulting/client/{client_id}/documents`). Port :8003.

**Port note:** `page.tsx` line 11–12 hard-codes `http://localhost:8006/api/consulting/client/${token}` — **this is a bug.** `consulting_api.py` actually binds to :8003; `next.config.mjs` lines 23–24 rewrite `/api/consulting/:path*` to :8003 (not 8006). The server-side initial fetch to :8006 fails; the client-side fetch through the rewrite works. First-paint is the SSR fallback, subsequent loads work. Flagging as a small defect, not correcting.

**State:** **Built** as a functional demo surface. WSB-specific content (Cohort 1 apprentice names, readiness scores, skills, salary projections) is partially hardcoded in `client-view.tsx`.

**What it shows Alma (sections in the page, for Borderplex-id engagement `wsb-001`):**

| Section | Backed by | State |
|---|---|---|
| Engagement basics (project name, lead, description) | `consulting_engagements` row | Live |
| Milestones | `engagement_milestones` table | Live |
| Team + apprentices | `engagement_team` table | Live |
| Client-visible activity feed | `engagement_updates` where `is_client_visible=TRUE` | Live |
| Deliverables + documents | `engagement_deliverables` + SharePoint via MS Graph | Live (documents from SharePoint) |
| Budget | `consulting_engagements.budget_*` fields | Live |
| **Talent pipeline card** | `engagement_team.is_apprentice=true` | Live-data-driven |
| **Funded Participants card** (Cohort 1 apprentices with readiness + salary projection) | **Hardcoded demo data** in the React component | Not live |
| **Outcomes for Your Board** ($25,500 investment, 2 placements projected ROI, 83% job readiness up from 20%) | **Hardcoded demo data** | Not live |
| **Your Regional Labor Market** (top skills + open roles + trend) | **Hardcoded demo data**; comment says "Powered by the Job Intelligence Engine" | Not live |
| Project documents | SharePoint via `agents/graph/sharepoint.py` | Live |

**Audience fit:** This page gives Alma everything a funder wants — outcomes for her board, visibility into funded participants, regional labor market lens, document trail. It is the richest funder surface today. The catch is that most of the funder-facing value is currently **demo-hardcoded** rather than driven by data.

### 4.2 Borderplex standalone dashboard (`agents/reporting/dashboard/`) — Alma's second surface

**UI surface:** Vite + React 19 + Tailwind app at `agents/reporting/dashboard/`. Not part of the main Next.js portal. Has its own `package.json`, own build. Header reads **"Waifinder · Borderplex Labor Market Intelligence — Workforce Solutions Borderplex — Prepared for Alma | Updated {lastUpdated}"**.

**Backend:** `agents/reporting/api.py` on :8000. 5 endpoints:
- `/api/overview` — summary statistics
- `/api/skills` — skills demand by category
- `/api/pipeline` — talent pipeline breakdown
- `/api/gaps` — skills-gap signals
- `/api/jobs` — job listings for the region

**State:** **Built.** Three panels + a query interface:
- `DemandPanel` (labor market demand)
- `PipelinePanel` (talent pipeline, funded-participants summary)
- `GapPanel` (skills-gap view)
- `QueryInterface` (chat-style query, based on the import in `App.tsx`)

**Data source:** Per `scripts/008-skills-demand-report.py` (line 4): *"First output for Alma at Workforce Solutions Borderplex. Generate skills demand report from Lightcast job listings. Parses the cfa_skills field (comma-separated) from legacy_data."* Lightcast Q3–Q4 2024 job listings + `job_listings` table.

**Audience fit:** This is Alma's "market intelligence" surface — the JIE-facing view. Distinct from the client portal (which is engagement-specific) — this one is region-specific. Complementary rather than redundant.

**Deployment note:** This dashboard is a second React codebase inside the repo, separate from `portal/student/`. No shared components or auth. Called out in prior branch-reality-map Section 3.5.C as a surface Gary's `refactor/staging` doesn't alter.

### 4.3 ESD (Andrew + Jenny) — generated outputs, not a live dashboard

**No dedicated UI page for ESD.** ESD's funder view is delivered as **generated monthly artifacts** that Krista / Bethany / Ritu produce from the Finance cockpit and send to Andrew + Jenny.

Evidence in code:
- `portal/student/app/internal/finance/components/cockpit-shell/activity-feed.tsx` line 10: *"Apr 15 — Agent — Generated April monthly placement dashboard for Andrew & Jenny."*
- `agents/finance/design/design_notes.md` lines 17–18: *"Funder | Washington State Employment Security Department (ESD)"*, *"ESD Contract Manager | Andrew Clemons (Andrew.Clemons@esd.wa.gov)"*.
- `agents/finance/design/design_notes.md` line 251: *"{priority: HIGH, owner: Ritu / Andrew ..."* — ESD contact as drill action owner.
- `agents/finance/design/cockpit_data.py` tracks: ESD-directed contract terminations (3 providers), quarterly placements toward 730 PIP threshold, provider-level reconciliation.

**ESD's experience:** Andrew and Jenny receive monthly outputs. They do not have a web account. The Finance cockpit is **Krista's view of ESD's oversight** — it tracks the data ESD cares about, but ESD staff don't log in. This aligns with the prompt: "Alma at Borderplex uses (or will use) a Borderplex-adapted version of this funder dashboard" — implying ESD's version is an **output pipeline**, not a platform surface.

### 4.4 Funder summary — 3 modalities

| Funder | Org | Primary surface | Form factor | State |
|---|---|---|---|---|
| Alma | Workforce Solutions Borderplex | `/coalition/client?token=wsb-001` + `agents/reporting/dashboard/` :8000 | Two web dashboards (client-portal + labor-market) | Built; some sections demo-hardcoded |
| Andrew Clemons | WA State ESD (K8341 contract manager) | Monthly generated placement dashboard output | Reports, not a web page | Built as generation; not a live surface |
| Jenny | WA State ESD | Same as Andrew | Reports | Same |
| Future funders | various | Borderplex-style client portal is the template; ESD-style output-only is the lightweight fallback | TBD | Pattern visible, scaling work not done |

Funders are a real audience with real surfaces. The v1 framing ("funders are report recipients, not platform users") was wrong.

### 4.5 Gaps specific to the funder audience

1. **"Outcomes for Your Board"** card is hardcoded demo data. For v1 with Borderplex, that's arguably OK; for v1.1 (a second funder) the data model behind this card does not yet exist. Fields that would need to come from live data: `invested_amount`, `projected_placements`, `avg_job_readiness_uplift`, `skills_gained`.
2. **"Your Regional Labor Market"** is hardcoded. The JIE could feed this, but the wiring from `agents/reporting/api.py` → `/coalition/client/:token` view does not exist today.
3. **ESD output pipeline is manual.** The monthly dashboard is generated by agent/Krista, not auto-published to a funder-viewable URL.
4. **No shared funder model.** Each funder is its own one-off: Alma via consulting engagement, Andrew/Jenny via monthly reports. No `funders` table, no `funder_engagements` table, no templated report delivery.
5. **Multi-funder customer support.** A future intermediary customer with multiple funders would need a way to slice outcomes by funder. No such slicing exists.

---

## Section 5 — Operational partners (narrower than v1)

v2 tightens this section. Funders moved to §4. Operational partners are narrower: **colleges** and **provider subawardees**.

### 5.1 College partner portal

Unchanged from v1.

**UI surfaces:** `portal/student/app/college/page.tsx` (+ `/college/login/page.tsx` for token entry). 312 lines + 91 lines.
**Backend:** `agents/portal/college_api.py` on :8004. `GET /api/college/dashboard/{token}`.
**Data:** 2 partners in `college_partners` (Bellevue College, North Seattle College). 4,669 programs in `college_programs`. 10,754 rows in `program_skills`. ILIKE matching of students to institutions.
**Support:** `agents/college-pipeline/map_programs_to_skills.py` — offline program-to-skills mapper.

**State:** Built (Vegas-era). Read-only. Fuzzy matching limits coverage.

### 5.2 Provider subawardees

Providers are real partners per CLAUDE.md and the Finance cockpit data. The K8341 grant has multiple training providers (Ada, Vets2Tech, Apprenti, Code Day, Per Scholas, Year Up, WABS†, NCESD†, Riipen†, WTIA, ESD 112, I&CT Bellevue College, DynaTech Systems; † = ESD-terminated).

**UI surface:** none dedicated. Providers surface as rows in the Finance cockpit's Providers tab (6 providers visible in `/cockpit/status.tab_counts.providers`).

**Data:** Provider rates in `CFA_GRANT_CONTEXT.md`. Provider reconciliation in `K8341_Provider_Reconciliation_v3_3-27.xlsx` fixture. `wji_placements.vendor` holds provider identity.

**Audience reality:** Providers are **the objects of staff work**, not users. A provider doesn't log into anything. They send invoices (via email/SharePoint) that Bethany and Krista reconcile. The platform is a ledger of provider performance; it is not a provider-facing tool.

**Contrast:** If Waifinder ever onboards the providers themselves as customers of wfd-os (a provider licensing the platform to run their own operations), that would be a different relationship. Today they are subawardees, not platform customers.

### 5.3 AIEngage (contractor, not a partner)

Worth naming here because v2's prompt flagged it. AIEngage is a **contractor** CFA hired for placement-recovery verification ($245K budget per `cockpit_data.py`; 256 Q1 2026 placements attributed via LinkedIn outreach). They are represented in the Finance cockpit as a CFA Contractor row, not as a platform user. AIEngage's staff do not log into wfd-os. They are a service provider whose outputs show up as data in Krista's and Bethany's views.

### 5.4 Summary — operational partners

| Partner | Surface | State |
|---|---|---|
| Colleges | `/college?token=<...>` + `/college/login/` | Built, read-only |
| Provider subawardees | — (objects of staff work, not users) | Tracked in data; no partner surface |
| Contractors (AIEngage) | — (data-only, in Finance cockpit) | Tracked, no user surface |

---

## Section 6 — Shared / cross-cutting infrastructure

Largely unchanged from v1. Brief recap; full file lists in v1 if needed.

- **`portal/student/app/internal/_shared/`** — 19 files. Cockpit shell + drill + hero + tabs + status-chip + verdict-box. On `feature/finance-cockpit`; not on `integrate/grant-compliance-scaffold`.
- **Authentication** — essentially nonexistent on in-scope branches. `?id=uuid` for students, `?token=` for colleges, no auth for staff cockpits. (Magic-link work is on `refactor/staging`'s `issue-24` line; not in this document's scope.)
- **LLM abstractions** — `agents/llm/client.py` (Gemini Flash wrapper). Removed on `refactor/staging` in favor of `packages/wfdos-common/wfdos_common/llm/` multi-provider adapter. Here, `agents/llm/` is authoritative.
- **Microsoft Graph shared library** — `agents/graph/` (`auth.py`, `sharepoint.py`, `teams.py`, `transcript.py`, `invitations.py`, `config.py`). Used by Scoping, Grant ingestion, Email sending, Grant-compliance evidence collection, and the Borderplex client portal's SharePoint document listing.
- **Database + migrations** — `scripts/001–010` on `development`; `011-embeddings-metadata.sql` on `feature/finance-cockpit`; `011–013` (three files) on `claude/sleepy-wiles-f9fc04`; own Alembic on `agents/grant-compliance/`.
- **Staff agent** — `agents/assistant/staff_agent.py`. Role-aware via `?user=`. Cross-cutting across all named staff (Ritu, Gary, Krista, Bethany, Jason, Jessica).

New in v2:

- **`agents/finance/design/cockpit_data.py`** — the data-extraction and fixture-mapping module. Shared in the sense that its categories and provider taxonomy are reused across the Finance cockpit and the grant reconciliation pipeline. Worth calling out because its taxonomy (providers by K8341 category) is the de-facto canonical provider list.
- **`agents/assistant/api.py`** on :8009 — the conversational-agent router for all six (or seven, counting `finance_agent.py`) agents. Cross-cutting across student, employer, college, youth, consulting, staff audiences.

---

## Section 7 — Waifinder as operator (new section)

Waifinder uses the platform itself, in multiple capacities. This is not "Consulting component" — it is Waifinder's operational tooling, which happens to span both Consulting and Coalition/Workforce modules.

### 7.1 Waifinder placement staff — the Recruiting Workbench

**This is the core v2 reframe.** The Recruiting Workbench at `/internal/recruiting/` serves **Waifinder staff running placement-matching as a managed service** to intermediary customers (today: Borderplex, via Cohort 1 apprentices on the WSB engagement).

**Persona:** currently Ritu herself, possibly with help. Future: a dedicated placement specialist at Waifinder (possibly promoted from a graduated apprentice). No specific human is named in the docs.

**Why this is "Waifinder operator," not "Coalition intermediary staff":**
- CFA Coalition no longer has a placement function internally (Dinah left; Coalition pivoted to provider recovery).
- Borderplex as an intermediary customer does not do its own matching — it funds Waifinder to do matching for its funded participants.
- Waifinder's value-add to a workforce board customer is the domain depth (tech roles, agentic AI) + employer relationships that let one placement specialist serve multiple workforce board customers.

**UI surfaces (on `feature/finance-cockpit`):**

| Route | File | State |
|---|---|---|
| `/internal/recruiting/workday` | `portal/student/app/internal/recruiting/workday/{page.tsx, workday-client.tsx}` | **Built** — filterable job list + student drill (Phase 2D–2E). |
| `/internal/recruiting/applications` | `applications/page.tsx` | **Skeleton** — `ComingSoon` stub. |
| `/internal/recruiting/caseload` | `caseload/page.tsx` | **Skeleton** — `ComingSoon` stub. |

**Backend:**

| Service | File | Port | State |
|---|---|---|---|
| Job board API | `agents/job_board/api.py` | :8012 | Built (Phase 2D–2E). |
| Embedding-based matching | `agents/job_board/data_source.py` + `embeddings` table (VECTOR(1536), HNSW) | — | Built. |
| Match narratives generator | — | — | **Not on this branch.** Schema ready (12-col `match_narratives` table), zero rows. |
| Gap analysis generator | `agents/career-services/gap_analysis.py` | — | Built (from `development`). |

**Data dependencies:** same as v1 — `jobs_enriched`, `jobs_raw`, `v_jobs_active`, `embeddings`, `applications`, `students`, `student_skills`, `gap_analyses`, `match_narratives`.

**New observation for v2 — apprentice integration:**
The Recruiting Workbench today matches **students** to **jobs_enriched** rows. It does **not** yet model the integrated consulting-apprentice-placement flow. Specifically:
- A Cohort 1 apprentice on a Waifinder engagement is in `engagement_team`, not in `students`.
- The apprentice's transition from "on engagement" to "placement-ready" has no state machine in code.
- The client-hire option ("Host an apprentice for OJT — evaluate talent during a real project before committing to a hire" per `employer_agent.py` line 248) is a talking point, not a tracked flow.
- The "19 districts' jobs" from Alma and the "4 SMB intros" are not distinguished in any table from generic `jobs_enriched` rows.

**Gaps / pain points specific to Waifinder-as-placement-operator:**
1. One of three sub-pages is built. Applications + caseload are still stubs.
2. Apprentice entity type does not exist in the matching layer.
3. Consulting engagement → placement pipeline has no data model.
4. Per-customer scoping is not present — Waifinder running placement for Borderplex AND for a future second customer would mix their data in one `jobs_enriched` table. `jobs_enriched.deployment_id` exists (and is `'cfa-seattle-bd'` for most rows) but is not surfaced as a tenancy filter in the recruiting workbench UI.

### 7.2 Waifinder consulting operations

Waifinder uses the Consulting component to run its own business:

- **BD Command Center** at `app/internal/bd/` (uncommitted WIP) — Jason's inbound pipeline cockpit.
- **Marketing cockpit** at `app/internal/jessica/` (uncommitted WIP) — Jessica's content performance view.
- **Scoping pipeline** at `agents/scoping/` — pre-proposal workflow for new consulting engagements (test fixture: Alma at WSB).
- **Consulting intake + pipeline** at `agents/portal/consulting_api.py` + `app/cfa/ai-consulting/` — public inquiry funnel plus internal pipeline management.
- **Client portals** at `app/client/` + `app/coalition/client/` — the second is Borderplex-adapted; see §4.1.

This is all Consulting component, covered in the architecture doc. v2 notes it here because it is **Waifinder's own use** of those modules. The modules generalize to other consulting businesses; Waifinder is just the origin customer.

### 7.3 Waifinder as employer of apprentices during OJT

Not built as a discrete module. Represented in data only as:
- `engagement_team.is_apprentice=true` rows for engagements where Waifinder is the delivery entity.
- `consulting_engagements.cohort_id` links an engagement to a cohort.

**What doesn't exist:** timesheet tracking, HR records, pay tracking, hour tracking against the OJT curriculum. `staff_agent.py` line 83 concedes: *"OJT timesheet tracking not yet in WFD OS."*

### 7.4 Waifinder as potential employer-of-record post-cohort

**Not modeled.** An apprentice who finishes a cohort and stays at Waifinder has no distinct entity status — they remain in `engagement_team` or transition to an unspecified-next-state. The wfd-os data model does not yet distinguish apprentice / full-hire / contractor states.

### 7.5 Marketing / BD infrastructure inherited from Consulting

Section 7 exists as a deliberate alternative to calling all of this "Consulting component." The distinction matters because:
- **Consulting component** is a product line Waifinder could sell to *other* consulting businesses.
- **Waifinder-as-operator** is Waifinder's specific use of those modules plus additional operator-only concerns (apprentice management, cohort tracking, cross-customer placement, engagement-to-placement pipeline).

The code today does not draw this distinction. If wfd-os ever licenses the Consulting component to a non-Waifinder consulting business, the operator-specific concerns would need to be factored out.

### 7.6 Summary — Waifinder as operator

| Operator capacity | Primary surface | State |
|---|---|---|
| Placement matching (managed service) | `/internal/recruiting/workday` + `job_board/api.py` :8012 | Built (workday only) |
| Consulting BD | `/internal/bd/` (uncommitted) + `/api/consulting/bd/*` | Built in uncommitted WIP |
| Marketing | `/internal/jessica/` (uncommitted) + `/api/consulting/marketing/*` | Built in uncommitted WIP |
| Scoping new engagements | `agents/scoping/` | Built |
| Employer of apprentices during OJT | — | Not built |
| Post-cohort employment tracking | — | Not built |
| Cohort-level progress view (for Gary) | — (staff agent only) | Not built |

---

## Section 8 — Things that don't fit / need adjudication

Updated for v2.

### 8.1 Managed service vs SaaS for matching — not decided

Today, Waifinder provides matching as a **managed service** to Borderplex. Waifinder staff (Ritu) use the Recruiting Workbench on Borderplex's behalf. Borderplex staff do not log into the workbench.

Two future models are visible in the code:
- **Managed service persists.** Waifinder scales by hiring more placement specialists. One specialist per multiple workforce board customers. Wfd-os grows multi-tenant features (per-customer scoping of `jobs_enriched`, per-customer apprentice rosters). No customer-facing workbench needed.
- **SaaS for some customers.** A future customer (e.g., a workforce board with its own placement staff, unlike Borderplex) might license the workbench and operate it themselves. This would require auth, per-tenant isolation, and a much less Waifinder-internal UX.

Not decided. The `refactor/staging` branch's multi-tenant edge-proxy work (issue-30 on Gary's line, out of scope for this doc) hints at future SaaS support, but nothing on the in-scope branches actively pursues it.

### 8.2 Case manager / career coach — absent, probably intentional

Coalition (CFA) eliminated Dinah's role. Borderplex's model relies on Waifinder-managed placement, so no case manager on their side either. The architecture doc lists "career services" as a Coalition/Workforce module but it manifests as **gap analysis output for students** + **conversational student agent**, not as a **coach-facing workbench**.

**Recommendation (per prompt constraint, observation-only):** Defer this role until a customer signal emerges. Today, no platform user is a career coach; wtc's `CaseMgmt` + `CaseMgmtNotes` models remain unported for good reason.

### 8.3 `agents/grant-compliance/` adjudicated

Closed per v2 corrections (see §0 and §1.2): it **is** the Quinn module as partially built. The Phase 1 draft's "designed only" was incorrect.

### 8.4 `/internal` root page — miscast

Unchanged from v1. `/internal/page.tsx` serves Consulting inquiry triage. Needs a different route or a different `/internal` root.

### 8.5 Two client portals

`portal/student/app/client/page.tsx` and `portal/student/app/coalition/client/page.tsx` both exist. The second is the Borderplex-adapted one used by Alma. The first — the un-adapted version — is a generic consulting-client portal.

**Audience question:** Are these two surfaces for the same audience (consulting clients) seen via two branding paths, or two different audiences? Not obvious from the code. Both reach the same backend (`consulting_api.py`). A WSB-specific `if engagement.id === "wsb-001"` branch in `coalition/client/client-view.tsx` lines 488–589 adds funder-facing sections that the plain `/client/` doesn't render.

### 8.6 Agent name inconsistency

`agents/assistant/` on `integrate/grant-compliance-scaffold` has **`finance_agent.py`** (7th agent, Krista-adjacent). Uncommitted WIP adds **`bd_agent.py`** and **`marketing_agent.py`** (8th and 9th, Jason and Jessica). None of these three are on `feature/finance-cockpit`. The canonical assistant layer varies by branch — merge will require reconciling.

### 8.7 Dashboard duplication

Alma has two surfaces (`/coalition/client` and `agents/reporting/dashboard/`) that overlap on labor-market content. The former is engagement-specific with a market-intelligence card; the latter is region-specific with three panels. Reasonable people could merge or keep separate.

### 8.8 Hardcoded demo data in the funder-facing UI

The Funded Participants, Outcomes for Your Board, and Regional Labor Market cards in `/coalition/client?token=wsb-001` contain hardcoded numbers and names. Valid for a single-client demo; does not scale. The data model behind each card needs to be designed before a second client.

---

## Section 9 — Observations for code organization

Updated for the corrected audience picture.

### 9.1 Where the current structure aligns with audience-first thinking

(Carried forward from v1; still accurate.)
- `portal/student/app/internal/` as the staff umbrella works structurally.
- `_shared/` is a clean shared-primitives library.
- `components/dashboard/` is cleanly student-audience.
- `agents/portal/college_api.py` is cleanly partner-audience.
- `agents/career-services/gap_analysis.py` is cleanly audience-function-named.

### 9.2 Where the current structure fights audience-first thinking (corrected)

- **The Recruiting Workbench is at `/internal/recruiting/` — good location** for what it is (Waifinder-operator surface). But it sits alongside Finance (a Coalition-intermediary surface) under the same `/internal/` umbrella as if they served the same audience. Post-v2, these are **different audiences** even though both are "staff" users.
- **`/internal/page.tsx` renders Consulting inquiry triage** — covered in v1.
- **Coalition's two intermediary staff personas (Krista, Bethany) vs. Waifinder's one operator persona (placement specialist)** are not structurally distinguished. Both live under `/internal/`. A future intermediary customer installation would want Krista + Bethany views but not the Recruiting Workbench.
- **Funder dashboards are scattered.** Alma's view lives in two places (`app/coalition/client/` inside the Next.js portal and `agents/reporting/dashboard/` as a standalone Vite app). ESD's view is a generated output. There is no `app/funder/` namespace.
- **Client portals duplicated.** `app/client/` and `app/coalition/client/` both exist, with different content for the same backend.
- **Apprentice entity is inferred from `engagement_team.is_apprentice=true`.** There is no dedicated apprentice/cohort data model — cohort membership lives in `engagement_team` + `engagement_id`, student-ness lives in `students`, and the two don't link. This is not a naming mismatch; it's a missing abstraction. The integrated consulting→placement flow that Ritu described has nowhere to live in the schema.
- **`agents/apollo/`, `agents/marketing/`, `agents/scoping/` are Consulting-audience infrastructure** but sit as peers to Coalition agents. (Unchanged from v1.)
- **`agents/grant-compliance/` is Coalition-audience** (Bethany) but structurally is a standalone FastAPI with its own Alembic + schema. Naming-wise it is alphabetically adjacent to `agents/grant/`; semantically it is what the architecture doc calls Quinn. No reference between the two in code.

### 9.3 What would need to move if reorganizing by primary audience

Low-controversy (unchanged from v1):
- `app/internal/jessica/` + `app/internal/bd/` (Consulting, not Coalition) would belong under a Consulting umbrella.
- `/internal/page.tsx` (Consulting inquiry triage) belongs under a BD-named path.
- Newsletter + `/unsubscribe/` (Consulting marketing).
- `agents/apollo/`, `agents/scoping/`, `agents/marketing/` are Consulting infrastructure.

Harder calls (updated for v2):
- **The Recruiting Workbench.** By current audience it is Waifinder-operator. By architectural intent it is Coalition/Workforce "recruiting / placement staff workbench." Reasonable to place in either — the question is whether the workbench will ever be used by a customer's own staff (SaaS) or always by Waifinder (managed service). §8.1.
- **`agents/grant-compliance/`** — Coalition (Bethany) audience but standalone structure. Fold into `agents/grant/`, keep independent, or rename?
- **Funder dashboards** — `/coalition/client/`'s WSB branching and `agents/reporting/dashboard/` could consolidate under an `app/funder/` umbrella, or stay split by form factor (embedded-in-engagement-portal vs. standalone-intelligence-dashboard).
- **Waifinder operator vs. Coalition intermediary** distinction suggests two different `/internal/` sub-namespaces: one for Waifinder-operator surfaces (recruiting, BD, marketing, scoping), one for intermediary-staff surfaces (finance, grants). The current structure mixes them.

### 9.4 The integration-visibility gap

v2 adds one material observation not in v1: **The integrated business model (consulting engagement = OJT + placement pipeline) is invisible in the code structure.**

- An engagement is modeled (`consulting_engagements`, `engagement_team`, `engagement_milestones`, `engagement_deliverables`, `engagement_updates`).
- Apprentice participation is modeled (`engagement_team.is_apprentice`).
- Funder relationship is modeled for Borderplex (the WSB-specific code branches in `/coalition/client/client-view.tsx`).
- **Placement** (the act of an engagement's apprentice becoming a hire at the client) is **not** modeled. No table, no workflow, no state transition.
- **Job postings shared by a funder** (Alma's 19 districts, her 4 SMBs) are not distinguished from generic `jobs_enriched` rows. They are not linked to her engagement or her funded apprentices.

Code organization observation: the three data surfaces that together would tell the integrated story — `consulting_engagements`, `engagement_team`, `students`, `jobs_enriched`, `applications` — all exist, but live in separate namespaces (consulting vs. coalition) and do not know about each other. The integration is not an organizational failure; it is an unfactored concept.

### 9.5 Multi-tenancy not present but latent

`jobs_enriched.deployment_id` exists and is mostly `'cfa-seattle-bd'`. `consulting_engagements.client_access_token` exists. `college_partners` has a token column. Each of these is a per-tenant key, but there is no unified tenant model. A future second workforce board customer would show up as another `deployment_id` value, but nothing in the UI or API enforces isolation.

---

## Appendix A — Corrections to prior documents

### A.1 To `wfd_os_architecture.md`

- **"(Jessica module)" misnomer** for the Recruiting Workbench. Jessica does Marketing. The workbench serves Waifinder's (unnamed) placement staff. Architecture doc should either rename the module or clarify persona.
- **"Recruiting / placement staff workbench — Coalition staff doing placement work"** is misleading: on the evidence of this document, Coalition staff do not do placement work. Waifinder staff do, on Coalition's behalf. Arch doc language should change to "Waifinder placement staff providing managed-service matching to workforce intermediary customers."
- **"Compliance / Quinn — designed"** — `agents/grant-compliance/` is Quinn, partially built. Architecture doc should move Quinn from "Designed" to "In progress / Partially built on `integrate/grant-compliance-scaffold`."
- **Funder audience is missing from the architecture doc.** It treats funders only as "outcome-report recipients." Per v2, Alma at Borderplex has two live web surfaces. Andrew/Jenny at ESD have monthly generated reports. Architecture doc should add Funders as a first-class audience.
- **Integrated consulting→placement flow** is not described in the architecture doc. The apprentice-hosting opportunity language in `agents/assistant/employer_agent.py` is the closest articulation in code.

### A.2 To `wfd_os_code_reality_phase1.md`

- "Compliance / Quinn — designed only": **still wrong** (see §1.2).
- "Recruiting / placement staff workbench — built (Phases 2B–2E)": **partial** (workday only; applications + caseload are `ComingSoon`).
- **New:** Phase 1 draft has no funder audience discussion. Missing content.
- **New:** Phase 1 draft describes "Apprentice workforce management — in wtc, needs port." On current v2 evidence, apprentice management on wfd-os is partially built via `engagement_team` + `cohort_id`. A full port of wtc's `CaseMgmt` is not necessarily the right move; the apprentice tracking belongs in the consulting engagement layer, not a separate case-management domain.

### A.3 To `wfd_os_branch_reality_map.md`

- Section 3.2.B / Recruiting workbench still listed as built. Only workday/ is built.
- Section 3.3.C WIP inventory is accurate but did not flag that these are **Consulting** additions even though uncommitted on the Coalition branch's worktree.
- Section 6.4 ("grant-compliance — what is this actually?") — v2 of the audience doc answers: it is Quinn-as-built. Branch map can be updated in-place or superseded.

### A.4 To v1 of this audience doc

- §1.1 (Placement specialist) mis-identified the persona's organization. The Recruiting Workbench is Waifinder-operator, not Coalition-staff. Moved to §7.1 in v2.
- §4 (Partners) conflated funders and operational partners. Split in v2 as §4 (Funders) + §5 (Operational partners).
- §6 (Things that don't fit) did not identify the integrated consulting→placement flow as a first-class observation. Added in v2 as §9.4.

---

## Appendix B — Questions this document surfaces but does not answer

Informational only.

1. **When does matching become SaaS for a customer?** §8.1. Depends on future customer signal. Platform is architected for managed-service first.
2. **What is Leslie's role?** Still undefined in code.
3. **Do `agents/grant/` and `agents/grant-compliance/` merge?** Overlapping staff (Bethany), overlapping workflows (grant reconciliation + compliance). Two independent subsystems today.
4. **Does `/internal` root keep its current page?** Currently a Consulting inquiry triage; miscast for the path name.
5. **Should the career-coach / case-manager persona be planned?** v2 observation: no active customer has this role. Defer until one does.
6. **Should funders have their own namespace** (`app/funder/`)? Today Alma is served via two different paths (`/coalition/client/` and `agents/reporting/dashboard/`). ESD is a generated artifact. A unified funder surface is possible but not currently needed.
7. **Does the integrated consulting→placement flow need a dedicated domain?** §9.4. The flow is real; the code doesn't represent it. Reasonable to add or to leave implicit and let the engagement lifecycle carry it.
8. **Data model for `Funded Participants` card.** Currently hardcoded demo data. Fields needed: apprentice.readiness_score, apprentice.projected_placement_date, apprentice.projected_salary_range, apprentice.skills_with_levels. No such fields exist yet.
9. **Multi-tenant scoping for Recruiting Workbench.** When the second workforce board customer arrives, will `jobs_enriched.deployment_id` filter the workbench? Today it does not — the workbench sees all deployments.
10. **19 districts + 4 SMBs from Alma** — where do these live in the schema? They appear to be either (a) generic `jobs_enriched` rows without per-customer tags, or (b) not yet ingested. Either way, Alma's specific contributions are not distinguishable from generic job supply.

---

*End of v2. Output: `docs/coalition_workforce_audience_view_v2.md`. Word version at `docs/coalition_workforce_audience_view_v2.docx`. v1 preserved at `docs/coalition_workforce_audience_view.md`.*
