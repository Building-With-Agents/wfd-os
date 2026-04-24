# wfd-os Code Reality — Phase 1 Draft

*Date: April 19, 2026*
*Owner: Ritu Bahl*
*Status: DRAFT — based on Ritu-Claude conversation context. Requires Claude Code verification (Phase 2) before treating as authoritative.*

This document maps the architectural components and modules from
`wfd_os_architecture.md` to the actual codebase as best I understand it
from our conversations and prior recons. It identifies what exists, what's
in the wrong place, what's missing, and what needs to be ported from wtc.

**Important caveat:** I don't have direct access to the codebase in this
conversation. This draft is based on:
- The Phase 2D/2E/2F/2G build work we've done together this month
- The earlier Claude Code recon on student-facing infrastructure
- The recon that cloned and inspected Building-With-Agents/watechcoalition
- What Ritu has described in conversation

Every statement should be verified in Phase 2. Treat this as a working
hypothesis to be tested, not a source of truth.

---

## Part 1 — Overall Codebase Layout

**Expected structure:**

Based on our build work, the wfd-os codebase is organized roughly:

```
wfd-os/
├── agents/
│   ├── finance/              # Finance module backend
│   ├── job_board/            # Recruiting module backend
│   ├── portal/               # Multiple FastAPI apps
│   │   ├── student_api.py    # Student profile module backend
│   │   ├── showcase_api.py   # Talent showcase module backend
│   │   ├── college_api.py    # College partner module backend
│   │   ├── consulting_api.py # Consulting modules backend
│   │   └── wji_api.py        # WJI reporting module backend
│   ├── assistant/            # 6-agent conversational layer
│   ├── career-services/      # Gap analysis module
│   ├── profile/              # Resume parsing
│   └── reporting/            # Analytics dashboard
├── portal/
│   └── student/              # Next.js frontend
│       ├── app/
│       │   ├── internal/     # Staff-facing cockpit
│       │   │   ├── finance/
│       │   │   └── recruiting/
│       │   ├── student/      # Student dashboard
│       │   ├── showcase/
│       │   ├── careers/
│       │   ├── college/
│       │   ├── youth/
│       │   ├── wji/
│       │   ├── coalition/    # Duplicated coalition tree
│       │   ├── cfa/
│       │   │   └── ai-consulting/
│       │   └── client/
│       └── components/
└── scripts/                  # Migrations, utilities
```

**Known issues with the current layout:**

1. **Everything is flat under `agents/` and `portal/student/app/`.** There's
   no structural hint that things belong to different components. The
   architectural separation (Youth / Coalition/Workforce / Consulting)
   isn't reflected in the directory structure.

2. **The `/coalition/*` duplicated tree in the frontend.** The earlier
   recon flagged this — there's a parallel set of pages under
   `app/coalition/` that mirrors much of what's at the top level. This
   is architectural debt from the "two brands, eventually consolidate"
   thinking that's since been clarified.

3. **`agents/portal/` is a dumping ground.** Five FastAPI apps in one
   directory with no clear component affiliation. student_api and
   showcase_api belong to Coalition/Workforce; consulting_api belongs
   to Consulting; wji_api belongs to Coalition/Workforce (grant
   reporting); college_api belongs to Coalition/Workforce.

4. **The `portal/student/` name is misleading.** It's the whole
   Next.js app, not just student-facing. It houses the staff cockpit,
   marketing pages, and everything else. Name was chosen early and
   stuck.

---

## Part 2 — Component Mapping (What Lives Where)

For each component, I map what I believe is currently in the codebase.

### Youth Component

**Backend:** Nothing substantive. There's no `agents/youth/` directory.
No youth-specific API.

**Frontend:** One file — `portal/student/app/youth/page.tsx` — a static
marketing page.

**Data model:** No youth-specific tables that I know of. All data
infrastructure is oriented toward adult workforce development.

**Assessment:** Essentially a stub. The Youth component exists in the
architecture document but barely exists in code.

### Coalition / Workforce Component

**Backend surface:**
- `agents/finance/` — Finance module (cockpit_api on :8013)
- `agents/job_board/` — Recruiting module (API on :8012, includes
  matching, narratives, Phase 2G work)
