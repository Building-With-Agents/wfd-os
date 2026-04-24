# Coalition / Workforce — Audience View

*Date: April 20, 2026*
*Owner: Claude Code (read-only recon)*
*Scope: Coalition/Workforce component of wfd-os, organized by audience served rather than by module name.*
*Status: AUTHORITATIVE as a read-only description of current code. Observations only — no reorganization proposals, no recommendations for immediate action.*

This document answers: **"For each kind of person using the platform, what does Coalition/Workforce actually give them today?"** It is the audience-first view of the same code the architecture doc describes by module and the branch reality map describes by branch.

Source branches inspected (from `branch reality map`):
- **`feature/finance-cockpit`** — the active Coalition/Workforce branch (finance cockpit, recruiting workbench, embeddings, migrations). Worktree at `C:\Users\ritub\Projects\wfd-os\.claude\worktrees\stupefied-tharp-41af25`.
- **`integrate/grant-compliance-scaffold`** + its uncommitted working tree in the main folder. The grant-compliance FastAPI app + BD/Marketing WIP.
- **`claude/sleepy-wiles-f9fc04`** — the one-commit lifeboat for migrations `011`–`013`.

Where code on the Vegas-era `development` baseline remains current (e.g., student profile backend, showcase, WJI, college portal), it is treated as current Coalition/Workforce surface.

---

## Section 0 — Corrections to flag before reading

Three source-document inconsistencies I ran into and **do not resolve silently**. Ritu decides whether/how to reconcile.

### 0.1 "Jessica module" — misnomer in the architecture doc

`docs/wfd_os_architecture.md` line ~246 calls the Recruiting / placement staff workbench **"(Jessica module)"**. The actual Jessica at CFA is Marketing (confirmed by `CLAUDE.md` lines 488–492 — "Jessica (Marketing): Content approval and campaign status. Apollo sequence status. No access to student PII or grant financials" — and by `agents/assistant/staff_agent.py` line 35 — "If user is jessica (Marketing): Lead with content status…"). The code agrees:

- `portal/student/app/internal/jessica/page.tsx` is explicitly named `JessicaMarketingCenter` (line 50) and pulls from `/api/consulting/marketing/*`. That is a **Consulting** surface.
- `portal/student/app/internal/recruiting/` is a Coalition/Workforce surface — but there is no named human persona attached to it in any doc. The placement-specialist user of the Recruiting workbench is **anonymous** in the docs today.

Throughout this document, I refer to the Recruiting workbench's user as **"placement specialist"** rather than "Jessica."

### 0.2 The Phase 1 draft mis-categorized `agents/grant-compliance/`

`wfd_os_code_reality_phase1.md` (which inherits from an earlier snapshot) describes **"Compliance / Quinn"** as *designed only, no code*. In fact, `agents/grant-compliance/` on `integrate/grant-compliance-scaffold` is a **partially-built 62-file FastAPI app with Alembic, QuickBooks OAuth, four compliance agents, 8 route modules, and a working test harness.** It *is* the Quinn module as-built — scoped narrowly to K8341 per its own `CLAUDE.md` but structurally generic. See Section 1.3 below.

### 0.3 The Recruiting workbench is partial

Architecture doc calls the workbench "in progress (Phases 2B–2E built; 2F polish and 2G narratives in flight)." Branch reality map repeats that. Actually on `feature/finance-cockpit`:
- `internal/recruiting/workday/page.tsx` — **built.** Server component that parallel-fetches `/stats/workday` + `/jobs` from `agents/job_board/api.py` on :8012. This is the Phase 2B-2E work.
- `internal/recruiting/applications/page.tsx` — **explicit `ComingSoon` placeholder**, 10 lines. Not built.
- `internal/recruiting/caseload/page.tsx` — **explicit `ComingSoon` placeholder**, 10 lines. Not built.

So "Recruiting workbench" at one level is built and at another is a set of stubs. Important if "in progress" was read as "mostly done" — only one of three main surfaces is actually working.

---

## Section 1 — Intermediary staff (primary users)

Coalition/Workforce is built for intermediary staff. The architecture doc emphasizes this; CLAUDE.md's "Visibility Principle" reinforces it. What the code actually builds today serves a narrow slice of that population.

I've identified staff roles by reading `agents/assistant/staff_agent.py` (lines 23–40 explicitly enumerate role-specific briefings) and by tracing the UI surfaces under `portal/student/app/internal/`. Where a role has dedicated UI, it's listed; where it only has an agent prompt, I note that.

### 1.1 Placement specialist / recruiter

**Persona note:** no named human in `CLAUDE.md`'s user list (Ritu, Gary, Krista, Bethany, Leslie, Jason, Jessica). Possibly "Leslie" — she's in the user list but has no role described anywhere in the code or docs I can find. Treat the persona as anonymous until confirmed.

**UI surfaces (on `feature/finance-cockpit`):**

| Route | File | State |
|---|---|---|
| `/internal/recruiting/workday` | `portal/student/app/internal/recruiting/workday/page.tsx` (+ `workday-client.tsx`) | **Built** — server component fetches `/stats/workday` + `/jobs` (paginated, filterable). First-paint has real data. Phase 2E student drill + job-context back navigation. |
| `/internal/recruiting/applications` | `portal/student/app/internal/recruiting/applications/page.tsx` | **Skeleton** — `ComingSoon` placeholder. |
| `/internal/recruiting/caseload` | `portal/student/app/internal/recruiting/caseload/page.tsx` | **Skeleton** — `ComingSoon` placeholder. |

Supporting frontend components (same tree):
- `recruiting/components/filter-chips.tsx`, `job-card.tsx`, `recruiting-chat-panel.tsx`, `recruiting-topbar.tsx`, `search-box.tsx`
- `recruiting/lib/api.ts`, `lib/types.ts`

All wrap the shared `AgentShell` from `app/internal/_shared/` (see §5).

**Backend services:**

