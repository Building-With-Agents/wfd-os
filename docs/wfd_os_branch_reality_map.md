# wfd-os Branch Reality Map

*Date: April 20, 2026*
*Owner: Claude Code (read-only recon)*
*Status: AUTHORITATIVE snapshot of git state as of this timestamp. Source docs cross-referenced: `wfd_os_architecture.md` (Apr 19), `wfd_os_code_reality_phase1.md` (Apr 19), `wfd_os_code_reality_phase2.md` (Apr 19).*

This document answers: **what is wfd-os today, across all its parallel
branches?** Because the work is split across unmerged branches, no single
checkout shows the full platform. This map makes the split visible.

---

## Part 0 — The one-line summary

The platform has fractured into **four parallel development lines**, each
advancing a different part of the architecture, each complete enough to
demo, **none yet merged**:

- **`development`** — the common Vegas baseline. Everyone branched from here.
- **`feature/finance-cockpit`** — Ritu's Finance + Recruiting staff cockpit (Phase 2A–2E). Adds `agents/finance/`, `agents/job_board/`, full `_shared/` cockpit shell. 23 commits, unpushed.
- **`integrate/grant-compliance-scaffold`** — a **disjoint-history branch** carrying the grant-compliance FastAPI app and a simpler `/internal/finance` page. 11 commits on its own timeline. Also the main folder's current checkout, with **56 additional uncommitted items** containing BD + newsletter + Jessica + new docs work.
- **`claude/sleepy-wiles-f9fc04`** — a one-commit branch carrying DDL for job-board migrations 011–013 that are already live in Postgres but nowhere else in source.
- **`refactor/staging`** (Gary's) — a 51-commit platform-infrastructure line: `packages/wfdos-common/`, per-service packaging, CI, pre-commit, Docker dev, `agents/laborpulse/`, `scripts/smoke/`, structured docs. Does **not** contain Ritu's Phase 2 cockpit work.

The four lines are compatible conceptually but **conflict on specific files**
— particularly migration numbering (`011`), `portal/student/app/internal/finance/page.tsx`,
and the wfdos_common refactor of shared services (student_api.py,
consulting_api.py, marketing/api.py, apollo/client.py, CLAUDE.md).

---

## Part 1 — Branches in Scope

| Branch | Tip | Commits | vs `development` | Last commit | Pushed? |
|---|---|---|---|---|---|
| `development` | `571d5bd` | 4 | baseline | 2026-04-15 | yes (origin) |
| `feature/finance-cockpit` | `87b2db3` | 27 | **+23 / −0** | 2026-04-18 | **local only** |
| `integrate/grant-compliance-scaffold` | `1a2bec6` | 11 | **DISJOINT** (no common ancestor) | 2026-04-17 | **local only** |
| `claude/sleepy-wiles-f9fc04` | `291f7cc` | 5 | **+1 / −0** | 2026-04-17 | **local only** |
| `origin/refactor/staging` (Gary) | `a69fae8` | 55 | **+51 / −0** | 2026-04-19 | yes (origin) |

> The prompt noted that `integrate/grant-compliance-scaffold` might include a
> recent WIP commit. **It does not**: tip is still `1a2bec6` (Apr 17). The
> intended backup commit was not made. The WIP lives only as uncommitted
> working-tree changes in `C:\Users\ritub\Projects\wfd-os` — 56 items: 30
> modified + 26 untracked. See Section 3.C for the contents.

---

## Part 2 — How to read this document

- **State labels used in module inventories:** `built` (usable), `in progress` (active work, not done), `skeleton` (stub / scaffolding), `designed` (in docs only, no code), `n/a` (not relevant on this branch).
- **Presence is what the branch's HEAD commit contains**, not working-tree state. The one exception, flagged explicitly, is `integrate/grant-compliance-scaffold`, where the main folder's uncommitted changes carry substantive work that would extend the branch if committed.
- **"Conflict" means same file path, different file contents** across branches. These are the surfaces where a merge produces `<<<<<<<` markers.
- File counts come from `git ls-tree -r --name-only <branch>` and are total tracked files (not hand-curated module lists).

---

## Part 3 — Per-Branch Inventory

For each branch: A (summary) → B (module inventory) → C (branch-unique
content) → D (branch-shared content).

### 3.1 `development` — the Vegas baseline

#### 3.1.A Branch summary

- **Tip:** `571d5bd` "infra(nginx): snapshot production reverse-proxy config (#36)" (2026-04-15)
- **4 commits total**, all from April 6–15.
- **332 tracked files.**
- **Characterization:** The post-Vegas snapshot plus 3 small housekeeping commits (data-file removal, Azure resource docs, nginx proxy config). No Phase 2A–2G work. No wfdos_common. Serves as the **shared root** from which `feature/finance-cockpit` and `claude/sleepy-wiles-f9fc04` forked and from which Gary's `refactor/staging` also ultimately descends.

#### 3.1.B Module inventory

**Youth component**
- Youth marketing surface: **built** (`portal/student/app/youth/page.tsx`, 475-line landing).
- Participant management / curriculum / family comms / funding: **unbuilt**.

**Coalition / Workforce component**
- Student profile: **built.** `agents/portal/student_api.py` (488 lines, :8001), `portal/student/app/student/`, dashboard components. Table `students` has 48 cols; 4,727 rows in local Postgres.
- Resume parsing: **built but underused.** `agents/profile/parse_resumes.py` + `link_resumes.py`. Only 3% of migrated students parsed.
- Gap analysis: **built.** `agents/career-services/gap_analysis.py`. Table `gap_analyses` has 30 rows.
- Job matching (embedding-based) / job_board: **not on this branch.** No `agents/job_board/`. Only the skill-average path in `student_api.py`.
- Match narratives: **not on this branch.** No generator code.
- Talent showcase: **built.** `agents/portal/showcase_api.py` (:8002), `app/showcase/`. 0 students currently eligible.
- College partner portal: **built.** `agents/portal/college_api.py` (:8004), `app/college/`.
- Recruiting / placement staff workbench (Jessica): **not on this branch.** No `internal/recruiting/`, no `internal/jessica/`.
- Finance & operations: **not on this branch.** No `agents/finance/`, no `internal/finance/`.
- WJI reporting: **built.** `agents/portal/wji_api.py` (:8007), `app/wji/`.
- Compliance / Quinn: **designed only.**
- Upskilling / learning resource discovery: **designed only.**
- Student-facing portal: **built.**
- Public arrival experience: **designed only.**

**Consulting component**
- Consulting funnel: **built.** `agents/portal/consulting_api.py` (:8003, 974 lines), `app/cfa/ai-consulting/`.
- Consulting pipeline / engagement management: **built (same file).**
- Client portal: **built.** `app/client/page.tsx`.
- BD and marketing: **built, scattered.** `agents/apollo/client.py` (256 lines), `agents/marketing/api.py` (233 lines), `agents/assistant/api.py` (6 agents). No BD command center UI.
- Apprentice workforce management: **not here** (wtc).
- Apprentice curriculum delivery: **not here** (wtc).

**Platform infrastructure**
- wfdos_common shared libs: **not on this branch.**
- Agent ABC, auth (magic-link), tier decorators, edge proxy: **not on this branch.**
- CI / pre-commit / Docker: **not on this branch.**
- Nginx proxy: **present.** `infra/nginx/wfd-os.conf`.

**Other agents (not in the architecture doc's module list, but present)**
`agents/apollo/`, `agents/grant/`, `agents/graph/`, `agents/llm/`, `agents/market-intelligence/`, `agents/marketing/`, `agents/reporting/` (+ Vite dashboard), `agents/scoping/`, `agents/college-pipeline/` — all present and substantive.

#### 3.1.C Branch-unique content

None — `development` is the baseline; everything here is on most other branches by definition. The one exception: `.cursor/rules/llm-provider.mdc`, `infra/nginx/README.md`, `infra/nginx/wfd-os.conf` are **missing from `integrate/grant-compliance-scaffold`** (see Section 3.3.D).

#### 3.1.D Branch-shared content

Everything on development is reproduced on `feature/finance-cockpit` (identical) and `claude/sleepy-wiles-f9fc04` (identical, since both fork cleanly). `refactor/staging` reproduces the files but with content-level modifications on several shared services (see Section 3.5.D). `integrate/grant-compliance-scaffold` reproduces most files but from its own disjoint history — same content at the blob level for the vast majority (verified by blob-hash comparison on key files).

---

### 3.2 `feature/finance-cockpit` — Ritu's cockpit line

#### 3.2.A Branch summary

- **Tip:** `87b2db3` "feat(recruiting): Phase 2E — student drill with job-context back navigation" (2026-04-18)
- **+23 commits ahead of development, 0 behind.** Last updated yesterday.
- **396 tracked files** (+64 vs development).
- **Characterization:** The Finance + Recruiting staff cockpit line. Delivers Phase 2A (scaffold), 2B (cockpit_api on :8013 + DataSource), 2C (Workday UI consuming live API), 2D (student embeddings matching on :8012), 2E (student drill). Adds the shared cockpit shell (`_shared/`). **The only branch that instantiates the staff Workbench the architecture document calls out as the Jessica module.**

#### 3.2.B Module inventory

Diffs from `development` inventory only:

- **Job matching & gap analysis:** **in progress → partially built.** Adds `agents/job_board/` (3 files: `__init__.py`, `api.py`, `data_source.py`). This is the Phase 2D embedding-based matching path. Port :8012. **No `match_narrative.py` file** — the match-narratives generator is not in this tree. (Phase 2G work appears to be on yet another branch, or only designed.)
- **Match narratives:** **designed + schema only.** The `match_narratives` table exists in local Postgres on all branches (12 cols) but no generator code is on this branch. Verified: grep for `match_narrative` produces zero hits across `agents/`.
- **Recruiting / placement staff workbench:** **built.** `portal/student/app/internal/recruiting/` with 11 files: `applications/page.tsx`, `caseload/page.tsx`, `workday/page.tsx` + `workday-client.tsx`, components (`filter-chips`, `job-card`, `recruiting-chat-panel`, `recruiting-topbar`, `search-box`), `lib/api.ts`, `lib/types.ts`. Job listings with match counts, student drill with gap + narrative UI, application initiation.
- **Finance & operations:** **built.** `agents/finance/` (10 files: `__init__.py`, `cockpit_api.py`, `data_source.py`, plus a `design/` subdir with HTML templates and fixture artifacts). Frontend: `portal/student/app/internal/finance/` (13 files) with cockpit-shell components (activity-feed, chat-panel, decisions-list, topbar), tabs, lib helpers, `operations/` sub-route, and fixture JSON.
- **Shared cockpit infra:** **built.** `portal/student/app/internal/_shared/` (19 files): `agent-shell.tsx`, `cockpit-shell.tsx`, drill system (7 section renderers), hero system (cell + grid), sidebar, status-chip, tabs-bar, verdict-box. This is the primitive library powering both finance and recruiting.
- **Frontend library utility:** `portal/student/lib/fetch.ts` — **unique to this branch** (not on `development`, not on others below). Fetch helper used by cockpit pages.
- **Database migration:** `scripts/011-embeddings-metadata.sql` — this branch's 011 is **different from sleepy-wiles's 011** (see Part 4).

All other modules identical to `development`.

#### 3.2.C Branch-unique content

Versus every other branch in this map:

- `agents/finance/` (10 files)
- `agents/job_board/` (3 files — underscore name)
- `portal/student/app/internal/finance/` (13 files — rich cockpit; conflicts with integrate's 2-file version)
- `portal/student/app/internal/recruiting/` (11 files)
- `portal/student/app/internal/_shared/` (19 files)
- `portal/student/lib/fetch.ts`
- `scripts/011-embeddings-metadata.sql` (different content from sleepy-wiles's `011-job-board-agent-schema.sql`)
- 23 unique commits with detailed Phase 2A–2E history.

None of the above exist on `refactor/staging`, `integrate/grant-compliance-scaffold`, `claude/sleepy-wiles-f9fc04`, or `development`.

#### 3.2.D Branch-shared content

Everything else (agents/*, portal/*, scripts/001–010, infra/nginx, CLAUDE.md, etc.) is **blob-identical to `development` and to `claude/sleepy-wiles-f9fc04`.** Not identical to `refactor/staging` (Gary has re-modified several shared services; see 3.5.D). `integrate/grant-compliance-scaffold` has the same content for most files but from its own history.

---

### 3.3 `integrate/grant-compliance-scaffold` — the disjoint grant line

#### 3.3.A Branch summary

- **Tip:** `1a2bec6` "Add /internal/finance portal page + finance_agent" (2026-04-17)
- **DISJOINT from `development`.** No common ancestor. Its own 11-commit history starts at `6338bc9` "Initial commit: WFD OS — Workforce Development Operating System" (2026-04-06) — a separately-authored initial commit that packages the same Vegas import but is not the same git object as `development`'s `fb319e2`.
- **395 tracked files.**
- **Characterization:** Built to host a grant-compliance FastAPI backend (imported from a separate Claude chat session) plus a simpler `/internal/finance` page and a `finance_agent` conversational agent. Created independently from `development` — probably branched off a parallel checkout. **This is the only branch with `agents/grant-compliance/`.**
- **Main folder is currently checked out on this branch**, with substantial uncommitted work on top (see 3.3.C).

#### 3.3.B Module inventory

Diffs from `development`:

- **Compliance / Quinn:** **partially built as a different thing.** Not Quinn specifically — this is `agents/grant-compliance/`, a FastAPI app (62 files) with its own Alembic migrations, source tree under `src/grant_compliance/`, 4 agents (classifier, compliance, reporting, time_effort), 8 route files (allocations, compliance, grants, qb_oauth, reports, time_effort, transactions), QuickBooks OAuth integration (`qb_oauth.py` + tokens table), audit logging, config, schemas. Own pyproject.toml and pytest tests (not verified in this recon).
- **Finance & operations (frontend):** **skeleton.** `portal/student/app/internal/finance/page.tsx` + `finance-client.tsx` — only 2 files, 79-line `page.tsx`. **This is a DIFFERENT implementation from `feature/finance-cockpit`'s 13-file `internal/finance/` tree.** Both branches have `page.tsx` but with different content (51 lines on finance-cockpit using server-component wrapper + cockpit-shell, 79 lines here using a simpler client component). **Merge conflict when both branches meet.**
- **Assistant — finance agent:** `agents/assistant/finance_agent.py` exists. This is a **7th conversational agent** not on any other branch (Ritu's uncommitted working tree has candidate 7th and 8th agents `bd_agent.py` and `marketing_agent.py` — see 3.3.C).
- **Missing files** vs `development`: `.cursor/rules/llm-provider.mdc`, `infra/nginx/README.md`, `infra/nginx/wfd-os.conf` — this branch forked before the nginx and cursor-rules commits landed on development.
- **CLAUDE.md:** older (676 lines vs 688 on development). Missing the standing rules appended later.

All other modules identical to `development` at file-content level (verified via blob hash on `student_api.py`, `consulting_api.py`, `marketing/api.py`, `apollo/client.py` — all match `development` exactly).

#### 3.3.C Branch-unique content

**Committed** (versus all other branches):

- `agents/grant-compliance/` (62 files) — entire FastAPI app + Alembic + QB OAuth.
- `agents/assistant/finance_agent.py`.
- `portal/student/app/internal/finance/` (2-file variant, conflicts with finance-cockpit's 13-file variant).
- 11 unique commits spanning Apr 6–17, including `98999f8 import: grant-compliance-system scaffold from Claude chat session`, `0f6d94c Step 0: integrate grant-compliance scaffold DB into wfd-os Postgres`, `846eed1 Lock in Step 0 near-miss defense + enforce QuickBooks read-only in code`, `50f5c20 Step 1a: real QB sandbox sync + startup guard + defense-model correction`.

**Uncommitted working-tree additions in the main folder** — these would land on this branch if committed as-is. They are substantive:

New files (26 untracked items):
- `agents/finance/` *(entire new module — note: finance on this branch is currently a frontend-only skeleton; this would add the backend)*
- `agents/assistant/bd_agent.py`, `agents/assistant/marketing_agent.py` *(8th and 9th agents)*
- `agents/apollo/hunter_client.py`
- `agents/market-intelligence/bd-pipeline/`
- `portal/student/app/internal/bd/`, `portal/student/app/internal/jessica/` *(new internal cockpits)*
- `portal/student/app/api/`, `portal/student/app/resources/`, `portal/student/app/unsubscribe/`
- `portal/student/components/newsletter-subscribe.tsx`, `portal/student/lib/content.ts`, `portal/student/lib/fetch.ts`
- `CFA_GRANT_CONTEXT.md`, `content/`, `docs/lead-scoring-algorithm.md`, `docs/wfd_os_architecture.md`, `docs/wfd_os_code_reality_phase1.md`, `scripts/create_wiki_pages.py`
- `portal/student/app/coalition/{client,coalition,showcase}-client.tsx`, `portal/student/app/for-employers/for-employers-client.tsx`, `portal/student/app/home-client.tsx`, `portal/student/app/showcase/showcase-client.tsx` *(server-component-wrapper extractions)*

Significant modifications (30 files):
- `CLAUDE.md` +69 lines (standing rule on server-component-wrapper pattern)
- `agents/apollo/client.py` +156 lines (`search_contacts_by_domain/by_name` + fallback)
- `agents/marketing/api.py` +302 lines (lead capture, newsletter subscribe/unsubscribe, issue list/detail)
- `agents/portal/consulting_api.py` +634 lines (BD command center API: priorities, hot-prospects, warm-signals, pipeline CRUD, signals, email drafts approve/reject, Graph API send helpers; Marketing API: performance, gaps, calendar, submit-content, leads-summary)
- `agents/portal/student_api.py` +16 lines
- `portal/student/app/layout.tsx` +30 lines
- Multiple frontend pages being refactored into `page.tsx` (server) + `<route>-client.tsx` (client) split per the new CLAUDE.md rule. Net delta across 30 files: **+1,527 / −2,322** (deletions dominate because client components are being extracted).

**This uncommitted work is not a single logical feature**; it is a multi-session accumulation of BD command center, newsletter/unsubscribe plumbing, Jessica's workbench, new internal cockpits, the server-component-wrapper refactor, and several new architectural docs. If committed, it would roughly double what makes this branch distinctive — shifting the center of gravity from "grant-compliance + finance_agent" to "grant-compliance + BD/marketing/newsletter + Jessica + server-component refactor + architecture docs."

#### 3.3.D Branch-shared content

Most of the tree (agents/assistant/ core, portal top-level pages, career-services, profile, apollo, marketing, grant, graph, llm, market-intelligence, reporting, scoping, college-pipeline) is **blob-identical with `development`**. This branch's disjointness is at the commit-graph level, not the content level — the Vegas bulk imports appear twice with the same final content but different commit ancestries.

Note: because this branch is disjoint from `development`, any cross-branch merge will need `git merge --allow-unrelated-histories` or a deliberate rebase-flatten.

---

### 3.4 `claude/sleepy-wiles-f9fc04` — the migrations lifeboat

#### 3.4.A Branch summary

- **Tip:** `291f7cc` "db(job-board): version migrations 011-013 for recruiting schema" (2026-04-17)
- **+1 commit ahead of development, 0 behind.**
- **335 tracked files** (+3 vs development — exactly the migration files).
- **Characterization:** A preservation branch. Its single commit versions three SQL migration files that were "previously applied to the live wfd_os DB but only existed as untracked files in a sibling worktree" (per the commit message). Migrations 011 and 012 originally came from `claude/dazzling-keller-394d4a`'s untracked scratch work; 013 is new here. **This is the only tracked source-of-truth for DDL already running in local Postgres.**

#### 3.4.B Module inventory

Identical to `development` in every module **except** for three additional migration files in `scripts/`:
- `011-job-board-agent-schema.sql` (183 lines) — creates `v_jobs_active` view, polymorphic `embeddings` table (VECTOR(1024) with HNSW cosine index), `applications` table with approval-status enum + `UNIQUE(student_id, job_id)`.
- `012-fix-embeddings-dimension.sql` (42 lines) — retypes `embeddings.embedding` to VECTOR(1536) for Azure OpenAI `text-embedding-3-small`.
- `013-broaden-scope-and-add-location.sql` — adds `city/state/country/is_remote/latitude/longitude/employment_type` to `jobs_enriched`, backfills from `jobs_raw.raw_data`, drops `is_suppressed` filter from `v_jobs_active`.

No other files added. No code changes outside `scripts/`.

#### 3.4.C Branch-unique content

- The three migration SQL files above. **Not present on any other branch as tracked files.**
- The commit `291f7cc`. **`git branch --all --contains 291f7cc` returns only this branch.**

#### 3.4.D Branch-shared content

Identical to `development` everywhere except `scripts/`.

---

### 3.5 `origin/refactor/staging` — Gary's platform line

#### 3.5.A Branch summary

- **Tip:** `a69fae8` "docs(smoke): flag §10 nginx VM deploy as prod-mutation (run manually)" (2026-04-19)
- **+51 commits ahead of development, 0 behind.** Pushed to origin.
- **474 tracked files** (+144 vs development, −2 removed).
- **Characterization:** The integration branch for the 16-branch `issue-NN` series. Introduces `packages/wfdos-common/`, per-service `pyproject.toml` packaging, a CI workflow, pre-commit hooks, structured phase exit-reports, multi-tenant edge-proxy config, a `laborpulse` workforce-Q&A module, and a full `scripts/smoke/` regression suite. **Does not contain any of Ritu's Phase 2 cockpit work (finance, recruiting, _shared/, job_board, migrations 011+). It is a parallel track focused on platform infrastructure, not product surface area.**

#### 3.5.B Module inventory

Diffs from `development`:

- **All Coalition/Workforce product modules that exist on `development`:** **still present but with content modifications on some files.** `student_api.py` (488 → 508 lines), `consulting_api.py` (974 → 1006 lines), `marketing/api.py` (233 → 231 lines), `apollo/client.py` (256 → 258 lines), `CLAUDE.md` (688 → 710 lines). Likely modifications: routing through the new `wfdos_common` adapter, tier decorators on endpoints, structured error envelopes, structured logging middleware. Not read line-by-line in this recon.
- **Recruiting / placement workbench, Finance, `_shared/`, `agents/job_board/`, `agents/finance/`:** **NOT on this branch.** Gary's line did not integrate Ritu's cockpit work.
- **`agents/grant-compliance/`:** **NOT on this branch.** Gary's line did not integrate the disjoint grant-compliance branch.
- **`agents/llm/`:** **REMOVED.** The llm client has moved to `packages/wfdos-common/wfdos_common/llm/` (with provider subpackages for Anthropic, Azure OpenAI, Gemini).
- **New module — `agents/laborpulse/`:** **built.** 4 files: `__init__.py`, `api.py`, `client.py`, `pyproject.toml`. Workforce-development Q&A endpoint backing a new `/laborpulse` Next.js page. Includes mock mode and 503 handling when JIE is unavailable (per smoke tests under `scripts/smoke/laborpulse/`).
- **New shared-libs package — `packages/wfdos-common/`:** **built.** Own package structure (`wfdos_common/`) with submodules: `agent/` (base ABC), `auth/`, `config/`, `db/`, `errors/`, `llm/` (multi-provider adapter), `logging/`, `models/`, `queries/`, `schema/`, `tenancy/`, `testing/`, `tiers/`. **~25 test files** — the only substantial test suite in the repo.
- **New infrastructure-as-code:** `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, `.secrets.baseline`, `Procfile`, `docker-compose.dev.yml`, `docker/postgres-init/*.sql`.
- **New edge-proxy config:** `infra/edge/nginx/wfdos-platform.conf` (multi-tenant white-label). The old `infra/nginx/wfd-os.conf` is **also still present** — both configs exist simultaneously.
- **Structured docs:** `docs/refactor/` (5 exit reports for phases 2–5 + laborpulse + INDEX + issue-29 migration guide), `docs/ops/credential-rotation.md`, `docs/config/identity-migration.md`, `docs/database/wfdos-schema-inventory.md`, `docs/laborpulse.md`, `docs/public-url-contract.md`, `docs/white-label-config.md`.
- **Per-service `pyproject.toml`** for 10 agents: apollo, assistant, grant, laborpulse, market-intelligence, marketing, portal, profile, reporting, scoping. Supports "issue-27 — per-service packaging." Eliminates `sys.path` hacks.
- **Archived issue tracker snapshots:** `archive/superseded-issues-2026-04-14/` (12 JSON files).

All Youth, all Student-Portal-facing pages, all Consulting frontend pages: still there, blob-identical to development.

#### 3.5.C Branch-unique content

144 files unique to this branch. Highlights:

- `packages/wfdos-common/` entire tree (~50 files including tests).
- `agents/laborpulse/` (4 files).
- `scripts/smoke/` (19 smoke-test runners covering agent, auth, bootstrap, cta, edge, errors, laborpulse, tenancy).
- CI/dev infrastructure: `.github/workflows/ci.yml`, `.pre-commit-config.yaml`, `.secrets.baseline`, `Procfile`, `docker-compose.dev.yml`, `docker/postgres-init/*`.
- 10 per-agent `pyproject.toml` files.
- `infra/edge/nginx/wfdos-platform.conf` (white-label tenancy).
- `docs/refactor/phase-{2,3,4,5}-exit-report.md`, `docs/refactor/laborpulse-exit-report.md`, `docs/refactor/issue-29-migration.md`, `docs/refactor/INDEX.md`.
- `docs/ops/credential-rotation.md`, `docs/config/identity-migration.md`, `docs/database/wfdos-schema-inventory.md`, `docs/laborpulse.md`, `docs/public-url-contract.md`, `docs/white-label-config.md`.
- `archive/superseded-issues-2026-04-14/` (12 JSON artifacts).

51 unique commits with theme-coded history (`feat(llm): ...`, `feat(db): ...`, `feat(auth): ...`, `chore(phase-N): exit gate`, `feat(laborpulse): ...`, `chore(smoke): ...`).

#### 3.5.D Branch-shared content — with content conflicts

Most files reproduce `development`. But **the following files share paths with `development` and `feature/finance-cockpit` / `integrate/grant-compliance-scaffold` but have different content on this branch:**

| Path | dev/finance/sleepy blob | integrate blob | staging blob |
|---|---|---|---|
| `agents/portal/student_api.py` | `c576caea` (488 L) | `c576caea` (488 L) | `8af03617` (508 L) |
| `agents/portal/consulting_api.py` | `7b5dad53` (974 L) | `7b5dad53` (974 L) | `e69f78f6` (1006 L) |
| `agents/marketing/api.py` | `f9949431` (233 L) | `f9949431` (233 L) | `b0ae16bc` (231 L) |
| `agents/apollo/client.py` | `ab6c7d4d` (256 L) | `ab6c7d4d` (256 L) | `06929590` (258 L) |
| `CLAUDE.md` | `ddf05d1f` (688 L) | `e843932005` (676 L) | `46a4afd2` (710 L) |

Plus `llm` is removed entirely and lives under `packages/wfdos-common/`. These files are the hotspots where a merge with `feature/finance-cockpit` or `integrate/grant-compliance-scaffold` will surface refactor vs. feature conflicts.

---

## Part 4 — Cross-Branch Module Matrix (Section E)

Cell values:
- **✅** — built and blob-identical-or-equivalent to the other ✅ cells in the row
- **◼** — built but **content differs** from other ✅ cells in the row (conflict with the reference)
- **◧** — skeleton / partial / different implementation of the same concept
- **—** — not present
- **n/a** — module does not apply

Reference for ✅ vs ◼ is the `development` blob. Where the architecture's module expects code that doesn't exist on `development` (e.g., finance, recruiting), the ✅ is taken from `feature/finance-cockpit` instead.

### Youth component

| Module | development | feature/finance-cockpit | integrate/gc-scaffold | sleepy-wiles | refactor/staging |
|---|---|---|---|---|---|
| Youth marketing page | ✅ | ✅ | ✅ | ✅ | ✅ |
| Youth participant mgmt | — | — | — | — | — |
| Youth curriculum | — | — | — | — | — |
| Youth-family comms | — | — | — | — | — |
| Youth funding | — | — | — | — | — |

### Coalition / Workforce component

| Module | development | feature/finance-cockpit | integrate/gc-scaffold | sleepy-wiles | refactor/staging |
|---|---|---|---|---|---|
| Student profile | ✅ | ✅ | ✅ | ✅ | ◼ (wfdos_common refactor) |
| Resume parsing | ✅ | ✅ | ✅ | ✅ | ✅ |
| Gap analysis | ✅ | ✅ | ✅ | ✅ | ✅ |
| Job matching (embedding) `agents/job_board/` | — | ✅ | — | — | — |
| Job-board schema migrations 011–013 | — | ◼ (011-embeddings-metadata, 42 lines) | — | ◼ (011-job-board-agent-schema + 012 + 013) | — |
| Match narratives generator | — | — | — | — | — |
| Match narratives DB schema | — (table in DB, not a branch artifact) | | | | |
| Talent showcase | ✅ | ✅ | ✅ | ✅ | ✅ |
| College partner portal | ✅ | ✅ | ✅ | ✅ | ✅ |
| Recruiting / placement workbench (Jessica) | — | ✅ | — (Jessica's `internal/jessica/` exists only uncommitted) | — | — |
| Finance backend (`agents/finance/`) | — | ✅ | — (uncommitted in main-folder WIP) | — | — |
| Finance frontend (`internal/finance/`) | — | ✅ (13 files, cockpit-shell) | ◧ (2 files, simpler client) | — | — |
| Cockpit `_shared/` primitives | — | ✅ | — | — | — |
| WJI reporting | ✅ | ✅ | ✅ | ✅ | ✅ |
| Compliance / Quinn (as designed) | — | — | — | — | — |
| `agents/grant-compliance/` (actual code) | — | — | ✅ (62 files, FastAPI + Alembic + QB OAuth) | — | — |
| Upskilling / learning resource | — | — | — | — | — |
| Student-facing portal | ✅ | ✅ | ✅ | ✅ | ✅ |
| Public arrival experience | — | — | — | — | — |

### Consulting component

| Module | development | feature/finance-cockpit | integrate/gc-scaffold | sleepy-wiles | refactor/staging |
|---|---|---|---|---|---|
| Consulting funnel | ✅ | ✅ | ✅ | ✅ | ◼ (consulting_api.py refactor, +32 L) |
| Consulting pipeline / engagement | ✅ (same file as funnel) | ✅ | ✅ | ✅ | ◼ |
| Client portal | ✅ | ✅ | ✅ | ✅ | ✅ |
| BD & marketing (infrastructure) | ✅ (apollo, marketing, newsletter tables) | ✅ | ✅ | ✅ | ◼ (apollo +2 L, marketing −2 L — wfdos_common adapter) |
| BD command center UI | — | — | — (uncommitted in main-folder WIP: `internal/bd/`) | — | — |
| BD command center API | — | — | — (uncommitted in main-folder WIP: +634 L on consulting_api.py) | — | — |
| Newsletter subscribe/unsubscribe | — | — | — (uncommitted in main-folder WIP: +302 L on marketing/api.py) | — | — |
| Apprentice workforce mgmt | — (in wtc) | — | — | — | — |
| Apprentice curriculum | — (in wtc) | — | — | — | — |

### Platform infrastructure (not in the architecture-doc module list, but material)

| Layer | development | feature/finance-cockpit | integrate/gc-scaffold | sleepy-wiles | refactor/staging |
|---|---|---|---|---|---|
| `wfdos_common` shared libs | — | — | — | — | ✅ (`packages/wfdos-common/`) |
| Agent ABC | — | — | — | — | ✅ |
| Magic-link auth | — | — | — | — | ✅ |
| Tier decorators | — | — | — | — | ✅ |
| Multi-tenant edge proxy | — | — | — | — | ✅ (`infra/edge/nginx/wfdos-platform.conf`) |
| Simple nginx proxy | ✅ (`infra/nginx/wfd-os.conf`) | ✅ | — (branch predates it) | ✅ | ✅ (still present alongside new one) |
| `agents/laborpulse/` | — | — | — | — | ✅ |
| CI workflow | — | — | — | — | ✅ |
| Pre-commit hooks | — | — | — | — | ✅ |
| Docker dev | — | — | — | — | ✅ |
| Per-service pyproject.toml | — | — | — | — | ✅ (10 agents) |
| Smoke tests | — (2 scripts in `scripts/`) | same | same | same | ✅ (`scripts/smoke/` — 19 runners) |
| `agents/llm/client.py` | ✅ | ✅ | ✅ | ✅ | — (moved to `packages/wfdos-common/wfdos_common/llm/`) |
| `.github/workflows/` | — | — | — | — | ✅ |

### Docs (current Ritu work — not architecture modules)

| Doc | development | feature | integrate | sleepy-wiles | refactor/staging |
|---|---|---|---|---|---|
| `wfd_os_architecture.md` | — | — | — (in main-folder WIP, untracked) | — | — |
| `wfd_os_code_reality_phase1.md` | — | — | — (in main-folder WIP, untracked) | — | — |
| `wfd_os_code_reality_phase2.md` | — | — | — (was in vibrant-cannon worktree, untracked) | — | — |
| `wfd_os_branch_reality_map.md` (this doc) | — | — | — (written now, main folder untracked) | — | — |
| `CFA_GRANT_CONTEXT.md` | — | — | — (main-folder WIP, untracked) | — | — |
| `docs/lead-scoring-algorithm.md` | — | — | — (main-folder WIP, untracked) | — | — |
| `docs/refactor/phase-{2..5}-exit-report.md` | — | — | — | — | ✅ |

---

## Part 5 — Integration Considerations (Section F)

This section is **informational only**. Ritu decides integration timing
and approach in coordination with Gary.

### 5.1 Known merge conflicts

When two or more of these branches meet, the following surfaces will
collide:

**A. Migration 011 — hard collision.**
Three 011 files, each different:
- `feature/finance-cockpit:scripts/011-embeddings-metadata.sql`
- `claude/sleepy-wiles-f9fc04:scripts/011-job-board-agent-schema.sql`
- (`refactor/staging` does not add an 011)

Resolution: renumber one of them. Sleepy-wiles's set (011 + 012 + 013) is already in the live DB; renumbering those three would require chained renames. The less invasive fix is to renumber feature/finance-cockpit's one 011 to 014.

**B. `portal/student/app/internal/finance/page.tsx` — content conflict.**
Feature/finance-cockpit's 51-line server-component wrapper pointing at `cockpit-shell` vs. integrate/grant-compliance-scaffold's 79-line page using a simpler `finance-client.tsx`. These are two implementations of the same route. One wins — probably feature/finance-cockpit's (it is the richer, deliberately architected cockpit UI), with the integrate version preserved in history if the simpler variant is still wanted for some purpose.

**C. Shared service refactors in `refactor/staging`.**
`refactor/staging` has modified `agents/portal/student_api.py`, `agents/portal/consulting_api.py`, `agents/marketing/api.py`, `agents/apollo/client.py`, and `CLAUDE.md` on top of the `development` baseline (different blob hashes, nontrivial line counts). Meanwhile:
- `feature/finance-cockpit` left those files unchanged vs. `development`. Merging `refactor/staging` first and `feature/finance-cockpit` second is a clean apply (finance-cockpit does not touch those files).
- The **main-folder uncommitted WIP** has added +634 L to `consulting_api.py`, +302 L to `marketing/api.py`, +156 L to `apollo/client.py`, +69 L to `CLAUDE.md`, +16 L to `student_api.py`. **All of those target the same files `refactor/staging` also modified.** This is the biggest conflict hotspot. Landing refactor/staging first means the WIP must be re-applied on top of the refactored versions of those files — a meaningful rewrite, not a clean merge.

**D. `agents/llm/` removal.**
`refactor/staging` removes `agents/llm/` in favor of `packages/wfdos-common/wfdos_common/llm/`. Any other branch that imports from `agents.llm.client` needs to change imports when rebased onto staging. (None of feature/finance-cockpit, integrate/grant-compliance-scaffold, or sleepy-wiles appear to add new `agents/llm/` call sites, but existing sites still reference it.)

**E. `integrate/grant-compliance-scaffold` has disjoint history.**
Any merge requires `--allow-unrelated-histories`. The safer approach is to rebase the 11 unique commits (stripping the re-done initial commit and the near-identical Vegas files) onto `development`, keeping only the 4 substantive commits (`98999f8`, `0f6d94c`, `846eed1`, `50f5c20`, `e5e98f9`, `1a2bec6`) as a clean topical patch series.

**F. Missing-file regression risk on integrate/grant-compliance-scaffold.**
This branch lacks `.cursor/rules/llm-provider.mdc`, `infra/nginx/README.md`, `infra/nginx/wfd-os.conf`. A naive merge direction that preserves "everything from integrate" could accidentally drop those. The fix: always reconcile with development's tree as baseline rather than integrate's.

### 5.2 Modules that exist in different forms

| Concept | Forms | Recommended canonical |
|---|---|---|
| `/internal/finance/page.tsx` | 51-line cockpit-shell wrapper (finance-cockpit) vs. 79-line direct client (integrate) | **finance-cockpit** (richer cockpit alignment) |
| Migration 011 | embeddings-metadata (finance-cockpit) vs. job-board-agent-schema (sleepy-wiles) | **sleepy-wiles's triplet** (already applied to DB); renumber finance-cockpit's |
| `agents/finance/` | Not yet on integrate (uncommitted WIP only) vs. full 10-file module on finance-cockpit | **finance-cockpit's** (mature) |
| `agents/job_board/` underscore vs. `agents/job-board/` hyphen | Underscore wins (finance-cockpit); hyphen was an abandoned scratch name in `dazzling-keller` worktree | **underscore** (already the tracked form) |
| `agents/llm/` vs. `packages/wfdos-common/wfdos_common/llm/` | Current (development) vs. refactored (staging) | **packages version** once refactor lands |
| `infra/nginx/wfd-os.conf` vs. `infra/edge/nginx/wfdos-platform.conf` | Single-tenant simple vs. multi-tenant white-label | TBD by Ritu + Gary; one or both may be kept with role differentiation |
| Grant compliance as "Quinn" (architecture concept) vs. `agents/grant-compliance/` (actual code on integrate) | Designed vs. built | Rename or reposition Quinn relative to the shipping code |
| Finance agent count: 6 (development) → 7 (integrate, +finance_agent) → 9 (integrate WIP, +bd_agent, +marketing_agent) | — | Land the uncommitted additions as one focused commit |

### 5.3 Branches with unique work to preserve before any deletion

- **`claude/sleepy-wiles-f9fc04`** — commit `291f7cc` is the only tracked copy of DDL already in the live DB. Must be cherry-picked or rebased onto `development` (or `feature/finance-cockpit` with renumbering) before deletion.
- **`feature/finance-cockpit`** — 23 unique commits + 64 unique files. The entire Phase 2 cockpit work lives nowhere else. Unpushed.
- **`integrate/grant-compliance-scaffold`** — 11 unique commits + `agents/grant-compliance/` (62 files) + 26 untracked WIP items + 30 uncommitted-modified files in the main folder. Unpushed.
- **`claude/dazzling-keller-394d4a`** — not in scope here; previously established to contain no unique tracked work (its 3 untracked migration files are byte-identical to what sleepy-wiles versioned; only the stub `agents/job-board/` hyphen dir is unique, and it was abandoned in favor of `agents/job_board/` underscore on finance-cockpit).
- **`claude/vibrant-cannon-c4998c`** — contains one untracked doc (`wfd_os_code_reality_phase2.md`) which should be copied to `docs/` in the main folder.

### 5.4 Possible sequencing to minimize conflicts

(Again, illustrative — not a prescription.)

1. **Commit the main-folder WIP** onto `integrate/grant-compliance-scaffold` as one or more topic-scoped commits. This freezes the WIP into version control so it can be rebased and tested. Suggested grouping:
   - Commit 1: "feat(backend-apis): BD command center + newsletter + lead capture" — consulting_api.py +634 L, marketing/api.py +302 L, apollo/client.py +156 L, new `agents/apollo/hunter_client.py`, new `agents/assistant/bd_agent.py` + `marketing_agent.py`, `agents/market-intelligence/bd-pipeline/`, `agents/finance/` (the backend).
   - Commit 2: "feat(frontend): BD cockpit, Jessica workbench, resources, unsubscribe" — new `internal/bd/`, `internal/jessica/`, `resources/`, `unsubscribe/`, `api/`, `components/newsletter-subscribe.tsx`, `lib/content.ts`, `lib/fetch.ts`.
   - Commit 3: "refactor(portal): extract client components per server-wrapper rule" — the 30 page.tsx files split into `<route>-client.tsx` siblings, + CLAUDE.md standing rule.
   - Commit 4: "docs(architecture): add architecture + reality docs" — wfd_os_architecture.md, wfd_os_code_reality_phase1.md, wfd_os_code_reality_phase2.md, wfd_os_branch_reality_map.md, CFA_GRANT_CONTEXT.md, docs/lead-scoring-algorithm.md, scripts/create_wiki_pages.py.
2. **Cherry-pick `claude/sleepy-wiles-f9fc04:291f7cc`** onto `feature/finance-cockpit`. Resolve 011 naming by renumbering `feature/finance-cockpit`'s `011-embeddings-metadata.sql` to `014-embeddings-metadata.sql` so the sleepy 011/012/013 stay tracked as-applied.
3. **Decide on refactor/staging ordering.** Two viable orders:
    - **Stage first, then products.** Land `refactor/staging` → `development` first; then rebase `feature/finance-cockpit` + `integrate/grant-compliance-scaffold` onto the refactored base. Cleanest long-term but forces Ritu/Gary coordination immediately and re-applies the WIP on top of wfdos_common-adapted services.
    - **Products first, then stage.** Land `feature/finance-cockpit` + `integrate/grant-compliance-scaffold` (with rebase-flattened history) onto `development` first; then rebase `refactor/staging` onto the new base. Keeps the product feature work intact; forces Gary to re-apply the refactor on top of the newly-landed code.
4. **Delete preserved worktrees** after cherry-picks land. `claude/dazzling-keller-394d4a` and `claude/vibrant-cannon-c4998c` are safe to delete immediately after preserving the Phase 2 doc from the latter.

---

## Part 6 — What This Document Doesn't Tell You

- **No line-level comparison** of the refactored services on `refactor/staging` (student_api, consulting_api, marketing/api, apollo/client, CLAUDE.md). I confirmed hashes differ but did not read the diffs. If you're deciding merge order, sampling those diffs is the next investigation.
- **No inspection of `packages/wfdos-common/`'s implementation**, only its file tree. The adapter pattern, how `agents/*` consume it, how auth tiers integrate — all unsurveyed here.
- **No test run results.** `refactor/staging` has ~25 package-level tests and 19 smoke runners; I did not execute any.
- **Working-tree WIP inventory** (Section 3.3.C) is based on `git status --porcelain` and an earlier file-by-file diff for the 4 files you asked about; I did not read the 30 modified frontend pages line-by-line.
- **No cross-check against Gary's intent.** The `refactor/staging` sequence is what the commit graph shows; conversations with Gary may reveal goals not visible in git.

---

## Part 7 — Summary Table (every module × every branch)

One consolidated grid for the "at a glance" view the prompt asked for:

| | dev | finance-cockpit | gc-scaffold | sleepy-wiles | staging |
|---|---|---|---|---|---|
| Youth marketing | ✅ | ✅ | ✅ | ✅ | ✅ |
| Student profile | ✅ | ✅ | ✅ | ✅ | ◼ |
| Resume parsing | ✅ | ✅ | ✅ | ✅ | ✅ |
| Gap analysis | ✅ | ✅ | ✅ | ✅ | ✅ |
| Job matching (job_board) | — | ✅ | — | — | — |
| Job-board migrations (011–013) | — | ◼ (011 only) | — | ◼ (011+012+013) | — |
| Match narratives generator | — | — | — | — | — |
| Talent showcase | ✅ | ✅ | ✅ | ✅ | ✅ |
| College partner portal | ✅ | ✅ | ✅ | ✅ | ✅ |
| Recruiting workbench (Jessica) | — | ✅ | ◧ WIP | — | — |
| Finance backend | — | ✅ | ◧ WIP | — | — |
| Finance frontend | — | ✅ (rich) | ◧ (simple) | — | — |
| Cockpit `_shared/` | — | ✅ | — | — | — |
| WJI reporting | ✅ | ✅ | ✅ | ✅ | ✅ |
| Compliance / Quinn | designed | designed | ◧ (grant-compliance app) | designed | designed |
| Upskilling | designed | designed | designed | designed | designed |
| Student-facing portal | ✅ | ✅ | ✅ | ✅ | ✅ |
| Public arrival | designed | designed | designed | designed | designed |
| Consulting funnel | ✅ | ✅ | ✅ | ✅ | ◼ |
| Consulting pipeline | ✅ | ✅ | ✅ | ✅ | ◼ |
| Client portal | ✅ | ✅ | ✅ | ✅ | ✅ |
| BD/marketing infrastructure | ✅ | ✅ | ✅ | ✅ | ◼ |
| BD command center (UI + API) | — | — | WIP | — | — |
| Newsletter subscribe | — | — | WIP | — | — |
| Apprentice workforce (wtc) | — | — | — | — | — |
| Apprentice curriculum (wtc) | — | — | — | — | — |
| wfdos_common shared libs | — | — | — | — | ✅ |
| Agent ABC | — | — | — | — | ✅ |
| Magic-link auth | — | — | — | — | ✅ |
| Tier decorators | — | — | — | — | ✅ |
| Multi-tenant edge proxy | — | — | — | — | ✅ |
| laborpulse module | — | — | — | — | ✅ |
| CI / pre-commit / Docker | — | — | — | — | ✅ |
| Per-service pyproject | — | — | — | — | ✅ |
| Smoke tests | — | — | — | — | ✅ |

**Legend:** ✅ built & matches baseline · ◼ built but content-differs from baseline · ◧ skeleton/partial/alt-implementation · WIP uncommitted working-tree · — not present · designed in docs only.

---

*End of branch reality map. Output path: `docs/wfd_os_branch_reality_map.md` in the main wfd-os folder.*
