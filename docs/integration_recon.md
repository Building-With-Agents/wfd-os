# Integration Recon — feature/finance-cockpit vs origin/development

*Date: 2026-04-21 · Read-only analysis · No merge attempted · Uncommitted working file*

## TL;DR

**Textual overlap is tiny.** Only 3 files modified on both sides:
- `.gitignore` — definite conflict, trivial to resolve (~2 min)
- `agents/assistant/api.py` — definite conflict, non-trivial (10–15 min — my side added 3 agents, Gary's side rewrote imports + added middleware/error handlers)
- `portal/student/next.config.mjs` — **auto-merges clean textually**, but has **one hidden semantic conflict** (port 8012 collision; see §5.1)

**Architectural tension is the real story.** Gary's 39 commits were a comprehensive platform refactor (wfdos_common shared libs, tenant middleware, 5-portal migration, canonical schema, auth, CI, edge proxy) with a specific tenancy model. My 33 commits delivered feature work (finance cockpit Phase 2, Phase A multi-tenant seeding, Phase B matching pipeline) with a different tenancy model and patterns that bypass the new shared-lib layer. The branches are **compatible at the file level but divergent at the architecture level.** See §5 for details.

---

## 1. Merge-base facts

| | commit | |
|---|---|---|
| merge base | `571d5bd` | "infra(nginx): snapshot production reverse-proxy config (#36)" — 2026-04-15 |
| feature/finance-cockpit tip | `3208298` | Phase B verification (Task 7) |
| origin/development tip | `6904b60` | Gary's CI fix: `env_prefix="PG_"` |
| my side | 33 commits | |
| Gary's side | 39 commits | |
| files modified, my side | 82 | |
| files modified, Gary's side | 200 | |
| files modified, both sides (intersection) | **3** | (see §3) |

---

## 2. Summary of what each side did

### My 33 commits (in theme order)

- **Finance cockpit Phase 1A–2E (pre-Phase A, ~23 commits)**: `agents/finance/`, `portal/student/app/internal/finance/`, `portal/student/app/internal/recruiting/`, `portal/student/app/internal/_shared/`, `agents/job_board/` (api.py, data_source.py), job_board migration 011.
- **Phase A (Cohort 1 data setup, 3 commits)**: `scripts/014-tenants-seed.sql` (tenants table + tenant_id on 5 tables), `scripts/phase_a_fetch_sharepoint_resumes.py`, `scripts/phase_a_parse_cohort1_resumes.py`, `scripts/phase_a_ingest_elpaso_jobs.py`, `.gitignore` additions.
- **Phase B (matching, 6 commits)**: `scripts/016-cohort-matches.sql`, `scripts/phase_b_task[1–6]_*.py`, `docs/cohort1_placement_report.md`. Added `agents/assistant/api.py` registry entries for bd_agent/marketing_agent/finance_agent (pre-dates my Phase A work — part of Phase 2G/integrate work that was on this branch already).

### Gary's 39 commits (in theme order)

- **wfdos_common scaffold + migration (issues #16–#31)**: created `packages/wfdos-common/` with config, models, db engine + middleware + shared queries, llm adapter, logging, testing fixtures, auth (magic-link + tier decorators), error envelopes, agent ABC, white-label, edge proxy, CTA URLs.
- **Phase exit gates (4)**: reports + smoke plans across phases 2–5.
- **Portal migration (#22c)**: migrated 5 services (college, consulting, showcase, student, wji APIs) to `wfdos_common.db` engine factory + shared query helpers.
- **Canonical schema (#22b)**: added `docker/postgres-init/10-schema.sql` — a fresh-install canonical schema with `tenant_id TEXT` columns (string-keyed tenancy).
- **laborpulse module**: new FastAPI service on **port 8012** (workforce-development Q&A backed by JIE). See §5.1 for port collision.
- **CI + plumbing fixes (Apr 20)**: pytest imports, `PG_` env_prefix, port 3000 Procfile pin, `/api/laborpulse` + `/api/student` rewrites.
- **Auth wiring**: SessionMiddleware + auth router installed on consulting/student/assistant APIs; magic-link token URL encoding; `/auth/*` proxy through Next.js.

---

## 3. Textual conflicts — the 3 intersecting files

### 3.1 `.gitignore` — **Definite conflict (trivial)**

- **My side**: appends 12 lines — `agents/finance/design/fixtures/`, `data/cohort1_resumes/`, `data/cohort1_ingestion_digest.json`, `data/cohort1_jobs_raw_cache/`, `data/cohort1_jobs_ingestion_digest.json`, and comments.
- **Gary's side**: appends 1 line — `.coverage` (for the new pytest setup).
- **Region**: both append to the same trailing region of the file.
- **Resolution**: keep both (concat). No semantic conflict. ~2 minutes.

### 3.2 `agents/assistant/api.py` — **Definite conflict (non-trivial)**

- **My side (1 commit, `18381da` — "Add /internal/finance portal page + finance_agent")**: added 3 imports (`bd_agent`, `marketing_agent`, `finance_agent`) and 3 `_REGISTERED_AGENTS` entries. Net: +6 lines, no other structural changes.
- **Gary's side (3 commits: `5ce026b` `feat(auth): install SessionMiddleware`, `46b186c` `[#29] structured error envelope`, `e73531c` `[#27] per-service pyproject`)**: removed `sys.path.insert` hacks (per #27), replaced `HTTPException` with `ValidationFailure` from `wfdos_common.errors`, added `RequestContextMiddleware` + `SessionMiddleware` + `install_error_handlers()`, added `allow_credentials=True` to CORS.
- **Conflict regions**:
  - **Imports block** (lines ~10–42 merge-base). Gary deleted the `_REPO_ROOT` / `sys.path.insert` stanza AND added `wfdos_common.*` imports. My side added 3 agent imports after the existing agent imports. These regions overlap because both touch the same import block.
  - **Agent registry block** (lines ~97–110 merge-base). I added 3 lines; Gary didn't modify the registry block but his preceding changes shift line numbers — git sees the edited region as adjacent. Probably still resolves cleanly with -X patience but textually in conflict.
  - **FastAPI app construction block** (lines ~39–48). I didn't touch; Gary rewrote entirely. Not a conflict on my side, just a rewrite on his.
- **Assessment**: Both sides' changes are legitimate and complementary — my 3 new agents need to exist, and Gary's middleware/error-handler stack needs to exist. A clean resolve is: use Gary's rewritten framework (imports, middleware, error handlers) + re-add my 3 agent imports + my 3 registry entries on top. ~10–15 minutes of careful editing.

### 3.3 `portal/student/next.config.mjs` — **Auto-merges clean (but has a semantic conflict — see §5.1)**

- **My side**: added `turbopack: { root: ... }` for Turbopack workspace root pin, fixed `/api/consulting` destination port `8006 → 8003`, added rewrites for `/api/finance/:path*` → `:8013`, `/api/recruiting/:path*` → `:8012`, `/api/grant-compliance/:path*` → `:8000`.
- **Gary's side**: added `/auth/:path*` → `:8003`, `/api/laborpulse/:path*` → `:8012`, `/api/student/:path*` → `:8001`.
- **Textual result**: git's recursive merge produces a valid combined `next.config.mjs` with all rewrites. `git merge-tree` confirms no CONFLICT marker.
- **Hidden semantic problem**: my `/api/recruiting/*` and Gary's `/api/laborpulse/*` both point at **port 8012**. In the merged config, both rewrites are present and the runtime will route correctly based on URL prefix — but **both services can't actually be running on :8012 simultaneously.** See §5.1 for the port collision.

---

## 4. Theme grouping

### Theme A — Authentication / session middleware (Gary-only)

- Gary's side: `SessionMiddleware`, magic-link auth, `@public`/`@read_only`/`@llm_gated` tier decorators, `/auth/*` rewrite in Next.js, workforce-development role, session cookies.
- My side: nothing. All my services are auth-free (Phase B scripts are offline batch runs).
- **Conflict surface**: only `agents/assistant/api.py` (added middleware mentioned in §3.2). My finance cockpit API (`cockpit_api.py`) has no auth; if Gary's tier-decorator pattern becomes mandatory, this needs retrofitting post-merge. Not a merge-time conflict.

### Theme B — Database engine / `wfdos_common.db` (Gary migrated 5 services)

- Gary's side: `wfdos_common.db.engine.get_engine(tenant_id)`, `session_scope()`, `TenantResolver` middleware, shared queries (`get_student_profile`, `get_student_skills`, `get_student_skill_count`). Migrated 5 portal services (college, consulting, showcase, student, wji APIs).
- My side: I touched **zero** of those 5 services. My Phase B scripts use direct `psycopg2.connect(**PG_CONFIG)` throughout.
- **Conflict surface**: none at file level. But my Phase B scripts bypass `wfdos_common.db` — they open their own connections, don't use the tenant-resolver middleware, and don't use the shared query helpers. Post-merge, my scripts would continue to work (they're batch tooling, not API endpoints), but they'd be "out of pattern." See §5.4.

### Theme C — LLM client (Gary moved it to packages/)

- Gary's side: removed `agents/llm/` entirely; added `packages/wfdos-common/wfdos_common/llm/{adapter.py, base.py, providers/}`.
- My side: I don't import `agents.llm` anywhere. My Phase B scripts call Azure OpenAI directly via `requests` (`backfill_embeddings.embed_text`, `match_narrative._call_chat_json`, my own `llm_extract_skills`). Grep confirms zero `from agents.llm` / `import agents.llm` in my scripts.
- **Conflict surface**: none. My scripts are unaffected by the removal.

### Theme D — Database schema / migrations

- Gary's side: `docker/postgres-init/10-schema.sql` — NEW file, **fresh-install canonical schema.** Not an ALTER-based migration; it's a `CREATE TABLE IF NOT EXISTS` bootstrap for docker-compose local-dev databases.
- My side: `scripts/014-tenants-seed.sql` (ALTER-based migration — adds `tenants` table + `tenant_id UUID` columns to 5 existing tables), `scripts/016-cohort-matches.sql` (CREATE `cohort_matches` table).
- **Conflict surface**: none at file level (different paths, different purposes). But **content-level divergence is major** — see §5.2.

### Theme E — `CLAUDE.md`

- **My side**: zero modifications (confirmed; not in intersection).
- **Gary's side**: zero modifications (confirmed; not in intersection).
- **No conflict.**

### Theme F — Portal API services

- My side: added new services in new locations (`agents/finance/cockpit_api.py`, `agents/job_board/api.py`, `agents/job_board/data_source.py`, my uncommitted `agents/job_board/match_narrative.py`). **Did not modify any of the 5 existing portal APIs.**
- Gary's side: modified all 5 existing portal APIs (for db engine migration, logging, auth middleware). Added `agents/laborpulse/` (new service).
- **Conflict surface**: none at file level. But runtime port collision — see §5.1.

### Theme G — Frontend / Next.js portal routes

- My side: added `turbopack.root` pin, fixed a wrong port, added 3 API rewrites (`/api/finance`, `/api/recruiting`, `/api/grant-compliance`).
- Gary's side: added 3 API rewrites (`/auth`, `/api/laborpulse`, `/api/student`). Next.js forced to port 3000 via Procfile `--port`.
- **Conflict surface**: textual auto-merge is clean (§3.3). Port 8012 collides (§5.1). See §3.3 above.

---

## 5. Architectural / logical conflicts — the real story

### 5.1 Port 8012 collision (runtime conflict)

- My `agents/job_board/api.py` binds to `uvicorn.run(app, host="0.0.0.0", port=8012)` (Phase 2E recruiting API).
- Gary's `agents/laborpulse/api.py` binds to port 8012 per its own docstring: *"LaborPulse — FastAPI service (port 8012)"* and the `/api/laborpulse/:path*` rewrite in next.config.mjs points at 8012.
- **Both services cannot run simultaneously on 8012.** One must move. Strictly a runtime conflict, not a source-tree one. The next.config.mjs file will textually accept both rewrites (§3.3), but the process manager will hit an "address already in use" error.
- **Resolution options**: (a) move laborpulse to a free port (8015 or 8014) and update next.config.mjs + Procfile + laborpulse smoke-test scripts; (b) move job_board to a different port (probably 8014) and update next.config.mjs + `workday-client.tsx` references; (c) consolidate into one multiplexed service (out of scope for merge).

### 5.2 Tenancy model divergence — **the biggest architectural tension**

My Phase A migration 014 and Gary's `wfdos_common` tenancy use **fundamentally different tenant models:**

| | My tenant model | Gary's tenant model |
|---|---|---|
| Identifier type | `UUID` (FK to `tenants.id`) | `TEXT` (e.g., `"waifinder-flagship"`) |
| Backing table | `tenants(id UUID PK, code TEXT UNIQUE, name TEXT)` with CFA/WSB seeded | **No `tenants` table** — strings are ambient identifiers |
| Source of tenant_id at runtime | Application supplies WSB UUID explicitly in every query | Middleware resolves from `Host` header or `X-Tenant-Id` → sets `request.state.tenant_id` |
| Columns added | `tenant_id UUID REFERENCES tenants(id) NOT NULL` on students / jobs_enriched / applications / gap_analyses / match_narratives | `tenant_id TEXT` nullable on audit_log, `tenant_id TEXT NOT NULL` on qa_feedback (new table) |
| Foreign-key enforcement | Yes | No — just a string label |

**Implication**: if we adopt Gary's model, my `tenants` table and all UUID FKs become decoration; all queries would key off `request.state.tenant_id` strings. If we keep mine, Gary's middleware needs to resolve the string to a UUID via a lookup through the `tenants` table before setting request state. **Both are valid choices; they can't both be the source of truth.**

**Possible bridge**: keep my `tenants` table, have Gary's `TenantResolver` middleware resolve the Host header → `tenants.code` → `tenants.id` UUID, and set `request.state.tenant_id` to the UUID string. All existing Phase A/B WSB data and all FK constraints remain valid. Gary's canonical schema would need updating to match (add `tenants` table; change `tenant_id TEXT` columns to `tenant_id UUID REFERENCES tenants(id)`). Requires a conversation with Gary.

### 5.3 Canonical schema (`10-schema.sql`) massively diverges from the live DB

Gary's `docker/postgres-init/10-schema.sql` is a fresh-install bootstrap for local docker-compose DBs. **It reflects a cleaner, future-looking schema — not the current live schema.** Key divergences vs the live DB (which my migrations 014/016 have further evolved):

| Table | Live DB (my migrations applied) | Gary's canonical schema |
|---|---|---|
| `tenants` | **exists** (UUID PK, code TEXT, CFA+WSB seeded) | **missing** |
| `students.id` | UUID | Not defined — but `gap_analyses.student_id BIGINT NOT NULL -- FK: students.id` implies **`students.id BIGINT`** |
| `students.tenant_id` | UUID NOT NULL (from my 014) | — (not defined yet) |
| `gap_analyses.id` | UUID | `BIGSERIAL` |
| `gap_analyses.tenant_id` | UUID NOT NULL (from my 014) | missing |
| `gap_analyses.missing_skills` | `text[]` ARRAY | `JSONB` |
| `match_narratives` | exists (from Phase 2G commit on my branch) | **missing** |
| `cohort_matches` | exists (from my 016) | **missing** |
| `embeddings` (pgvector, from sleepy-wiles 011) | exists | **missing** |
| `jobs_enriched` / `jobs_raw` | exist | **missing** |

Gary labeled this migration "**permissive pass 1**". My reading: it's an aspirational baseline for a future-clean local-dev DB and **not intended to replace the live DB immediately.** When docker-compose spins up a fresh dev DB, it uses Gary's schema. When the live DB runs, it's evolved via numbered SQL migrations in `scripts/NNN-*.sql` (the `001-create-schema.sql` plus `014`, `016`, and the sleepy-wiles 011/012/013 that were applied out-of-tree).

**Implication**: no merge-time conflict. But **two sources of schema truth now exist** — live-DB-via-migrations and canonical-via-docker-init. They differ on PK types, tenancy model, and which tables exist. The integration conversation needs to pick one as authoritative going forward.

### 5.4 My Phase B scripts bypass `wfdos_common.db`

Gary's #22c migrated 5 portal services to use `get_engine(tenant_id)` + `session_scope()` + shared query helpers (`get_student_profile`, `get_student_skills`, `get_student_skill_count`). My Phase B scripts (`phase_b_task[1–6]_*.py`) use raw `psycopg2.connect(**PG_CONFIG)` throughout — they don't participate in the new pattern.

This isn't a textual conflict and isn't a runtime issue (scripts are batch tooling, not API endpoints). It's a **pattern-consistency debt**: post-merge, the codebase will have two DB access patterns. The scripts could be migrated to the new pattern as a foundation-hardening pass, but it's not required for the merge to succeed.

### 5.5 My `agents/assistant/api.py` additions (3 new agents) predate Phase A/B

The 3 new agents I registered (`bd_agent`, `marketing_agent`, `finance_agent`) came from commit `18381da` which predates Phase A and is part of Ritu's Phase 2G integration work. Files `agents/assistant/bd_agent.py`, `marketing_agent.py`, `finance_agent.py` are committed as new files on my branch; Gary's branch has none of them. **No file-level conflict** (Gary didn't touch those files), but the registry additions need to land on top of Gary's rewritten `api.py` (see §3.2).

Note: `finance_agent.py` on my branch is committed; on the **main folder's uncommitted WIP** there's a second `finance_agent.py` from the `integrate/grant-compliance-scaffold` branch. Check they are the same content before merging, or the integration branch will shadow.

---

## 6. Integration options assessment

### Option A — Rebase `feature/finance-cockpit` onto `origin/development`

**How**: `git rebase origin/development` from feature/finance-cockpit; resolve conflicts per-commit as rebase walks my 33 commits.

- **Conflicts I'd actually resolve**: 2 textual (`.gitignore`, `agents/assistant/api.py`) + 1 runtime (port 8012) + 1 architectural (pick tenancy model).
- **Rebase granularity**: 33 commits × ~2 files-touched-on-average = potentially 33 resolve points. Most are trivial (each commit only touches small regions); the hotspots are the 2 conflict files and any commits that touch `agents/assistant/api.py` (just 1 in my case).
- **Time estimate**: 2–4 hours, most of it spent on tenancy-model decision and the `agents/assistant/api.py` editing.
- **Risk**: medium. Rebase preserves my commit history neatly; the architectural decisions (tenant model, port 8012) must be settled once; then the mechanical resolves are quick.
- **Clean-history win**: feature/finance-cockpit becomes a linear add on top of Gary's new base.

### Option B — Merge `origin/development` into `feature/finance-cockpit`

**How**: `git merge origin/development` from feature/finance-cockpit.

- **Conflicts to resolve**: 2 textual + 1 runtime + 1 architectural — exactly the same set as Option A, but all at once in a single merge commit.
- **Time estimate**: 1.5–3 hours (slightly faster than rebase because no per-commit walking).
- **Risk**: medium. A merge commit preserves both histories visibly; any resolution mistake is encoded in the single merge commit.
- **History cost**: merge commit clutters history but keeps both topic branches' commits traceable.

### Option C — Start fresh from `origin/development`; bring my work over selectively

**How**: `git checkout -b feature/finance-cockpit-v2 origin/development`; cherry-pick or re-apply logical chunks.

- **Conflicts to resolve**: same 2 textual + 1 runtime + 1 architectural — but spread across smaller bring-over chunks.
- **Time estimate**: 4–8 hours. Higher because it's more code movement, but each chunk is smaller and each rollback is cheaper.
- **Risk**: low per-chunk (you test each bring-over), but higher cumulative risk of leaving something behind.
- **Why consider it**: if you want to also migrate my Phase B scripts to use `wfdos_common.db` patterns during the bring-over, or if you want to align my tenant model to Gary's string-identifier model during the rewrite. Makes non-trivial architectural conversion explicit rather than bolted on during merge.

### Rough comparison table

| | Option A: rebase | Option B: merge | Option C: selective bring-over |
|---|---|---|---|
| Resolve surface | 2 textual + architectural decisions | 2 textual + architectural decisions | 2 textual + architectural conversion per chunk |
| Time | 2–4 hr | 1.5–3 hr | 4–8 hr |
| Risk (could break something unnoticed) | Medium | Medium | Low (per chunk) but higher cumulative-omit risk |
| History preservation | Clean linear on top of dev | Merge commit with both histories | Original history lost; new history per chunk |
| Good if… | You want clean history and plan to land the whole feature-cockpit as-is | You want fastest integration and don't mind the merge commit | You want to re-pattern the Phase B scripts to `wfdos_common.db` during the move |

---

## 7. Talking points for the conversation with Gary

A concrete agenda, in priority order:

1. **Tenancy model**: UUID-FK (mine) vs string-identifier (Gary's). Which is the source of truth going forward, and how does the other side adapt?
2. **Port 8012 collision**: laborpulse vs job_board. Pick which one moves and to what port. (next.config.mjs, Procfile, smoke scripts all need to follow.)
3. **Canonical schema (docker/postgres-init/10-schema.sql)** vs live-DB migrations: which is authoritative? Does Gary's canonical schema need to be extended with tenants + the Phase 2 embedding/matching/narrative tables, or do we keep docker-init as "aspirational" and the live DB as truth?
4. **`agents/assistant/api.py`**: confirm the resolution plan (Gary's framework + my 3 agent registrations on top) is what both sides want.
5. **Phase B scripts vs `wfdos_common.db`**: OK to leave my scripts on raw psycopg2 as batch tooling, or is Gary expecting everything to use the new engine factory?
6. **Integration mechanic**: rebase (Option A), merge (Option B), or selective bring-over (Option C)?

---

## 8. What this recon didn't check

- **Line-level conflicts within `agents/assistant/api.py`** beyond the per-commit stats. I cited approximate regions; git's patience or recursive strategy may widen or narrow them slightly. A dry-run `git merge --no-commit` would be the definitive check (you asked me not to attempt merges — respected).
- **Runtime behavior post-merge.** I flagged the port 8012 collision and the tenancy model tension, but there may be subtler runtime behaviors (request-state interactions, middleware ordering, env-var shadowing from Gary's `PG_` prefix fix on `PgSettings`) that only show up on boot.
- **Test coverage alignment.** Gary added `packages/wfdos-common/tests/*` (~25 test files) and `scripts/smoke/` (19 files). My Phase B work has no test files. Post-merge, Gary's CI will run against the merged tree; any imports my code pulls in that break his tests would surface there.
- **The `integrate/grant-compliance-scaffold` disjoint branch** is still separate — this recon is feature/finance-cockpit ↔ origin/development only. That branch (plus its ~50-file uncommitted WIP in the main folder) remains a separate integration problem.

---

## 9. Appendix — Commands used to produce this recon

```
git fetch --all --prune
git merge-base feature/finance-cockpit origin/development
   # 571d5bd

git diff --name-only 571d5bd..feature/finance-cockpit  # 82 files
git diff --name-only 571d5bd..origin/development        # 200 files
comm -12 <(sort …) <(sort …)                            # 3 files

git merge-tree --write-tree feature/finance-cockpit origin/development
   # tree: bdbf277; 2 CONFLICT lines (.gitignore, agents/assistant/api.py)
   # 1 auto-merged line (next.config.mjs)

git log --oneline 571d5bd..origin/development -- agents/assistant/api.py
   # 3 commits: 5ce026b, 46b186c, e73531c

git show origin/development:docker/postgres-init/10-schema.sql  # canonical schema inspection
git show origin/development:packages/wfdos-common/wfdos_common/db/__init__.py  # tenancy model inspection
```

---

*End of recon. No branches modified. No merge attempted. Integration decisions deferred to the Ritu + Gary conversation.*