| Service | File | Port | State |
|---|---|---|---|
| Job board API (job listings + match counts + student drill) | `agents/job_board/api.py` | :8012 | **Built** (Phase 2D–2E). Provides `/stats/workday`, `/jobs`, `/jobs/{id}/drill`, `/students/{id}/drill`. |
| Job board data source | `agents/job_board/data_source.py` | — | **Built.** |
| Embedding-based match scoring | Inline in job_board + leverages `embeddings` table | — | **Built** (Phase 2D cosine matching over pgvector). |
| Match narrative generator | — | — | **Not built on this branch.** The `match_narratives` table exists (12 columns) in Postgres, but no generator code lives on `feature/finance-cockpit`. Architecture doc's "Phase 2G — narrative generation validated, UI integration in flight" has not landed on this branch. |
| Gap analysis generator | `agents/career-services/gap_analysis.py` | — | **Built** (from `development`). 30 rows in `gap_analyses` table. |

**Data dependencies:**
- `jobs_enriched` (103 rows, 26 cols; includes `city/state/country/is_remote/latitude/longitude/employment_type` after migration 013)
- `jobs_raw` (103 rows; JSearch payload in `raw_data` JSONB)
- `v_jobs_active` view (migration 011, broadened in 013)
- `embeddings` polymorphic table (VECTOR(1536), HNSW cosine; covers both students + jobs; 249 rows)
- `applications` table (migration 011; UNIQUE(student_id, job_id); approval-status enum) — 3 rows, nearly empty
- `students`, `student_skills`, `student_work_experience`, `student_education`, `student_journeys`
- `gap_analyses` (30 rows; `target_role`, `gap_score`, `missing_skills`, `recommendations`)
- `match_narratives` (0 rows; schema ready, no generator)

**Gaps / pain points visible in code:**
1. Two of three recruiting sub-pages are `ComingSoon` stubs. A placement specialist can browse + filter jobs and drill into a job or a student, but cannot yet view their application caseload or manage the pipeline of applications they've initiated.
2. Match narratives UI references exist throughout `workday-client.tsx` design but the generator to populate `match_narratives` is not on this branch. First-class user-visible effect: students will have no written "why this match" explanations until the generator lands.
3. The `applications` table has 3 rows — the placement specialist's primary artifact (tracked submissions) is essentially empty in production data.
4. No staff-to-student messaging infrastructure on this branch (student portal lacks inbound messages; no notification system for the specialist to see student replies).
5. The Recruiting workbench and the Finance cockpit share a sidebar + shell but no navigation ties an individual student's placement journey to their cost/impact in the Finance cockpit. Specialists can't easily answer "how does this student I'm placing affect our K8341 burn."

### 1.2 Grant compliance / finance operations — **Krista**

**Persona note:** `agents/assistant/staff_agent.py` line 29 — "If user is krista (Finance): Lead with financial briefing — outstanding invoices, payroll status, grant burn rate."

**UI surfaces (on `feature/finance-cockpit`):**

| Route | File | State |
|---|---|---|
| `/internal/finance` | `portal/student/app/internal/finance/page.tsx` (+ `cockpit-client.tsx`) | **Built** — server-component wrapper parallel-fetches `/cockpit/status` + `/cockpit/hero` + `/cockpit/decisions` from :8013. Rich cockpit UI: hero tiles, decisions list, per-tab content, polymorphic drill. |
| `/internal/finance/operations` | `portal/student/app/internal/finance/operations/page.tsx` (+ `finance-client.tsx`) | **Skeleton + cross-branch coupling** — frontend expects grant-compliance backend at `http://localhost:8000/api/grant-compliance/*`. Backend is `agents/grant-compliance/` which lives on `integrate/grant-compliance-scaffold`, NOT on this branch. Neither branch has a complete operations sub-page on its own. |

Supporting files (same tree):
- `finance/components/cockpit-shell/{activity-feed,chat-panel,decisions-list,topbar}.tsx`
- `finance/components/tabs/tab-content.tsx`
- `finance/lib/{api,format,types}.ts`
- `finance/lib/cockpit-fixture.json` (design-time mock data)

**Backend services:**

| Service | File | Port | State |
|---|---|---|---|
| Finance cockpit API | `agents/finance/cockpit_api.py` | :8013 | **Built.** Routes: `/cockpit/status`, `/cockpit/hero`, `/cockpit/decisions`, `/cockpit/tabs/{tab_id}`, `/cockpit/drills/{key}`, `/cockpit/refresh`, `/health`. Reads from Excel fixtures via `data_source.py`. Loaded data confirms: 5.4 months K8341 runway, 5 Excel files, tab counts: decisions=11, providers=6, transactions=53, reporting=2, audit=6, high_priority=5. |
| Excel data source | `agents/finance/data_source.py` | — | **Built.** Wraps `design/cockpit_data.py::extract_all`. Switching to QB is documented as a one-line change in `default_source()`. |
| Cockpit data extraction | `agents/finance/design/cockpit_data.py` | — | **Built.** |
| HTML generators + template | `agents/finance/design/{generate_cockpit.py,cockpit_template.html,CFA_Cockpit.html}` | — | **Built** — design-artifacts for the cockpit. |

**Data dependencies:**
- Not Postgres-first. The Finance cockpit today reads from **5 Excel fixtures in `agents/finance/design/fixtures/`** (gitignored): `GJC Contractors 2024`, `K8341 GJC CFA WTWC Exh B`, `K8341_Cost_Per_Placement`, `K8341_Provider_Reconciliation_v3_3-27`, `WJI TWC Candidate Tracking`. Krista's Excel exports are the source of truth.
- Postgres tables related to this persona but not wired in: `wji_payments` (10 rows), `wji_placements` (7 rows), `wji_upload_batches`.