- `agents/portal/student_api.py` — Student profile backend (:8001)
- `agents/portal/showcase_api.py` — Talent showcase backend (:8002)
- `agents/portal/college_api.py` — College partner backend (:8004)
- `agents/portal/wji_api.py` — WJI reporting backend
- `agents/career-services/gap_analysis.py` — Gap analysis generator
- `agents/profile/parse_resumes.py` — Resume parsing
- `agents/profile/link_resumes.py` — Resume linking pipeline
- `agents/assistant/api.py` (:8009) — 6-agent conversational layer
  (partially serves student chat)

**Frontend surface:**
- `portal/student/app/internal/finance/` — Finance cockpit UI
- `portal/student/app/internal/recruiting/` — Recruiting Workday UI
- `portal/student/app/student/` — Student dashboard
- `portal/student/app/showcase/` — Employer talent browse
- `portal/student/app/careers/` — Student intake form
- `portal/student/app/college/` — College partner dashboard
- `portal/student/app/wji/` — WJI grant dashboard
- `portal/student/app/for-employers/` — Employer marketing landing
- `portal/student/app/coalition/*` — Duplicated coalition tree (should
  probably go away)
- `portal/student/components/dashboard/` — Student dashboard components
  (journey pipeline, gap analysis preview, job matches, showcase
  status, etc.)
- `portal/student/app/internal/_shared/` — Shared cockpit infrastructure
  (drill panel, hero grid, section renderers, tabs)

**Data model:** The bulk of the Postgres schema serves this component:
students, student_skills, student_work_experience, student_journeys,
gap_analyses, jobs_enriched (Phase 2D), applications, match_narratives
(Phase 2G), college_partners, college_programs, program_skills. Plus
finance tables.

**Assessment:** The densest component in the codebase, matches the
architecture document's framing of this as the flagship component.

### Consulting Component