**Gaps / pain points visible in code:**
1. **Excel as source of truth.** Krista's workflow today is "edit Excel → the cockpit reflects it." This is fine for a demo, brittle for production. No persistence of cockpit state to Postgres; no audit trail of changes.
2. **`operations/` sub-page is cross-branch-broken.** Finance cockpit frontend expects a backend that lives on `integrate/grant-compliance-scaffold`. Kristalosing access to grant-compliance data inside the finance cockpit depends on a merge that hasn't happened.
3. **No write-back from WJI dashboard into cockpit.** `wji_payments` + `wji_placements` are populated but the Finance cockpit doesn't surface them — Krista has to cross-reference.
4. **No connection from placements-in-recruiting to placements-in-finance.** Recruiting specialist places a student; cockpit doesn't light up. One of the "cross-component flow" gaps the architecture doc alludes to but doesn't yet implement.

### 1.3 Grants / provider operations — **Bethany**

**Persona note:** `agents/assistant/staff_agent.py` line 31 — "If user is bethany (Grants): Lead with grant briefing — placement count toward 730 PIP threshold, provider status, ESD deadlines."

**UI surfaces:**

| Route | File | State |
|---|---|---|
| `/wji` | `portal/student/app/wji/page.tsx` | **Built** (Vegas-era). Grant partner upload surface: Excel upload for placements + payments, summary stats, batch management. 556 lines. |

No staff-specific workbench for Bethany beyond this. No `/internal/grants/` route. She currently uses the general WJI dashboard (which also serves grant partners) and the staff agent briefing.

**Backend services:**

| Service | File | Port | State |
|---|---|---|---|
| WJI grant dashboard API | `agents/portal/wji_api.py` | :8007 | **Built.** 6 routes: `/upload/placements`, `/upload/payments`, `/dashboard`, `/placements`, `/payments`, batch deletion. |
| Grant file ingestion (SharePoint) | `agents/grant/api.py` (+ `database/`, `ingestion/`, `queries/`, `reconciliation/` subdirs) | unknown port | **Built.** Separate service from `wji_api.py`. Handles SharePoint-sourced grant documents, reconciliation of partner submissions. |
| **Grant compliance system** (Quinn-as-built) | `agents/grant-compliance/` — 62 files; only on `integrate/grant-compliance-scaffold` | :8000 | **Partially built (skeleton + rules engine).** Four agents: Transaction Classifier (skeleton), Time & Effort (skeleton), Compliance Monitor (**rule engine ready**, see `compliance/rules.py` + `unallowable_costs.py`), Reporting (skeleton). Eight API route modules: allocations, compliance, grants, qb_oauth, reports, time_effort, transactions. QuickBooks OAuth live (per `integrate/...` commit `50f5c20 Step 1a: real QB sandbox sync`). MS Graph evidence integration (`integrations/msgraph/evidence.py`). |

**Data dependencies:**
- `wji_placements` (7 rows), `wji_payments` (10 rows), `wji_upload_batches`
- `grant-compliance`'s own Postgres schema (Alembic migrations `e935de2c6a04_initial_schema.py` + `52e509f9e39a_add_qb_oauth_tokens.py`) — grants, allocations, transactions, time certifications, compliance flags, report drafts, QB OAuth tokens.
- QuickBooks sandbox data (sync via `qb_oauth` route)

**Gaps / pain points visible in code:**
1. **Bethany has no dedicated UI surface.** The WJI dashboard serves both her (as staff) and grant partners (as uploaders). Mixed-audience page.
2. **Grant-compliance app is orphaned.** 62 files of substantive work on a disjoint-history branch that has never been pushed. The branch tip (`1a2bec6`) has not moved in 3 days. The rule engine is functional (per README), but no wiring exists from Bethany's persona to these rules — she can't yet see compliance flags from the staff cockpit.
3. **Placement-count-toward-730-PIP-threshold is hard-coded in the staff agent briefing** but not yet a cockpit metric. Bethany's #1 KPI is invisible unless she asks the agent.
4. **Two overlapping grant subsystems** in different places: `agents/grant/` (SharePoint ingestion + reconciliation, on `development`) and `agents/grant-compliance/` (QB + CFR compliance + reporting, on `integrate`). The relationship between them is not explicit in code or docs.

### 1.4 Career coach / case manager — possibly **Leslie**

**Persona note:** Leslie is listed in `CLAUDE.md` line 407 as a user of the staff agent, but has **no role description** in `staff_agent.py`, `CLAUDE.md`, or the architecture doc. Her function is undefined in the codebase.

The architecture-doc concept of a "career coach / case manager" maps loosely onto the wtc models `CaseMgmt` + `CaseMgmtNotes` (noted in the Phase 1 draft as "needs port from wtc"). **No equivalent surface or backend exists on wfd-os today.**

**UI surfaces:** none specific to this role. The student-facing portal's "Career Services" / "My Journey" sections are student-oriented, not coach-oriented — a coach has no view that says "here are my 20 students and where each one is stuck."

**Backend services:**
- `agents/career-services/gap_analysis.py` — produces gap analyses that students see in their portal; no coach-facing interface to author, override, or annotate.
- `career_services_interactions` table exists (row count not queried in this recon; worth inspecting later).
- `student_journeys` table (3,573 rows) — tracks each student's progression through stages, but there is no UI surface to view this as a coach would.

**Gaps / pain points visible in code:**
- **Entirely unserved on wfd-os today.** The architecture doc treats career coaching as a module-in-context (embedded in student profile + gap analysis + student journey), not as a dedicated staff surface. If Leslie is the intended user, she has no cockpit, no caseload, no notes, no scheduled follow-ups, no intervention log.
- wtc's `CaseMgmt` / `CaseMgmtNotes` would be the reference if this were ported, but nothing in the current code signals a port is in flight.

### 1.5 Operations / leadership — **Ritu, Gary**

Both named in `staff_agent.py` with explicit role briefings (lines 25, 27):
- Ritu (CEO): "Lead with the big picture — grant status, consulting pipeline, cohort status, anything needing her attention. She wants cross-system visibility in 60 seconds."
- Gary (Tech Lead): "Lead with cohort briefing — student progress, who needs help, sprint status. He wants to eliminate coordination overhead."

**UI surfaces:**

| Route | File | State | Notes |
|---|---|---|---|
| `/internal` (root) | `portal/student/app/internal/page.tsx` | **Built — but wrong audience.** 1,000+ lines. Despite the `/internal` path being where the architecture doc says the Staff Agent "Lives," this page renders a **Consulting Inquiries triage view** (uses `/api/consulting`, manages prospective-client inquiries with Apollo contact IDs). That's Jason's (BD) work, not Ritu's or Gary's. |
| CEO briefing | N/A — no dedicated page | **Not built.** Ritu's "60-second cross-system view" is delivered only via the staff agent conversation, not a visual dashboard. |
| Cohort briefing | N/A — no dedicated page | **Not built.** Gary's cohort briefing also only exists as an agent response. |

**Backend services:**

| Service | File | Notes |
|---|---|---|
| Staff agent (role-aware) | `agents/assistant/staff_agent.py` | **Built.** Role-aware via `?user=` query param. Tools: `_get_grant_summary`, `_get_consulting_pipeline`, `_get_cohort_status`, `_get_placement_summary`, `_get_recent_inquiries`, `_draft_update`. Aggregates cross-system data for conversational briefings. |

**Gaps / pain points visible in code:**
1. **The leadership view is conversational-only.** There is no visual CEO cockpit. "Cross-system visibility in 60 seconds" only works if Ritu is willing to have a chat.
2. **`/internal` root is mis-branded for this audience.** A first-time visitor who types `/internal` expecting an operations-leadership landing gets the Consulting Inquiries triage page. That page arguably belongs at `/internal/bd/` or `/internal/consulting/` — its current location at `/internal` root is a historical accident.

### 1.6 Named staff with no role description

- **Leslie** — listed in `CLAUDE.md` line 407 alongside the other staff agent users; not named in `staff_agent.py`'s role-briefing template. No UI or backend built for her; see §1.4.

### 1.7 Summary table — intermediary staff

| Role | Person | Primary UI | Primary backend | State of UI | State of backend |
|---|---|---|---|---|---|
| Placement specialist | unnamed (possibly Leslie) | `/internal/recruiting/workday` | `job_board/api.py` :8012 + `career-services/gap_analysis.py` + `profile/parse_resumes.py` | Built (1 of 3 sub-pages) | Built (matching), no narrative generator |
| Grant compliance / finance ops | Krista | `/internal/finance` | `finance/cockpit_api.py` :8013 (Excel) + `grant-compliance/` :8000 (cross-branch) | Built main page, skeleton `operations/` | Built main, partial grant-compliance |
| Grants / provider ops | Bethany | `/wji` (shared with partners) | `portal/wji_api.py` :8007 + `grant/api.py` + `grant-compliance/` | Mixed-audience, no dedicated staff view | Built (all three subsystems, but uncoordinated) |
| Career coach / case manager | possibly Leslie | — (none) | `career-services/gap_analysis.py` only | **Not built** | Not built as staff-facing |
| Operations / leadership | Ritu, Gary | — (agent only; `/internal` root is miscast) | `assistant/staff_agent.py` | **Not built** | Built (conversational) |

---

## Section 2 — Students (secondary users)

Students interact with the platform. Ritu's framing is that they are secondary because the platform measures success by staff effectiveness; the student surfaces exist so that staff have someone to serve.

### 2.1 Student-facing portal

**UI surface:** `portal/student/app/student/page.tsx` — a client component that takes `?id=<uuid>` as auth, fetches profile + matches + gap + journey + showcase state in parallel, and renders 8 dashboard components:
- `header.tsx` — identity + completeness bar
- `congratulations-banner.tsx`
- `journey-pipeline.tsx` — the stage progression (Intake → Assessment → Training → OJT → Job Ready → Showcase → Placement → Post-Placement)
- `gap-analysis-preview.tsx` — preview of the skills gap
- `job-matches-section.tsx` + `job-match-card.tsx` — matched jobs
- `showcase-status.tsx` — showcase eligibility/activation
- `ai-career-navigator.tsx` — embedded assistant

**Backend services:**
- `agents/portal/student_api.py` on :8001 — 7 endpoints under `/api/student/{student_id}/*` plus `/api/stats` and `/api/health`:
  - `/profile`, `/matches`, `/gap-analysis`, `/journey`, `/showcase`, POST `/chat`
- `agents/assistant/api.py` on :8009 — `student_agent.py` serves the in-page career-navigator

**State:** **Built** (Vegas-era). The UI is polished and functional. Per the data snapshot in `docs/wfd_os_code_reality_phase2.md`: 4,727 students in Postgres, of which **1% have `profile_completeness_score >= 0.7`, 0% are showcase-eligible, 0% are showcase-active, 3% have `resume_parsed=true`**, 86% have `pipeline_status='unknown'`. So for most students, the dashboard has almost nothing to render.

**Honest assessment of how well it serves students vs. collects data for staff:**
The surfaces are student-first in design (UX is built for the individual seeing their own data, not a staff view). But the *operational gating* is staff-driven — a student becomes showcase-eligible only when staff flip `showcase_active=true`, and no one has yet. The portal works for one hypothetical motivated student but does not yet accept traffic from the 4,727 migrated students in any meaningful way.

### 2.2 Public arrival / intake

**UI surface:** `portal/student/app/careers/page.tsx` — a 282-line React page. A landing view with a "Get started" CTA that reveals an intake form (skills checkbox grid with 22 skill options, role picker with 12 role options, resume upload).

**Backend:** The intake form's submit endpoint is not obvious from the page head — I did not trace it in this recon. Likely `student_api.py` or a portal route.

**State:** **Built** (Vegas-era) — the form exists and submits. How complete the submit handler is, I did not verify.

**Public arrival experience (architectural concept):** The architecture doc calls for a "paste a job → upload a resume → get a real gap analysis → see natural conversion CTAs" flow. That is **designed only** — no code implements the job-paste + instant-gap flow. The intake form is the current closest surface.

### 2.3 Gap analysis (student-visible)

`components/dashboard/gap-analysis-preview.tsx` renders a preview on the student dashboard. The full gap analysis data is in `gap_analyses` (30 rows) and generated by `agents/career-services/gap_analysis.py`.