**Backend:**
- `agents/portal/consulting_api.py` — Consulting intake + pipeline
  (12 routes under /api/consulting/*)

**Frontend:**
- `portal/student/app/cfa/ai-consulting/` — Waifinder consulting
  funnel (landing, blog, chat)
- `portal/student/app/client/` — Client portal surface

**Data model:** Not clearly separated from Coalition/Workforce data.
Consulting inquiries and engagements may live in the same database as
student/Coalition data. Worth verifying in Phase 2.

**Assessment:** Partially built. The customer-facing consulting funnel
exists. Internal consulting operations tooling (pipeline management,
engagement delivery, apprentice workforce management) is partially
present but not clearly organized. Nothing for apprentice curriculum
delivery — that's all in wtc.

**Important mis-placement to flag:** The path `app/cfa/ai-consulting/`
uses the "cfa" segment which is wrong under the current structure.
This is Waifinder's consulting, not CFA's. The path should probably
be `app/consulting/` or similar. Legacy naming from when everything
was under the CFA umbrella before the three-entity structure
clarified.

---

## Part 3 — Module-by-Module Inventory

For each module from the architecture document, my best read on code status.

### Youth Component Modules

**Youth program marketing surface** — Built, minimal.
- Frontend: `portal/student/app/youth/page.tsx` (static)
- Backend: None
- Status: As architecture states — minimal marketing page only.

**Youth participant management** — Unbuilt. No code, no schema, no plan.

**Youth curriculum delivery** — Unbuilt.

**Youth-family communication** — Unbuilt.

**Youth funding and sponsorship** — Unbuilt.

### Coalition/Workforce Component Modules

**Student profile** — Built (Vegas-era).
- Backend: `agents/portal/student_api.py` with 7 endpoints
  (profile, matches, gap-analysis, journey, showcase, chat, stats)
- Frontend: `portal/student/app/student/page.tsx` + dashboard
  components at `portal/student/components/dashboard/`
- Schema: `students` table (48 columns), `student_skills`,
  `student_work_experience`, `student_journeys`, `student_education`
- Resume parsing: `agents/profile/parse_resumes.py` +
  `link_resumes.py`
- Note: The student_api uses old skill-averaging matching, not the
  newer Phase 2D embeddings. Three matching code paths exist
  (mentioned in Part 6 below).

**Job matching & gap analysis** — Built, with complications.
- Backend:
  - `agents/job_board/` for the Phase 2D embedding-based matching
  - `agents/career-services/gap_analysis.py` for gap analysis
  - `agents/portal/student_api.py` has its own matching logic
    (skill vector averaging)
- Schema: `jobs_enriched` (Phase 2D), `gap_analyses` (30 rows of
  rich data from original React platform)
- Note: Three separate matching code paths that don't know about
  each other. Consolidation needed.

**Match narratives** — In progress (Phase 2G).
- Backend: `agents/job_board/match_narrative.py` (computes overlap,
  calls gpt-4.1-mini for narrative generation)
- Schema: `match_narratives` table (pending migration, Phase 2G)
- Frontend: Integration into student drill (in flight)

**Talent showcase** — Built (Vegas-era).
- Backend: `agents/portal/showcase_api.py`
- Frontend: `portal/student/app/showcase/page.tsx`
- Note: Uses `resume_parsed=TRUE` as eligibility proxy, doesn't
  enforce `showcase_active` flag.

**College partner portal** — Built (Vegas-era).
- Backend: `agents/portal/college_api.py`
- Frontend: `portal/student/app/college/`
- Schema: `college_partners` table (2 partners: Bellevue College,
  North Seattle College)

**Recruiting / placement staff workbench (Jessica module)** — In
progress (Phases 2B-2G).
- Backend: `agents/job_board/` with full API including Phase 2E
  student drill endpoint, Phase 2G match narrative endpoint
- Frontend: `portal/student/app/internal/recruiting/workday/` with
  drill system, shared components
- Schema: uses jobs_enriched, students, student_skills,
  applications, match_narratives
- Status: Most actively developed surface. Phase 2F polish items
  pending.

**Finance & operations** — Built (Phase 1-2).
- Backend: `agents/finance/cockpit_api.py` on :8013
- Frontend: `portal/student/app/internal/finance/`
- Data: reads Excel fixtures from Krista's exports
- Status: Functional, being actively tested.

**WJI reporting** — Built (Vegas-era).
- Backend: `agents/portal/wji_api.py` (6 routes)
- Frontend: `portal/student/app/wji/page.tsx`

**Compliance / Quinn** — Designed only. No code.
- Design conversations held about scope (K8341-narrow for v1),
  user (Krista), interaction model (Teams via Graph API),
  approach (structured agent with human-in-loop graduating to
  autonomy)
- Nothing built yet.

**Upskilling / learning resource discovery** — Designed only. No code.
- Concept developed in conversation today.
- Would be a new module — agent that curates free courses from
  YouTube and other sources.

**Student-facing portal** — Built but underused.
- Same code as Student profile module's frontend
  (`portal/student/app/student/page.tsx`)
- Status: UI is complete, but students aren't flowing through it
  (low traffic, mostly Handshake-gate signups that didn't engage)

**Public arrival experience** — Designed only. No code.
- Build spec drafted (see `coalition_arrival_spec.md` from earlier)
- Would be a new module — paste job + upload resume + get gap
  analysis without signup

### Consulting Component Modules

**Consulting funnel** — Built (Vegas-era).
- Backend: `agents/portal/consulting_api.py` (inquire endpoints)
- Frontend: `portal/student/app/cfa/ai-consulting/` (landing, blog,
  chat)
- Note: The `cfa/ai-consulting` path is misleading — should be under
  a non-CFA path since this is Waifinder's business.

**Consulting pipeline / engagement management** — Built (Vegas-era).
- Backend: `agents/portal/consulting_api.py` (pipeline endpoints —
  CRUD on inquiries and engagements)
- Frontend: Presumably somewhere, possibly in `/client/` or an
  internal staff view. Needs verification.

**Client portal** — Built (Vegas-era), state unclear.
- Frontend: `portal/student/app/client/page.tsx`
- Backend: Presumably part of consulting_api.
- Status: Exists but unclear how complete or used.

**BD and marketing** — Built (Vegas-era), state unclear.
- Not sure where this lives exactly.
- May be part of consulting_api or separate.
- Needs verification.

**Apprentice workforce management** — In wtc, needs port.
- Currently lives in `Building-With-Agents/watechcoalition` — the
  Prisma schema has rich models (Jobseeker, employees, CaseMgmt,
  CareerPrepAssessment with 6 domain ratings, etc.)
- None of this is in wfd-os yet.
- Port is Gary's work, per Ritu's direction.

**Apprentice curriculum delivery** — In wtc, needs port.
- Gary built this for Cohort 1 — weekly sprint cadence, training
  exercises, onboarding docs, evaluation infrastructure.
- TRAINING_EXERCISES.md and ONBOARDING.md in wtc describe the
  structure.
- Port is Gary's work.

---

## Part 4 — What's In the Wrong Place

Architectural mismatches to fix eventually:

1. **`portal/student/app/cfa/ai-consulting/`** — "CFA" in the path is
   incorrect. This is Waifinder's consulting business. Rename to
   something like `app/consulting/` or `app/waifinder/`. Low urgency
   but should happen before any customer-facing use.

2. **`portal/student/app/coalition/*` duplicated tree** — Parallel
   pages that mirror top-level pages. Legacy from earlier branding
   thinking. Should be consolidated into the top-level pages with
   styling/theming differences rather than duplicated routes.

3. **`agents/portal/` mixed responsibilities** — Houses FastAPI apps
   for multiple components (Coalition/Workforce + Consulting + WJI).
   Should be organized by component:
   - `agents/coalition/` → student_api, showcase_api, college_api,
     wji_api, career-services
   - `agents/consulting/` → consulting_api
   - `agents/finance/` already exists under Coalition/Workforce
   - `agents/job_board/` already exists under Coalition/Workforce

4. **`portal/student/` is the whole frontend** — Name implies it's
   only student-facing, but it houses staff cockpit, marketing,
   everything. Consider renaming to `portal/` or `web/` with
   subdirectories for different user audiences. Large refactor;
   defer unless urgent.

5. **Three matching code paths** (Phase 2D note): skill vector
   averaging in student_api, precomputed gap_analyses rows, and
   Phase 2D embeddings in job_board. They don't know about each
   other. Should be consolidated so the student dashboard uses
   the same matching logic as the recruiter workbench.

6. **The `agents/career-services/gap_analysis.py` generator** — Serves
   the gap analyses that show up on the student dashboard. Should
   probably be inside `agents/job_board/` since it's conceptually
   part of the matching-and-gap subsystem, not a separate service.

---

## Part 5 — What Needs to Come From wtc

Work that currently lives in `Building-With-Agents/watechcoalition`
and needs to be ported to wfd-os before wtc can sunset:

### From wtc itself

**Apprentice workforce management** — The data models (Jobseeker with
apprentice-specific fields, CaseMgmt, CaseMgmtNotes) and the UI for
managing apprentices through the program.

**Apprentice curriculum delivery** — The structured learning
infrastructure. TRAINING_EXERCISES.md is the content; the code that
delivers and tracks it is what needs to move.

**CareerPrepAssessment infrastructure** — wtc has a 6-domain rating
system (Cybersecurity, DataAnalytics, ITCloud, SoftwareDev,
DurableSkills, Branding) with dedicated models for each. wfd-os
doesn't have this. If Waifinder's apprenticeship uses it, the
infrastructure needs to come over.

**WebAuthn passkey auth** — wtc has NextAuth v5 with WebAuthn
configured. wfd-os has no auth. This is a reference implementation
to learn from when building wfd-os auth, not infrastructure to port
directly (different stack), but it's a proven pattern.

**Richer student data model** — wtc's Prisma schema has more
normalized decomposition than wfd-os's flatter students table.
JobseekerJobPosting with matching artifacts (totalMatchScore,
gapAnalysis, linkedInProfileUpdate, elevatorPitch, generatedResume)
is richer than anything in wfd-os. Worth evaluating: adopt wtc's
data model, or evolve wfd-os's simpler model?

**Case management workflow** — wtc has CaseMgmt and CaseMgmtNotes.
This is staff-facing workflow for managing students through the
program. Jessica probably needs something like this eventually.
Worth porting.

### From Building-With-Agents/job-intelligence-engine

**The JIE pipeline** — Python agents for job sourcing, normalization,
skills extraction, clustering, salary analytics, co-occurrence
analysis. This is the analytics layer that Cohort 1 has been
building through Weeks 1-7.

**Decision needed:** Does JIE get absorbed into wfd-os as a module, or
does it remain a separate service that wfd-os calls via API? Either
works architecturally. Absorption simplifies deployment; separation
preserves independent iteration.

---

## Part 6 — What Needs to Be Built New

Modules in the architecture document that don't exist anywhere yet:

**Compliance / Quinn** — AI compliance assistant. Designed, not built.
Estimated: multiple focused build sessions.

**Upskilling / learning resource discovery** — The YouTube course
agent. Conceptually designed in today's conversation. Estimated:
2-3 weeks for minimum viable, 6-8 weeks for catalog-backed version.

**Public arrival experience** — Gap analysis before signup. Build
spec drafted (coalition_arrival_spec.md). Estimated: 2-3 Claude
Code sessions for v1.

**Real auth infrastructure** — Magic-link, OAuth, or similar. wtc's
NextAuth+WebAuthn is the reference pattern. Estimated: 1-2 focused
sessions to build from scratch in wfd-os, or longer if we adopt
the wtc patterns.

**Multi-tenancy** — The platform currently assumes one customer
(CFA). Commercial SaaS requires multi-tenant data isolation. This
isn't a single module but a cross-cutting architectural change
affecting every module.

**Module licensing / feature flags** — For "design broad, implement
narrow" to work commercially, we need infrastructure for enabling
and disabling modules per customer. Configuration schema,
permission enforcement, pricing-tier logic. Not built.

**Data portability / export** — Customers who license the platform
and later leave need to take their data with them. No export
functionality today.

**Youth component substance** — Youth participant management,
curriculum delivery, family communication, funding. All unbuilt.
Low priority unless Youth becomes a strategic push.

---

## Part 7 — Build Roadmap (Rough)

Ordering suggestions based on dependencies and strategic value. This
is a hypothesis — refine based on what Claude Code finds and based on
business priorities.

**Near-term (next 1-3 months):**

1. Complete Phase 2G (match narratives in UI) — in flight
2. Phase 2F polish items (apply URL hyperlink, description expand,
   job drill completeness, skills rendering fix, URL normalization)
3. Matched-students table redesign (design work, then build)
4. Consolidate the three matching code paths — pick one, deprecate
   the others
5. Address the `/coalition/*` duplicated tree

**Mid-term (3-6 months):**

6. Public arrival experience (gap analysis before signup)
7. Real auth infrastructure (unblocks CFA deployment)
8. Multi-tenancy infrastructure (unblocks second customer)
9. Port apprentice workforce management from wtc (Gary)
10. Port apprentice curriculum delivery from wtc (Gary)

**Longer-term (6-12 months):**

11. Quinn compliance agent
12. Learning resource discovery agent
13. JIE integration (absorb or formalize as service)
14. Module licensing / feature flag infrastructure
15. wtc sunset (when items above make it feasible)

**Deferred indefinitely unless triggered:**

16. Youth component substance (unless CFA's youth program technology
    needs grow)
17. Data portability tooling (until a real customer asks)
18. Generic LMS features (intentionally out of scope)

---

## Part 8 — Gary Coordination

Things that are Gary's work rather than something for you or Claude
Code sessions:

**From wtc to wfd-os:**
- Apprentice workforce management port
- Apprentice curriculum delivery port
- JIE integration decision + execution
- Possibly: richer data model patterns

**Training cohort management:**
- Gary runs Cohort 1 on wtc currently
- He decides when wfd-os is ready for the cohort to transition
- Criteria for readiness are unclear — worth defining explicitly

**Decisions needing Gary's input:**
- JIE: absorb into wfd-os, or keep as separate service?
- Apprentice data model: port wtc's rich schema, or redesign?
- Cohort transition timing: what specifically needs to be true about
  wfd-os before the cohort moves?

**Communication suggestion:**
When the time comes to start coordinating the wtc sunset in earnest,
a focused conversation with Gary around these questions would be
more productive than trying to infer his intent from the code.

---

## Part 9 — Architecture Health Check

Does the code match the architecture document?

**Strong alignment:**
- Coalition/Workforce component — well-represented in code, matches
  architecture intent, has clear modules that map to directory
  structure (mostly)
- Finance and Recruiting modules — cleanly separated, well-scoped,
  match their architectural purpose

**Weak alignment:**
- Component boundaries aren't visible in the directory structure.
  You can't look at the code and know what component a module belongs
  to without outside knowledge.
- Consulting component is spread across multiple paths without clear
  organization.
- Youth component is aspirational — exists architecturally, barely
  exists in code.

**Architectural commitments not yet made:**
- Module interfaces are implicit. If we want true modularity, modules
  should communicate through documented APIs, not by reaching into
  each other's database tables.
- Multi-tenancy is not designed into the schema. Retrofitting this
  later is expensive.
- Feature flagging is nonexistent. If we want customer-configurable
  modules, the infrastructure for that doesn't exist.

**Refactoring that would improve alignment:**
- Reorganize `agents/` by component (coalition/, consulting/, youth/)
- Reorganize `portal/student/app/` similarly, or at minimum add clear
  namespace prefixes
- Consolidate the `/coalition/*` duplicated tree
- Rename `app/cfa/ai-consulting/` to something not misleadingly
  CFA-branded
- Extract shared infrastructure (auth when it exists, multi-tenancy,
  feature flags) out of specific modules into a clear platform core

**How urgent is this?**
Not very, yet. The code works. The cockpit is useful. The architecture
mismatch is confusing for newcomers but not blocking for you. Fix
opportunistically as other work touches these areas, or as a
deliberate refactoring sprint when wfd-os is nearing production
readiness.

---

## Part 10 — What This Document Doesn't Tell You

Being explicit about what's missing so Phase 2 can fill it in:

1. **Actual file-by-file status** — I've described modules at a high
   level; I haven't opened every file to see exactly what's there
   and what's not.

2. **Test coverage** — I have no visibility into what tests exist and
   what they cover. This matters for refactoring risk.

3. **Configuration and deployment** — Environment variables, deployment
   pipelines, hosting. Mostly invisible to me from this context.

4. **Exact data quality state** — How much data is in each table, how
   complete, how clean. Some covered by prior recons but not
   comprehensively.

5. **Actual commit history vs. Vegas-era work** — Git log details that
   would clarify what was built when and by whom.

6. **Unbuilt skeletons** — Code that was started but never finished.
   These exist (placeholder pages, stubbed functions) but I don't
   have a complete inventory.

7. **Dependencies and versions** — What libraries the platform relies
   on, where version upgrades are needed.

8. **Known bugs** — Beyond what we've surfaced in UI testing, there
   may be issues I don't know about.

Phase 2 (Claude Code recon) should fill these gaps.

---

## Part 11 — Recon Prompt for Claude Code

```
Recon task — read-only, do not modify anything.

Goal: verify and extend the attached Phase 1 code mapping document.
Ritu has drafted a component/module-level view of the codebase based
on conversation context. We need Claude Code to check that view
against the actual code and produce the authoritative version.

The Phase 1 draft is at:
/mnt/user-data/outputs/wfd_os_code_reality_phase1.md
(Or wherever Ritu places it.)

Also reference:
/mnt/user-data/outputs/wfd_os_architecture.md
(The architecture document that defines components and modules.)

For each claim in the Phase 1 draft about code location, file
purpose, or module status: verify against the actual code. For each
gap in the Phase 1 draft: fill it with what you find.

Specific tasks:

1. **Verify file locations and module mappings.** For every claim of
   the form "Module X lives at path Y" — confirm or correct.

2. **Fill in what Phase 1 couldn't see.** Specifically:
   - Test coverage per module (what tests exist, what they cover)
   - Configuration files and environment variables
   - Unfinished skeletons (pages/functions that exist but aren't
     complete)
   - Exact endpoints each API exposes vs. what the Phase 1 draft
     lists
   - Dependencies and versions (package.json, pyproject.toml,
     requirements.txt)

3. **Data quality snapshot.** For each key table (students,
   student_skills, gap_analyses, jobs_enriched, applications,
   match_narratives, etc.) — row count, null percentages on
   important columns, any data quality observations.

4. **Git history sanity check.** Look at git log to identify:
   - What commits happened in Vegas (approximately April 1-5)
   - What commits happened in the Initial commit on April 6
   - What's been committed since
   - Any patterns suggesting deferred cleanup or partial work

5. **Find what's in the wrong place.** The Phase 1 draft identifies
   several mismatches (`/coalition/*` duplication, `cfa/ai-consulting`
   naming, three matching code paths, `agents/portal/` mixed
   responsibilities). Verify these are real. Find others you notice.

6. **Cross-reference with wtc.** For each module the Phase 1 draft
   says "needs port from wtc" — verify the functionality exists in
   Building-With-Agents/watechcoalition (already cloned at
   C:/Users/ritub/Projects/watechcoalition). Don't port anything —
   just confirm what's there.

7. **Flag anything the Phase 1 draft got wrong.** If a module is
   described as "built" but the code is actually skeletal, say so.
   If something is "designed only" but actually has partial
   implementation, say so. Accuracy matters.

Output: a markdown document that can replace or supplement the
Phase 1 draft. Structure it similarly so the two are comparable.
Be explicit about what you verified vs. what you updated vs. what
you added.

**Do not make any changes to the code.** No refactors, no file moves,
no deletions, no new files. Pure read-only recon.

**Do not start any new work** — this is inventory and verification,
not building.

Stop when the recon document is complete. Ritu will review and
decide next steps.
```

---

*End of Phase 1 draft. Hand to Claude Code for Phase 2 verification.*