**State:** Backend + UI preview **built**. Rich "what do I do about this gap" content (training recommendations, sequencing) is present as data but UX surface is preview-only — there's no dedicated gap-detail page for the student.

### 2.4 Match narratives (student-visible)

**State:** **Not built for students on `feature/finance-cockpit`.** The `match_narratives` table has 0 rows. Even if the generator landed, architecture calls these "recruiter notes" — not clear from the design doc whether students are the intended audience or whether they are for staff only.

### 2.5 Upskilling / learning-resource discovery

**State:** **Designed only.** No code, no table, no stub page.

### 2.6 Youth surface (adjacent — not strictly Coalition/Workforce)

`portal/student/app/youth/page.tsx` — a 475-line static marketing landing for CFA's youth programs. Architecture doc treats Youth as its own component. Included here only because it lives in the same Next.js app and shares the `lib/` helpers.

### 2.7 Summary — student audience

Three student surfaces are real: student dashboard (`/student`), intake form (`/careers`), and youth landing (`/youth`). Two student-facing value propositions from the architecture — **public arrival (gap-before-signup)** and **upskilling recommendations** — do not yet exist in code.

---

## Section 3 — Employers (secondary users)

### 3.1 Talent showcase

**UI surface:** `portal/student/app/showcase/page.tsx` — 404-line React client. Browsable/filterable candidate list with privacy redaction (first name + last initial). Fields shown per candidate: location, availability, track, profile completeness, parse confidence, top skills, total skills.

**Backend:** `agents/portal/showcase_api.py` on :8002 — 3 endpoints:
- `/api/showcase/candidates` — filterable list
- `/api/showcase/filters` — filter options (skills, locations, tracks)
- `/api/showcase/candidates/{student_id}` — detail view

**State:** **Built** (Vegas-era). Uses `resume_parsed=TRUE` as a de facto eligibility proxy (per Phase 1 note); does not strictly enforce `showcase_active=true`.

**Data dependency:** `students` table (filtered by eligibility), `student_skills`, `student_work_experience`.

**Honest assessment:**
The showcase is functionally built but empty (0 students have `showcase_active=true`). An employer who lands on `/showcase` today sees 151 students at most (those with `resume_parsed=true`) and probably far fewer that actually display meaningful profile data — 71 students meet `completeness >= 0.7`. The employer experience is a functional shell over a mostly-empty catalog.

### 3.2 `/for-employers` landing

**UI surface:** `portal/student/app/for-employers/page.tsx` — marketing page with nav links to Showcase, College Login, Consulting. No gated employer login, no employer account, no direct employer action surface beyond "browse the showcase" and "contact CFA."

**State:** **Built — but not interactive.** There is no employer-side login, no per-employer saved searches, no shortlist, no messaging. All employer-facing flow stops at "browse the public showcase."

### 3.3 Employer-facing communication infrastructure

**None on the Coalition side.** `agents/portal/email.py` and `email_templates.py` exist (on `development`), but they are used by the Scoping / Consulting workflow, not for employer outreach from Coalition.

The architecture doc anticipates "Request through CFA → routed messaging" — not built.

### 3.4 Summary — employer audience

The employer experience is **browse-only**. A real employer workflow (log in → shortlist → contact → track hiring history) is present only as architecture intent. The "Employer Agent" (`agents/assistant/employer_agent.py`) provides a conversational surface, but there is no dedicated employer dashboard.

---

## Section 4 — Partners (tertiary users)

### 4.1 College partner portal

**UI surfaces:**
- `portal/student/app/college/page.tsx` — partner dashboard. Takes `?token=<...>` for tokenized auth. Renders graduate counts, placement metrics, curriculum-gap signals, employer-demand summary.
- `portal/student/app/college/login/page.tsx` — 91-line token-entry form.

**Backend:** `agents/portal/college_api.py` on :8004. Primary route: `GET /api/college/dashboard/{token}` — returns all dashboard data in one payload.

**State:** **Built** (Vegas-era). 2 partners in `college_partners` table (Bellevue College, North Seattle College). `college_programs` has 4,669 rows; `program_skills` has 10,754 rows. Matching of graduates to institutions is done via ILIKE on `student.institution` vs. `college_partner.institution_name`.

**Support modules:**
- `agents/college-pipeline/map_programs_to_skills.py` — populates `program_skills` by mapping CIP/SOC codes → skills taxonomy. Runs offline, not a live service.

**Gaps / pain points visible in code:**
- ILIKE matching is fuzzy — a student whose institution field reads "Bellevue College" matches; "BC" probably doesn't.
- No way for a college partner to upload their graduate list or request employer introductions from the portal. The architecture doc mentions "post upcoming cohort availability" and "request employer partnerships" as features — not built.
- Only the dashboard endpoint is implemented. No CRUD, no authenticated edit surface.

### 4.2 Provider-facing surfaces

**State:** No dedicated provider UI. Providers appear in the Finance cockpit's `providers` tab (6 providers) as data Krista manages, and in the grant-compliance app's schema (allocations, transactions), but providers themselves do not log in or interact with the platform.

### 4.3 Funder-facing surfaces (WJI)

**UI surface:** `portal/student/app/wji/page.tsx` — 556-line React page for grant-partner uploads (placements + payments Excel) + summary stats dashboard.

**Backend:** `wji_api.py` on :8007 (§1.3 above).

**State:** **Built** (Vegas-era).

**Audience ambiguity:** Per the prompt — "WJI reporting is produced *for* funders but they don't use the platform directly." True. The `/wji` page is used by **grant partner staff** (organizations CFA subcontracts with — vendors in `wji_payments.vendor`) who upload their data, and by **internal CFA staff** (Bethany) to view the aggregate. Funders (Alma/WSB) are the report recipients, but they receive outputs, not platform access.

### 4.4 Summary — partner audience

College partners have a real (if minimal) read-only dashboard. Grant partners have an upload surface that doubles as a CFA staff view. Providers and funders do not log in. This matches the architecture doc's "partners are tertiary" framing — none of these surfaces have the depth of the staff cockpit.

---

## Section 5 — Shared / cross-cutting infrastructure

Code that serves multiple audiences or is genuinely cross-cutting.

### 5.1 `_shared/` cockpit primitives

`portal/student/app/internal/_shared/` — 19 files on `feature/finance-cockpit`:

| File | Purpose |
|---|---|
| `agent-shell.tsx` | Outer page shell used by every staff cockpit (Finance, Recruiting) |
| `cockpit-shell.tsx` | Inner layout with sidebar + topbar + content |
| `sidebar.tsx` | Left navigation (currently hand-enumerated: Finance, Recruiting, Consulting-inquiry-triage) |
| `tabs-bar.tsx` | Tabs strip for multi-view pages |
| `hero/hero-cell.tsx`, `hero/hero-grid.tsx` | Top-of-page KPI tiles |
| `drill/drill-panel.tsx` | Slide-out detail panel for drill interactions |
| `drill/sections/drill-section-*.tsx` (7 files) | Polymorphic drill content renderers: `action-items`, `chart`, `prose`, `renderer`, `rows`, `table`, `timeline`, `verdict` |
| `status-chip.tsx`, `verdict-box.tsx`, `coming-soon.tsx` | Atomic primitives |
| `types.ts` | Shared TypeScript types |

**Audience:** all intermediary staff. This is the primitive library that makes the cockpits coherent.

**State:** **Built.** Heavily used by Finance; partially used by Recruiting (workday page uses `AgentShell`). Ready for new staff cockpits to adopt.

**Not on `integrate/grant-compliance-scaffold`.** A merge or adaptation would need to bring this forward.

### 5.2 Authentication

**State:** **Essentially nonexistent on these branches.** Student portal uses `?id=<uuid>`. College portal uses `?token=<...>`. Staff cockpits have **no auth** — they assume a trusted context (localhost or CFA VPN). Magic-link + tier-decorator work exists on the `issue-24`/`issue-25` branches under `refactor/staging` but does not intersect this document's scope.

### 5.3 LLM abstractions

`agents/llm/client.py` — provider-agnostic wrapper. Two entry points: `get_llm_response(messages, system_prompt)` and `get_structured_output(text, instructions)`. Currently routes to Gemini Flash via `google-generativeai`.

**Audience:** all six assistant agents + any backend that needs LLM calls.

**State:** **Built.** Removed on `refactor/staging` in favor of `packages/wfdos-common/wfdos_common/llm/` (with Anthropic/Azure/Gemini providers) but on this document's scope branches, `agents/llm/` is the shared path.

### 5.4 Microsoft Graph shared library

`agents/graph/` — `auth.py`, `sharepoint.py`, `teams.py`, `transcript.py`, `invitations.py`, `config.py`. Shared MS Graph wrapper used by scoping, grant ingestion, email sending, grant-compliance evidence collection.

**Audience:** backend services across Coalition (grant ingestion, email) + Consulting (scoping proposals).

**State:** **Built.**

### 5.5 Database schema and migrations

- `scripts/001-010` on `development` — schema + data backfill.
- `scripts/011-embeddings-metadata.sql` on `feature/finance-cockpit` — adds metadata columns to `embeddings` table.
- `scripts/011-job-board-agent-schema.sql`, `012-fix-embeddings-dimension.sql`, `013-broaden-scope-and-add-location.sql` on `claude/sleepy-wiles-f9fc04` — the job-board schema + embeddings fix + location columns.
- `agents/grant-compliance/alembic/` on `integrate/grant-compliance-scaffold` — that service's own Alembic-managed schema (distinct from the main `wfd_os` schema, though tables land in the same database).

**Audience:** all backend services.

**State:** The migration numbering itself is a known conflict (two different `011`s). Functionally, migrations 011–013 (sleepy) are **live in the database** while their source files are preserved on a lifeboat branch; migration 011 (feature) is **not yet applied** — per the branch reality map's Section 5.

### 5.6 The Staff Agent (role-aware)

`agents/assistant/staff_agent.py` is cross-cutting by design — it serves every staff role from one endpoint by switching briefing templates on `?user=`. Included here because it is the closest thing to a unified staff platform surface today.

**State:** **Built.** System prompt has role branches for Ritu, Gary, Krista, Bethany, Jason, Jessica. Tools: grant summary, consulting pipeline, cohort status, placement summary, recent inquiries, draft communication.

### 5.7 Summary — shared infrastructure

The shared cockpit shell (`_shared/`) and the staff agent are the two real cross-cutting assets. Everything else that looks shared (LLM client, Graph client, database) is infrastructure in the plumbing sense rather than audience-spanning in the product sense.

---

## Section 6 — Things that don't fit cleanly

Code that exists in the branches in scope but **does not serve Coalition/Workforce's audiences**. I flag explicitly.

### 6.1 BD / marketing / newsletter WIP — these are Consulting

All of the following live in the main folder's uncommitted working tree on `integrate/grant-compliance-scaffold`:

| Item | Audience | Evidence |
|---|---|---|
| `portal/student/app/internal/bd/` (`page.tsx` + `bd-client.tsx`, 34KB client) | **Consulting** — BD Command Center for Jason | `bd-client.tsx` API constants: `/api/consulting`. Endpoints: `/bd/priorities`, `/bd/hot-prospects`, `/bd/warm-signals`, `/bd/pipeline`, `/bd/email-drafts` |
| `portal/student/app/internal/jessica/` (`page.tsx`, 21KB) | **Consulting** — Marketing command center for Jessica | Component literally named `JessicaMarketingCenter`; pulls from `/api/consulting/marketing/*`; topic tags are consulting themes (ai-adoption, agentic-ai, cost-reduction, digital-transformation, etc.) |
| `portal/student/components/newsletter-subscribe.tsx`, `app/unsubscribe/` | **Consulting marketing** | Newsletter for Waifinder content distribution |
| `portal/student/app/resources/` | **Consulting (likely)** — content/lead-capture; not verified in this recon | Appears alongside newsletter/BD work |
| `agents/assistant/bd_agent.py`, `marketing_agent.py` (uncommitted) | **Consulting** | 8th and 9th conversational agents for BD + Marketing |
| `agents/apollo/hunter_client.py` (uncommitted) | **Consulting BD** | Apollo integration enhancement |
| `agents/market-intelligence/bd-pipeline/` (uncommitted) | **Consulting BD** | — |
| Modifications to `agents/portal/consulting_api.py` (+634 lines, uncommitted) | **Consulting** | BD + Marketing API endpoints under `/api/consulting/bd/*` and `/api/consulting/marketing/*` |
| Modifications to `agents/marketing/api.py` (+302 lines, uncommitted) | **Consulting marketing** | Newsletter + lead capture endpoints |
| Modifications to `agents/apollo/client.py` (+156 lines, uncommitted) | **Consulting BD** | Apollo contact search by domain/name |

**All of these are Consulting surfaces that happen to be uncommitted on the Coalition branch's worktree.** The misfile is accidental — the work was done in the main folder while it was checked out on `integrate/grant-compliance-scaffold`, but by audience the code belongs to Consulting.

### 6.2 `/internal` root page — misplaced Consulting Inquiries triage

`portal/student/app/internal/page.tsx` (1000+ lines) — despite living at the root of the staff cockpit, this page is a **Consulting Inquiries triage workbench for Jason (BD)**. Uses `/api/consulting`. Shows inquiries with Apollo contact IDs, project descriptions, sequence suggestions.

**Audience:** Consulting (BD). Currently occupies the prime navigation slot a Coalition leadership or cross-cockpit landing would want.

### 6.3 `agents/assistant/finance_agent.py` — ambiguous

Present on `integrate/grant-compliance-scaffold` as the 7th conversational agent. Name suggests Coalition (Krista); content not inspected in this recon. Flagged as unknown-audience.

### 6.4 `agents/grant-compliance/` — clearly Coalition/Workforce (but flagged in prompt)

The prompt asked "what is this actually?" — it is a **Coalition/Workforce Compliance/Quinn module, partially built as a standalone FastAPI**, not Consulting. Its own `README.md` says: "A grant-accounting and federal-compliance assistant that sits on top of QuickBooks. It proposes grant tagging for transactions, drafts time & effort certifications, runs 2 CFR 200 compliance checks, and generates funder-report drafts — always with a human in the loop and a full audit trail."

The four agents (Transaction Classifier, Time & Effort, Compliance Monitor, Reporting) align exactly with the K8341 workflow (classifier for invoices, time & effort for federal grant employees, compliance monitor for unallowable costs, reporting for SF-425 / foundation reports).

**Audience: Krista + Bethany (Coalition grant operations).** It belongs in Coalition/Workforce. The Phase 1 draft's "designed only" was wrong.

### 6.5 `agents/marketing/api.py` pre-existing routes — Consulting

On all branches in scope, `agents/marketing/api.py` already exists (233 lines on development, before the uncommitted +302). The pre-existing routes (pipeline, content) serve Consulting marketing operations, not Coalition. Not WIP — already there.

### 6.6 `agents/apollo/`, `agents/scoping/`, `agents/graph/` — infrastructure overlapping Consulting

These serve Consulting primarily (Apollo = BD lead enrichment, Scoping = Consulting sales pipeline, Graph = Microsoft 365 for Consulting + grant ingestion). Appearing in Coalition branches because they're shared plumbing, not because they serve Coalition audiences.

---

## Section 7 — Observations for code organization

Observations only. No proposals.

### 7.1 Where the current directory structure aligns with audience-first thinking

- **`portal/student/app/internal/` as the staff umbrella** works. Staff cockpits (Finance, Recruiting, and WIP BD / Jessica / Marketing) all live under `/internal/*`. The architecture doc's "Staff Agent lives on /internal" maps to a real directory. Sub-routes per role are directories. This is audience-first, even if the *names* of some sub-routes are confusing.
- **`portal/student/app/internal/_shared/`** is a clean shared-primitives library. It genuinely serves all staff audiences.
- **`portal/student/components/dashboard/`** is cleanly student-audience — all 8 files are for `/student/page.tsx` and none for staff.
- **`agents/career-services/gap_analysis.py`** — correctly located under a name that reflects its audience function.
- **`agents/portal/college_api.py`** — correctly isolated as the college partner backend.

### 7.2 Where the current structure fights audience-first thinking

- **`/internal/page.tsx` is wrong for its path.** It's a BD inquiry triage for Jason. A visitor to `/internal` gets Consulting content by default.
- **Recruiting workbench at `/internal/recruiting/` is unclaimed at the persona layer.** The architecture doc calls it "Jessica module," which is now known to be incorrect. No human role currently owns this cockpit in any doc.
- **Finance cockpit's `operations/` sub-page is split across branches.** Frontend on `feature/finance-cockpit`, backend (`agents/grant-compliance/`) on `integrate/grant-compliance-scaffold`. Neither branch can demonstrate this page working end-to-end without the other.
- **Two grant subsystems** live in `agents/grant/` (SharePoint + reconciliation, on `development`) and `agents/grant-compliance/` (QB + CFR + reporting, on `integrate`). Names suggest overlap but they are independent codebases with no cross-references.
- **`agents/portal/consulting_api.py` + `agents/portal/wji_api.py`** live in the same directory despite serving different components (Consulting vs. Coalition) and different audiences (BD staff / consulting clients vs. grant partners / Bethany). The `agents/portal/` name is a historical accident ("portal" = FastAPI-apps-that-back-the-portal); audience is not visible.
- **`agents/apollo/` is effectively Consulting infrastructure, but sits as a peer to Coalition agents** (`career-services`, `profile`, etc.). A reader of `ls agents/` cannot tell which directory belongs to which component.
- **Five of six agents in `agents/assistant/`** correspond to real product surfaces (student, employer, college, consulting, youth, staff). "staff_agent" serving all internal roles is correct, but the assistant layer doesn't differentiate Coalition staff agents (Krista-briefing, Bethany-briefing) from Consulting staff agents (Jason-briefing, Jessica-briefing) despite the briefings literally living in the same template.
- **Grant partners (uploaders) and Bethany (Coalition staff)** share the `/wji` surface. One route, two audiences. The UI doesn't differentiate or gate.
- **Uncommitted WIP on the Coalition branch is mostly Consulting code.** Accidents of session history, not deliberate organization — but a reader who pulls the branch today sees Coalition + Consulting mixed.

### 7.3 What would need to move if reorganizing by primary audience

Obvious wins (low controversy):
- **Jessica's Marketing workbench** (`app/internal/jessica/`) and **BD Command Center** (`app/internal/bd/`) both belong under a Consulting umbrella (e.g., `app/consulting/` or `app/internal/consulting/`). They are not Coalition.
- **`/internal/page.tsx`** (Consulting inquiry triage) belongs under a BD-named path, not `/internal` root.
- **Newsletter + `/unsubscribe`** belong under a Consulting Marketing path.
- **`agents/apollo/`, `agents/scoping/`, `agents/marketing/`** are Consulting infrastructure by audience, even if their current placement as peers of Coalition agents is tidy at the file-system level.

Harder calls (reasonable people could disagree):
- **`agents/grant-compliance/`** — Coalition by audience (Krista + Bethany), but structurally it's a standalone FastAPI with its own schema and its own lifecycle. Does it fold into `agents/grant/` (also Coalition), stay independent, or get renamed? Three defensible answers.
- **Recruiting workbench** — definitely Coalition, but naming it for a persona (Jessica in the docs; Leslie by elimination) risks the same misnomer problem we already have. Naming it structurally (`recruiting/`, `placement/`) might be safer.
- **`agents/graph/`** — truly cross-cutting (Coalition uses it for grant-compliance evidence, Consulting uses it for scoping transcripts). Probably stays as shared infrastructure under some neutral name.
- **`/wji` as shared grant-partner-uploader + Bethany surface.** Splitting them is more code; keeping them is confusing. Defensible either way.

### 7.4 A non-moving observation: audience clarity in docs and naming

Across the three source docs (architecture, Phase 1, branch reality map) and the code, **four different names are used for overlapping ideas**:

| Code directory | Architecture-doc name | Persona the code actually serves |
|---|---|---|
| `agents/grant-compliance/` | "Compliance / Quinn (designed only)" | Krista + Bethany (it's built, not designed-only) |
| `app/internal/recruiting/` | "Recruiting / placement staff workbench (Jessica module)" | Unnamed placement specialist (**not Jessica**) |
| `app/internal/jessica/` | n/a — not in architecture doc | Jessica (Marketing — **Consulting**, not Coalition) |
| `app/internal/finance/` | "Finance & operations" | Krista |

The mismatch between directory names, architecture-doc names, and persona intent is the single biggest readability problem. A new reader arriving at the repo cannot tell which audience any given directory serves without triangulating across three docs.

---

## Appendix A — Corrections to prior documents

### A.1 To `wfd_os_architecture.md`

- **Line ~246 / "Jessica module"**: Misnomer. The actual Jessica does Marketing (Consulting). The Recruiting workbench's persona is unnamed. Recommend renaming the module in-doc or providing a persona.

### A.2 To `wfd_os_code_reality_phase1.md`

- **"Compliance / Quinn — designed only, no code"**: Incorrect. `agents/grant-compliance/` on `integrate/grant-compliance-scaffold` is a 62-file partially-built FastAPI with working rule engine, QB OAuth, MS Graph integration. Agents are skeletons; API routes are defined; schema is live via Alembic.
- **"Recruiting / placement staff workbench — built (Phases 2B–2E)"**: Partial. Only `workday/` is built; `applications/` and `caseload/` are explicit `ComingSoon` stubs.

### A.3 To `wfd_os_branch_reality_map.md`

- **Section 3.2.B, Recruiting workbench** was listed as fully built ("applications, caseload, workday"). Two of the three are `ComingSoon` stubs. Recommend correcting to "built (workday only); applications + caseload are stubs."
- **Section 3.3.B, Assistant `finance_agent.py`** was flagged as "a 7th conversational agent not on any other branch." This is correct. The uncommitted WIP adds `bd_agent.py` and `marketing_agent.py` as 8th and 9th. (Section 3.3.C of the branch reality map already notes this in the WIP inventory.)
- **Section 6.4, "`agents/grant-compliance/` — what is this actually?"** — this document answers: it is Compliance/Quinn as partially built. Not Consulting.

---

## Appendix B — Questions this document surfaces but does not answer

These are observations Ritu may want to direct subsequent investigation or conversation with Gary toward. Informational only.

1. **Who is the placement specialist persona?** Is it Leslie (by elimination)? Someone unnamed? Is placement-specialist-work intended to continue as a distinct role, or is it a temporary scaffolding for the "Jessica module" architecture entry that never matched reality?
2. **What's Leslie's role?** She is in the staff user list but has no briefing template and no UI surface.
3. **Should `agents/grant/` and `agents/grant-compliance/` be one module?** They serve overlapping staff (Bethany), use overlapping data sources (grant documents), and have no cross-reference in code.
4. **Does `/internal/page.tsx` keep its path?** If the Consulting inquiry triage stays at `/internal` root, the cockpit's default first impression is Consulting. If it moves, the referrers from staff links need updating.
5. **Is the career-coach / case manager persona a planned module or a deferred one?** The architecture doc lists career services as built, but in practice the career-coach user has no surface at all. The only code near this concept is `agents/career-services/gap_analysis.py` (student-output-producing, not coach-facing) and the wtc `CaseMgmt` models (not ported).
6. **Who uses `/wji` primarily?** Grant partners upload, Bethany reviews. Either audience would benefit from a partitioned view.
7. **Match narratives — for staff or students?** The architecture doc says "recruiter notes" suggesting staff-first. Students in the same doc are promised "what students see about specific job matches." Both? If so, the same `match_narratives` row feeds two different UIs with potentially different permissions.

---

*End of audience view. Output: `docs/coalition_workforce_audience_view.md`.*
