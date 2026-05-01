# Rewrite Proposals — Phase A/B scripts onto Gary's wfdos_common foundation

*Date: 2026-04-21 · Read-only analysis · No code modified · Uncommitted working file*

## TL;DR

**Most of my code needs light ADAPT, not heavy REPLACE.** Of 11 files in scope (scripts/015 Ritu listed doesn't exist on my branch — I never created it):

- **2 migrations KEEP AS-IS** (014 tenants, 016 cohort_matches) — they're the product source of truth and Gary's canonical schema doesn't have these tables. See §Arch Decision 1 before acting.
- **8 Python scripts ADAPT** — mostly swap `os.getenv()` → `settings.*`, `psycopg2.connect(**PG_CONFIG)` stays (the `PG_CONFIG` compat shim in `wfdos_common.config` means no code change), add structured logging, maybe swap the LLM-call helpers onto `wfdos_common.llm.complete` where it fits (extraction + narratives; not embeddings).
- **1 Python script DELETE candidate** — `phase_a_fetch_sharepoint_resumes.py` could be rewritten onto `wfdos_common.graph.sharepoint` (MIGRATED in #17), but the existing helpers don't cover "download by item id"; may need a small helper added to wfdos_common.graph instead of deleting mine.

**One biggest decision looming over all of this:** tenant model. Mine is UUID-FK via a `tenants` table; Gary's is string-ID via `Host`/`X-Tenant-Id` middleware with no backing table. Both are valid; can't both be source of truth. Picking determines whether my migration 014 survives, whether my Phase B scripts keep their explicit `WHERE tenant_id = WSB UUID` filters, and whether Gary's `TenantResolver` middleware needs to hit a lookup table. See §Arch Decision 1.

**Total estimated effort if decisions settled: ~12–18 hours** for the full rewrite, **not including architectural-decision discussions** which are the bottleneck.

---

## §1. Gary's foundation — what I found

I read the public API surface of `packages/wfdos-common/` on `origin/development`. Below is the minimum I needed to understand to propose rewrites. This is my reading, not Gary's spec — if any of it's wrong, the proposals need adjusting.

### §1.1 `wfdos_common.db` — tenant-aware SQLAlchemy engine factory

**Public entry points:**
- `get_engine(tenant_id, *, read_only=False)` — cached engine per (tenant, mode).
- `session_scope(tenant_id, read_only=False)` — context manager (preferred for scripts).
- `db_session(request)` — FastAPI dependency that reads `request.state.tenant_id`.
- `TenantResolver` — ASGI middleware that pins `request.state.tenant_id` from `X-Tenant-Id` or `Host`.
- `get_student_profile(session, student_id)`, `get_student_skills(session, student_id)`, `get_student_skill_count(session, student_id)` — shared query helpers. Each accepts either a SQLAlchemy Session OR a raw psycopg2 connection (backward-compat bridge).

**Tenant model (important):** tenant_ids are **strings** (e.g. `"waifinder-flagship"`, `"wsb-elpaso-cohort1"`). **No `tenants` table in Gary's model** — strings are ambient identifiers resolved from request metadata. `settings.tenancy.default_tenant_id` provides a fallback.

**`wfdos_common.config.PG_CONFIG`** is a lazy-filled dict matching the old `scripts/pgconfig.py` shape. **`psycopg2.connect(**PG_CONFIG)` still works unchanged** — the shim handles the rewrite transparently. My scripts can switch the import line without touching connection code.

### §1.2 `wfdos_common.llm` — provider-agnostic completion adapter

**Public entry point:**
```python
from wfdos_common.llm import complete

text = complete(
    messages=[...],
    tier="default",        # or "synthesis"
    system=..., max_tokens=..., temperature=...,
)
```

- `tier="default"` → `chat-gpt41mini` (per `settings.llm.default_tier_model`).
- `tier="synthesis"` → `chat-gpt41` (per `settings.llm.synthesis_tier_model`).
- Fallback chain: configured primary → Anthropic → Gemini.
- Graceful degradation if primary provider has no credentials.

**Coverage gap**: `wfdos_common.llm` is **completion only**. No embeddings API, no PDF `inline_data`, no tool-calling (deferred to #26 Agent ABC). My code uses:
- Azure OpenAI embeddings (`embeddings-te3small` via `backfill_embeddings.embed_text`) — **no wfdos_common equivalent**. Stay on raw `requests`.
- Gemini PDF inline_data for resume parsing — **no wfdos_common equivalent**. Stay on `google.generativeai` SDK directly.
- Azure OpenAI chat completion for skill extraction + narrative generation — **wfdos_common.llm.complete fits here**. Swap.

### §1.3 `wfdos_common.auth` — magic-link + role-based access

- Magic-link issuance/verification via `issue_magic_link` / `verify_magic_link`.
- Session cookies via `issue_session` / `verify_session`.
- `require_role("staff", "admin")` FastAPI dependency.
- **Tier decorators:** `@public`, `@read_only(roles=...)`, `@llm_gated(roles=...)`.
  - `@read_only` uses the shared read-only engine (fails write attempts fast).
  - `@llm_gated` auto-returns 503 if LLM provider has no credentials.

**Relevance to my code:** my 11 files are **CLI scripts, not FastAPI endpoints**. The tier decorators don't apply — they're route decorators. My scripts run with full DB write access and invoke paid APIs directly (that's the nature of batch ingestion / analysis jobs). No auth middleware to wire.

### §1.4 `wfdos_common.config` — Pydantic settings singleton

```python
from wfdos_common.config import settings

settings.pg.host           # replaces os.getenv("PG_HOST")
settings.pg.user, .password, .database, .port
settings.azure_openai.endpoint   # replaces os.getenv("AZURE_OPENAI_ENDPOINT")
settings.azure_openai.key
settings.llm.provider      # "azure_openai" by default
settings.llm.default_tier_model  # "chat-gpt41mini"
settings.llm.synthesis_tier_model  # "chat-gpt41"
settings.tenancy.default_tenant_id  # "waifinder-flagship"
settings.auth.secret_key, .cookie_name, .session_ttl_seconds
settings.azure.tenant_id, .client_id, .client_secret  # AAD, not OpenAI
```

Lazy-loaded. Reads `.env` via `find_dotenv` (walks up from CWD). Tests monkeypatch env before first access.

**Settings I'd want that I couldn't find:**
- `RAPIDAPI_KEY` (JSearch). No `ApolloSettings` has a RapidAPI field on inspection. My Phase A JSearch script would stay on `os.getenv("RAPIDAPI_KEY")` or a new setting gets added.
- `GEMINI_API_KEY` for PDF resume parsing. `LlmSettings` has provider credentials for the adapter, but Gemini is used OUTSIDE the adapter (for PDF inline_data). Stay on `os.getenv("GEMINI_API_KEY")`.
- Graph API credentials — `settings.graph.*` exists (saw `GraphSettings`). Good for my SharePoint fetch script.
- SharePoint site IDs — `settings.sharepoint.*` likely exists. Worth using.

### §1.5 `wfdos_common.models` — Pydantic domain models

`wfdos_common.models.domain` defines `StudentProfile`, `EmployerProfile`, `CandidateShowcase`, `Skill`, `Education`, `GapAnalysis` as Pydantic `BaseModel`s.

**Significant mismatch:** `StudentProfile.id: int` — uses INT PK, consistent with Gary's canonical schema (`BIGSERIAL`). The **live DB has `students.id: UUID`** (from the Vegas-era migration). So if my scripts tried to `StudentProfile.model_validate(row)` where `row["id"]` is a UUID, it'd fail.

**Conclusion:** the models are aspirational, aligned with the canonical schema — not currently usable against the live DB. My scripts shouldn't try to adopt them yet. Flag for §Arch Decision 3.

### §1.6 `wfdos_common.logging` — structured JSON logging + ContextVars

```python
from wfdos_common.logging import configure, get_logger

configure(service_name="phase-b-task1")  # once per script
log = get_logger(__name__)
log.info("task.started", wsb_tenant_uuid=wsb)
```

ContextVars auto-attach `tenant_id`, `user_id`, `request_id` to every log line. `RequestContextMiddleware` hooks request lifecycle (API services). For CLI scripts, Gary provides `bind_context(tenant_id=...)` helpers (described in module docstring; I didn't read the source deeply).

**Relevance to my scripts:** currently I use `print()`. Swapping to structured logging is straightforward `ADAPT` — mostly cosmetic, but gives consistent JSON output that can be piped into Gary's observability stack later.

### §1.7 `wfdos_common.errors` — typed error envelope

`NotFoundError`, `ValidationFailure`, `ConflictError`, `UnauthorizedError`, `ForbiddenError`, `ServiceUnavailableError`. `install_error_handlers(app)` wires FastAPI.

**Not relevant for my scripts** — error handling in CLI scripts is just exception + exit code. No HTTP envelope to build.

### §1.8 `wfdos_common.graph` — Microsoft Graph (migrated from agents/graph/ in #17)

Same public surface as `agents/graph/` but re-homed. `sharepoint.list_client_documents_sync(company_safe_name, recursive=True)` lists drive items. No "download by item id" helper in the public surface I inspected — my Phase A script's download path would need either (a) a new helper added in wfdos_common.graph, or (b) keep my httpx-based direct calls.

### §1.9 `wfdos_common.testing` — shared pytest fixtures

`pytest_plugins = ["wfdos_common.testing"]` in `conftest.py` gives: `wfdos_db_session` (in-memory sqlite), `wfdos_llm_stub`, `wfdos_graph_stub`, `wfdos_auth_client`, etc.

**Relevance:** my scripts have no tests. Optional — could add scripted regression tests using these fixtures post-rewrite. Not required for integration.

### §1.10 `wfdos_common.agent` — Agent ABC (new in #26)

`wfdos_common.agent.base` defines a unified Agent base class + ToolRegistry. Used to standardize the 6 conversational agents. **Not relevant** to my batch scripts — they don't define agents.

### §1.11 Canonical schema (`docker/postgres-init/10-schema.sql`)

Fresh-install schema for docker-compose local dev. Uses BIGSERIAL PKs. **Diverges significantly from the live DB** (live uses UUIDs + has tables Gary's canonical doesn't yet include: tenants, embeddings, jobs_enriched, jobs_raw, match_narratives, cohort_matches, applications).

Gary labels it "permissive pass 1." Not authoritative for live DB migrations. **My migrations 014/016 run against the live DB, not against the canonical schema.** See §Arch Decision 3.

### §1.12 CLAUDE.md additions I should know about

Gary prepended two things to CLAUDE.md:

1. **"Load `docs/refactor/INDEX.md` first"** — per-phase map for foundation work.
2. **"GPG signing is mandatory on every commit."** My existing commits on `feature/finance-cockpit` are NOT GPG-signed. Will break the rule on any rebase/merge that creates new commits. Flag for §Arch Decision 5.

---

## §2. Key architectural decisions (preview)

Five decisions need settling before rewrites can execute cleanly. Details in §Arch Decisions section after the per-file proposals.

1. **Tenant model: UUID-FK (mine) or string-ID (Gary's)?** Determines whether migration 014 survives or gets reworked.
2. **My migrations 014 + 016 relationship to Gary's canonical schema.** Does canonical get amended to include tenants + cohort_matches, or does it remain "local-dev aspirational" while live DB stays evolved via numbered migrations?
3. **StudentProfile Pydantic model mismatch (INT vs UUID).** Decide whether to use models (post-canonical-migration) or stay on dicts for now.
4. **LLM adapter swap scope.** Replace my direct `requests.post` chat-completion calls with `wfdos_common.llm.complete`? Yes for extraction + narratives; no for embeddings + PDF parsing (adapter doesn't cover those).
5. **GPG-sign my existing commits.** Retroactively sign via rebase? Or accept the first rebase-onto-dev will create new signed commits anyway?

---

## §3. Per-file rewrite proposals

### §3.1 scripts/014-tenants-seed.sql

**Current purpose:** Creates `tenants` table (UUID PK, code TEXT UNIQUE, name TEXT, seeded with CFA + WSB rows), adds `tenant_id UUID NOT NULL REFERENCES tenants(id)` column to `students`, `jobs_enriched`, `applications`, `gap_analyses`, `match_narratives`. Backfills existing rows to CFA. Creates per-table indexes.

**Problems with current code (post-foundation-merge):**

Gary's tenant model uses a TEXT identifier resolved at request time. My migration creates a DB-level UUID entity and FK-wires tables to it. These aren't mutually exclusive (Gary's strings could map through my table), but they're not the same design. The biggest tension:

- Gary's `TenantResolver` middleware sets `request.state.tenant_id = "waifinder-flagship"` (a string). For his stack to use my table, the string needs to resolve to a UUID somewhere (presumably in the middleware or in a lookup). That's extra glue Gary hasn't written.
- If the glue exists, my migration provides the backing table Gary's foundation currently lacks. This is a real fit.
- If the glue doesn't exist and we adopt Gary's string-only model, my UUID FK columns become redundant; we'd convert them to TEXT, drop the `tenants` table, and rewrite my Phase B `WHERE tenant_id = <UUID>` clauses to `WHERE tenant_id = <string>`.

**Proposed rewrite approach:** **KEEP AS-IS** — contingent on §Arch Decision 1 going "UUID-FK with string→UUID resolver glue." Otherwise, **REPLACE** with a smaller migration that adds `tenant_id TEXT NOT NULL DEFAULT 'waifinder-flagship'` columns (no FK, no `tenants` table), seeded to `'cfa'` / `'wsb'` strings.

**Specific changes (if REPLACE path chosen):**
- Drop the `CREATE TABLE tenants (...)` block.
- Change every `tenant_id UUID REFERENCES tenants(id)` to `tenant_id TEXT NOT NULL`.
- Change backfill from `UPDATE students SET tenant_id = (SELECT id FROM tenants WHERE code='CFA')` to `UPDATE students SET tenant_id = 'cfa'`.
- Keep indexes (same shape, same rationale).
- Rename the migration file — the "tenants-seed" name stops making sense when there's no tenants table. Something like `014-tenant-id-columns.sql`.

**Architectural tensions:**
- If Gary's canonical schema eventually adds a `tenants` table (the TODO in his #16 follow-up says "migrating to a `tenants` DB table as the tenant list grows"), my migration is doing the work early. That's fine; the question is whether his conception of the `tenants` row includes `code` / `name` / `brand_config_json` or something else.
- My FK-constrained `tenant_id` means orphan prevention. If deleted tenants shouldn't cascade-orphan student rows, that's a feature. If Gary's view is that tenants are ephemeral labels, the FK is over-constraining.

**Estimated effort:**
- KEEP AS-IS path: 0 hours (already done). But expect to write ~30 min of docs explaining the glue required in Gary's middleware.
- REPLACE path: 2–3 hours (migration rewrite + re-run + data migration if live DB already has UUID-typed `tenant_id` columns filled with my UUIDs → would need `ALTER TYPE` + re-backfill; NOT trivial).

**Risks:**
- If both KEEP and Gary's model coexist without glue, two competing tenant identifiers float around — any code that gets `request.state.tenant_id` as a string can't use my UUID FKs directly. Runtime bugs become likely.
- If REPLACE chosen and my Phase B data is already keyed by UUID, re-keying requires a migration dance: new TEXT column, copy values via `tenants.code` lookup, drop UUID column, rename. Plus re-indexing. Plus all my `WHERE tenant_id = <WSB UUID>` queries in Phase B scripts break.

### §3.2 scripts/015-tenant-id-jobs-raw.sql

**Current purpose:** Ritu listed this in the inputs, but **this file does not exist on my branch.** `git ls-tree feature/finance-cockpit -- scripts/015-tenant-id-jobs-raw.sql` returns nothing. `ls scripts/015*` → no matches.

**Proposed rewrite approach:** **N/A — file doesn't exist.**

**If Ritu wants this to exist** (i.e., add `tenant_id` to `jobs_raw` table): a new migration would mirror 014's approach for that one table. Small — jobs_raw has a `deployment_id` column that already partitions by tenant effectively, so `tenant_id` is duplicative unless there's a specific query path that needs it. Flag for Ritu to clarify intent.

### §3.3 scripts/016-cohort-matches.sql

**Current purpose:** Creates `cohort_matches(id UUID PK, tenant_id UUID FK, student_id UUID FK, job_id INT FK, cosine_similarity FLOAT, match_rank INT, generated_at TIMESTAMPTZ, model_name TEXT, template_version TEXT)` with indexes and UNIQUE(student_id, job_id, tenant_id). Tenancy native to the table per §Phase A architectural pattern.

**Problems with current code (post-foundation-merge):**

- Same tenant_id typing tension as 014 — UUID FK here, TEXT in Gary's model. Dependent on §Arch Decision 1.
- Gary's canonical schema does not include a `cohort_matches` table. **This is my addition to the platform's schema.** Canonical schema would need amending to reflect it, OR cohort_matches stays live-DB-only (Gary's canonical treats it as "application-added, not core").

**Proposed rewrite approach:** **KEEP AS-IS** structurally (table shape is well-designed for its purpose), contingent on §Arch Decision 1 outcome. Two possible tweaks:
- If TEXT tenant_id path: replace `tenant_id UUID` → `tenant_id TEXT NOT NULL`, drop the FK to tenants(id). Matches 014's rewrite.
- If Gary wants cohort_matches in canonical schema: copy the CREATE TABLE block into `docker/postgres-init/10-schema.sql` (with BIGSERIAL PKs per Gary's convention? or UUID per live DB? see §Arch Decision 3).

**Specific changes:** Only if tenant_id path changes, apply the same substitution pattern as 014.

**Architectural tensions:**
- `match_rank` is application-assigned (1..N). This is fine but Gary may have an opinion on whether ranks should be re-derived from `cosine_similarity` on read vs. stored. Currently stored. Small design question.
- `model_name` + `template_version` are provenance columns for matching reproducibility. Gary's canonical doesn't have this pattern anywhere else; might be considered out-of-scope for canonical.

**Estimated effort:** KEEP AS-IS: 0 hours. Reshape for TEXT tenant_id: 1 hour (migration edit + re-apply).

**Risks:** If tenant_id typing changes in 014, must change here in lockstep — they're FK-connected conceptually even if not literally.

### §3.4 scripts/phase_a_fetch_sharepoint_resumes.py

**Current purpose:** Resolves SharePoint site (`computinforall.sharepoint.com/sites/cfatechsectorleadership`), walks to folder "Feb 23rd 2026 Cohort Resumes", downloads 9 PDFs to `data/cohort1_resumes/`.

**Problems with current code:**

- **Line 14**: `from azure.identity import ClientSecretCredential` — I import directly; Gary's `wfdos_common.graph.auth` already centralized this.
- **Lines 22–30**: reads `GRAPH_TENANT_ID`, `GRAPH_CLIENT_ID`, `GRAPH_CLIENT_SECRET` via `os.getenv` with AZURE_* fallback — `wfdos_common.config.settings.graph.*` has these (GraphSettings class I saw named).
- **Lines 38–57** (`get_token`, `headers`, `resolve_site`, `get_default_drive_id`): duplicates `_get_token`, `_headers`, `_get_drive_id` that `wfdos_common.graph.sharepoint` already exports.
- **Lines 58–94** (list_children, find_folder_recursive): no direct equivalent in `wfdos_common.graph.sharepoint` public surface — the closest is `list_client_documents_sync(company_safe_name, recursive=True)`, but that's scoped to the internal client workspace hierarchy, not arbitrary folder walks. My code would need to either (a) add a generic helper to `wfdos_common.graph.sharepoint` for downloading by folder path, (b) keep my walker but delegate token/drive resolution to `wfdos_common.graph`.
- **Lines 96–107** (`download_file`): streams via httpx; no direct wfdos_common equivalent (Gary's module creates+writes but doesn't download).

**Proposed rewrite approach:** **ADAPT (partial).**

**Specific changes:**
- Imports: replace `from azure.identity import ClientSecretCredential` with `from wfdos_common.graph.auth import get_token` (or whatever the public getter is — I'd verify before writing). Similarly for `_get_drive_id`.
- Replace `os.getenv("GRAPH_TENANT_ID")` / `AZURE_TENANT_ID` fallback block with `from wfdos_common.config import settings` + `settings.graph.tenant_id` / `settings.graph.client_id` / `settings.graph.client_secret`.
- Replace my `get_token`, `headers`, `resolve_site`, `get_default_drive_id` helpers with calls to wfdos_common.graph's versions.
- **KEEP** the `list_children`, `find_folder_recursive`, `download_file` helpers — no equivalents in wfdos_common. Consider upstreaming them later to wfdos_common.graph.sharepoint for reuse.
- Logging: swap `print()` → `wfdos_common.logging.get_logger(__name__).info(...)`.
- `configure(service_name="phase-a-fetch-sharepoint-resumes")` once at the top.

**Architectural tensions:**
- If Ritu wants zero direct httpx calls in my scripts, the "download by item id" helper needs to land in wfdos_common.graph first. That's a Gary PR, not mine. Flag as prerequisite.
- SharePoint tenant hostname is a CFA-specific ambient fact; not in Gary's settings model (SharePointSettings has site IDs but not arbitrary site resolution). OK to keep in my script as a constant with a comment.

**Estimated effort:** 1.5 hours (swap imports + auth + settings; keep domain logic).

**Risks:**
- If `wfdos_common.graph.auth.get_token()` has a different scope or caches tokens differently, my fetch script may need retry logic I don't currently have.
- Gary's module may enforce tenant context on Graph calls — need to verify that works for "fetching resumes on behalf of the CFA SharePoint" without a tenant being resolved by middleware (my script runs as CLI, not as an HTTP request).

### §3.5 scripts/phase_a_parse_cohort1_resumes.py

**Current purpose:** Reads 9 PDF resumes from `data/cohort1_resumes/`, calls Gemini 2.5 Flash with `inline_data` for structured extraction, INSERTs 9 new rows into `students` with tenant_id = WSB, cohort_id = `cohort-1-feb-2026`. Writes `student_skills` and `student_work_experience` rows.

**Problems with current code:**

- **Line 27–32**: imports `google.generativeai as genai` directly. **Cannot use `wfdos_common.llm.complete`** — that adapter is text-completion-only, no PDF `inline_data`. Stays on direct SDK.
- **Line 37**: `genai.configure(api_key=os.getenv("GEMINI_API_KEY"))` — should be `settings.llm.gemini_api_key` if Gary exposes it, else stay on env.
- **Line 36** (`PG_CONFIG` inline dict literal): I hardcoded `{"host": "127.0.0.1", ...}` as a local constant instead of importing from `scripts/pgconfig.py`. Should switch to `from wfdos_common.config import PG_CONFIG`.
- **Line 160** (`psycopg2.connect(**PG_CONFIG)`): stays unchanged — the PG_CONFIG shim is drop-in.
- **Logging**: `print()` throughout. Swap to `wfdos_common.logging`.
- **Tenant handling**: `wsb_tenant_id(conn)` looks up the UUID via `SELECT id FROM tenants WHERE code='WSB'`. Depending on §Arch Decision 1:
  - UUID path: stays the same (reads from `tenants` table).
  - TEXT path: set `tenant_id = 'wsb'` directly; drop the `wsb_tenant_id()` helper.

**Proposed rewrite approach:** **ADAPT.**

**Specific changes:**
- Imports: `from wfdos_common.config import settings, PG_CONFIG` (PG_CONFIG shim + settings for Gemini key).
- Drop the inline `PG_CONFIG = {...}` literal.
- `genai.configure(api_key=settings.llm.gemini_api_key or os.getenv("GEMINI_API_KEY"))` — or add `settings.gemini.api_key` if GaryExposes it; I'm not sure where he keeps Gemini credentials if at all.
- Remove `wsb_tenant_id` helper → decide per §Arch Decision 1.
- Logging: swap `print()` → `wfdos_common.logging.get_logger(__name__)`.
- `configure(service_name="phase-a-parse-cohort1-resumes")` at entry.
- Keep `EXTRACTION_PROMPT` verbatim (lifted from `agents/profile/parse_resumes.py` — should match whatever's canonical).

**Architectural tensions:**
- Gemini PDF inline_data isn't in Gary's adapter. OK to stay on direct SDK — he explicitly scoped `wfdos_common.llm` to simple text completion. But if wfdos_common grows a multimodal/embeddings surface later, this script should migrate.
- `cohort_id` string (`cohort-1-feb-2026`) is a free-text label on the students row, not a first-class entity. Gary has no cohort model in canonical schema. Fine for now.

**Estimated effort:** 1.5 hours.

**Risks:** Gemini API key retrieval may not match how Gary has Gemini creds configured — `LlmSettings` has `provider="azure_openai"` as default but I didn't see explicit `gemini_api_key` or `google_api_key` fields. Worth checking before assuming `settings.llm.gemini_api_key` exists.

### §3.6 scripts/phase_a_ingest_elpaso_jobs.py

**Current purpose:** Queries JSearch via RapidAPI for 6 job query strings, dedups across queries, filters (Borderplex metro + clearance + senior-title), INSERTs into `jobs_enriched` + `jobs_raw` with `tenant_id = WSB`, `deployment_id = 'wsb-elpaso-cohort1'`. Caches raw JSearch responses to disk. Has a `--reconcile` mode to re-apply filters on cached data.

**Problems with current code:**

- `from dotenv import load_dotenv` + `load_dotenv(r"C:\Users\ritub\Projects\wfd-os\.env")` — Gary's settings auto-loads via `find_dotenv`. Should drop.
- `os.getenv("RAPIDAPI_KEY")` — not in Gary's settings (no RapidAPI fields I found). Stays on env OR gets added to `LlmSettings`/new `JSearchSettings`.
- Hardcoded `PG_CONFIG` dict literal (same as 3.5). Swap to compat shim.
- `psycopg2.connect(**PG_CONFIG)` stays.
- Tenant lookup (`lookup_tenant_uuid`) — same §Arch Decision 1 dependency.
- Logging: `print()` throughout.

**Proposed rewrite approach:** **ADAPT.**

**Specific changes:** Same pattern as §3.5 — import `PG_CONFIG` + `settings`, drop inline PG_CONFIG literal, drop explicit dotenv load. RAPIDAPI_KEY stays on `os.getenv` (or prompt Ritu/Gary to add a setting). Logging swap.

**Architectural tensions:**
- `deployment_id` is a string tag on `jobs_raw` / `jobs_enriched` distinct from tenant_id. If Gary's tenant model is string-ID too, these two string identifiers start to look redundant (both are tenant-like partitioning). Gary's canonical schema doesn't include `deployment_id` on any table — it's my Phase 2D invention. Worth a conversation on whether deployment_id collapses into tenant_id going forward.

**Estimated effort:** 1 hour.

**Risks:** Low. The script's domain logic is self-contained (JSearch → filter → insert). Swapping infrastructure calls doesn't change behavior.

### §3.7 scripts/phase_b_task1_apprentice_embeddings.py

**Current purpose:** Generates embeddings for 9 WSB apprentices via Azure OpenAI `embeddings-te3small` deployment (1536-dim, text-embedding-3-small). Reuses `render_student`, `embed_text`, `upsert_embedding` from `backfill_embeddings.py`. Writes to `embeddings` table.

**Problems with current code:**

- Imports `backfill_embeddings as bf` via `sys.path.insert` at line 22. Gary's #27 eliminates sys.path hacks by making `agents.*` a namespace package (per-service pyproject). But `scripts/` isn't a namespace package — it's a flat CLI directory. So the `sys.path.insert(0, str(SCRIPTS_DIR))` stays unless Gary's packaging changed `scripts/`. Likely stays; verify.
- `from pgconfig import PG_CONFIG` — `scripts/pgconfig.py` should now re-export from `wfdos_common.config.PG_CONFIG` per Gary's §1.1 compat shim (I saw the comment "`scripts/pgconfig.py` itself is kept as a one-line re-export for any CLI script that still imports it by filename path"). Current import still works post-merge.
- `bf.embed_text(text)` — wfdos_common.llm is completion-only, no embeddings equivalent. Stays on Azure OpenAI direct calls.
- Logging: `print()` throughout.
- Tenant UUID lookup (§Arch Decision 1).

**Proposed rewrite approach:** **ADAPT (light).**

**Specific changes:**
- Verify `from pgconfig import PG_CONFIG` still resolves post-merge (Gary kept the re-export; low risk).
- Logging swap.
- Per §Arch Decision 1, adjust `lookup_tenant_uuid` usage.
- No change to `bf.embed_text` — raw Azure OpenAI is correct here.

**Architectural tensions:** None substantive. The script is embedding-generation infrastructure that doesn't overlap with Gary's foundation.

**Estimated effort:** 0.5 hours (logging swap + tenant handling).

**Risks:** Very low.

### §3.8 scripts/phase_b_task2_job_embeddings.py

**Current purpose:** Same as §3.7 but for 40 WSB jobs. Uses `render_job` + `extract_job_description` (LLM-cleans description via chat-gpt41mini before embedding) + `embed_text` from `backfill_embeddings`.

**Problems:** Same as §3.7 (pgconfig import, embeddings direct Azure call, logging). Additional: `extract_job_description` uses chat-gpt41mini via direct `requests.post` to Azure OpenAI. **This one COULD swap to `wfdos_common.llm.complete(..., tier="default")`** — same model, same semantics. Minor code change.

**Proposed rewrite approach:** **ADAPT.**

**Specific changes:**
- Same boilerplate as §3.7 (settings + logging).
- **`extract_job_description` in `backfill_embeddings.py`** — swap its raw Azure call to `wfdos_common.llm.complete`. But `backfill_embeddings.py` isn't mine (pre-existing script); modifying it is out of my scope here. **Flag as potential for Gary/Ritu to decide whether to adapt `backfill_embeddings.py`.**
- Within my own task2 script, nothing direct to swap.

**Architectural tensions:**
- `backfill_embeddings.py` is arguably in the set of modules Gary should adapt (#20 adapter migration). It does chat-completion for description cleanup AND embeddings. Half its calls should go through the adapter; the other half shouldn't. Hybrid retrofit. Flag for conversation with Gary.

**Estimated effort:** 0.5 hours (same as §3.7).

**Risks:** Low.

### §3.9 scripts/phase_b_task3_matching.py

**Current purpose:** Runs WSB-scoped top-10 matching query per apprentice via direct psycopg2 cosine query (uses pgvector `<=>`). Persists 90 rows to `cohort_matches` with rank, cosine, model+template provenance.

**Problems with current code:**

- Direct `psycopg2` cosine query — explicitly documented as adapting `data_source.py::student_matches()` with tenant filter added. Gary's `wfdos_common.db.queries` has `get_student_profile`, `get_student_skills`, `get_student_skill_count` but **no tenant-scoped matching helper.** My query logic is bespoke.
- Earlier tech debt flagged `student_matches()` should become tenant-aware (§Phase B Task 3 report). That's a Gary-side change, not mine — my script already does the right thing.
- Logging, tenant lookup, PG_CONFIG: same as §3.7.

**Proposed rewrite approach:** **KEEP AS-IS** for the matching query body (no wfdos_common equivalent exists). **ADAPT** for boilerplate (settings, logging, tenant handling).

**Specific changes:** boilerplate only. The core matching SQL stays as the Phase B source of truth until Gary's matching helpers become tenant-aware.

**Architectural tensions:**
- My `MATCH_SQL` constant could eventually move into `wfdos_common.db.queries.get_top_matches_for_student(session, student_id, tenant_id, limit)`. That's a foundation PR, not a rewrite of my code. Flag as future-work opportunity for Gary.
- Use of raw cursor execution vs SQLAlchemy Session — Gary's queries support both (§1.1 dual-path helpers). If my script used `session_scope()` instead of `psycopg2.connect`, it'd still work. Whether to swap is the bigger §Arch Decision 4.

**Estimated effort:** 0.5 hours.

**Risks:** Low.

### §3.10 scripts/phase_b_task4_gap_analyses.py

**Current purpose:** Extracts `skills_required` via LLM from each WSB job description (populates `jobs_enriched.skills_required`), then runs `mn.compute_overlap(student, job)` for each (apprentice, top-3 match) pair, computes gap_score, INSERTs 27 rows into `gap_analyses` with tenant_id = WSB.

**Problems with current code:**

- **Lines 88–124** (`llm_extract_skills`): calls `chat-gpt41mini` via direct `requests.post` to Azure OpenAI. **Can swap to `wfdos_common.llm.complete(..., tier="default")`.** Prompt format stays; JSON parsing stays.
- Imports `match_narrative as mn` via `sys.path.insert` to `agents/job_board/`. **`match_narrative.py` is uncommitted Phase 2G work** — not part of canonical code, lives as a working file on my branch. The import mechanism is fine post-merge; the module's location is the question.
- `fetch_student` / `fetch_job` duplicates existing `wfdos_common.db.queries.get_student_profile` partially. **`get_student_profile` in wfdos_common returns a different shape — it's for the `/student_api` endpoint, not for `compute_overlap` input.** I checked: my `fetch_student` includes skills + work_experience in a specific shape (`skills: [{name, source}]`) that compute_overlap expects; `get_student_profile` returns flat profile fields. Not a drop-in swap.
- Imports `llm_extract_skills` locally (defined in this file) — no wfdos_common equivalent; stays.
- Logging, settings, PG_CONFIG: same as §3.7.

**Proposed rewrite approach:** **ADAPT.**

**Specific changes:**
- **Swap `llm_extract_skills`'s raw HTTP call to `wfdos_common.llm.complete`**:

  ```python
  # BEFORE (current)
  resp = requests.post(
      f"{AZURE_ENDPOINT}/openai/deployments/{CHAT_DEPLOYMENT}/chat/completions?...",
      headers={"api-key": AZURE_KEY, ...},
      json={"messages": [{"role": "user", "content": prompt}], "temperature": 0.0, "max_tokens": 400},
      timeout=30,
  )
  content = resp.json()["choices"][0]["message"]["content"].strip()

  # AFTER (wfdos_common.llm)
  from wfdos_common.llm import complete
  content = complete(
      messages=[{"role": "user", "content": prompt}],
      tier="default",
      max_tokens=400,
      temperature=0.0,
  )
  ```

- `fetch_student` / `fetch_job` stay — their shape matches compute_overlap's input contract, and compute_overlap is Gary's (via match_narrative.py which is Ritu's Phase 2G).
- Logging swap.
- Settings + PG_CONFIG swap (same as §3.7).

**Architectural tensions:**
- Would be cleaner if `compute_overlap` lived in `wfdos_common` (it's domain-generic matching logic). Currently it's under `agents/job_board/match_narrative.py` on my branch, uncommitted. That's a Phase 2G landing decision, not a Phase B rewrite decision. Flag for §Arch Decision 4.
- `fetch_student` returns `work_experience` with `datetime.date` objects — I had a bug around this in Phase B Task 5 (had to serialize dates inline). If Gary's `get_student_profile` returns ISO strings, swapping would fix this bug. Worth inspecting `queries.py` more carefully before deciding.

**Estimated effort:** 1–1.5 hours.

**Risks:**
- `wfdos_common.llm.complete`'s error surface may differ from my direct-call errors (I catch `resp.raise_for_status()`; adapter raises `ProviderError`). Need to update exception handling.
- If `wfdos_common.llm.complete` adds stronger retries or fallbacks, I could get subtly different results vs. my current direct call. Not a correctness issue, just a behavior change.

### §3.11 scripts/phase_b_task5_narratives.py

**Current purpose:** For each (apprentice, top-3 match) pair, calls `mn.generate_narrative(student, job, overlap, cosine, label)` which LLM-generates verdict_line + narrative_text via `chat-gpt41mini`. INSERTs 27 rows into `match_narratives` with tenant_id = WSB.

**Problems with current code:**

- **`match_narrative._call_chat_json` in `agents/job_board/match_narrative.py`** (Phase 2G uncommitted) uses direct `requests.post` to Azure OpenAI chat-gpt41mini. **Same swap opportunity as §3.10.** But modifying `match_narrative.py` is Phase 2G work, not mine. Flag for Ritu/Gary's decision on whether that module becomes wfdos_common-adapter-backed.
- `_serialize_student_dates` helper I wrote inline is a workaround for a bug in my Task 4 `fetch_student`. If that bug gets fixed upstream, this workaround goes away.
- Logging, settings, PG_CONFIG: same boilerplate.
- `compute_input_hash` caches the input tuple; stays as-is.

**Proposed rewrite approach:** **ADAPT (boilerplate only)**. The substantive LLM-call swap belongs in `match_narrative.py`, which I don't own for this rewrite.

**Specific changes:** boilerplate (settings, logging, PG_CONFIG swap). Remove `_serialize_student_dates` if `fetch_student` is fixed upstream.

**Architectural tensions:**
- `match_narrative.py` is arguably a wfdos_common-worthy module (domain-generic: given student + job + overlap + cosine, produce recruiter's note). If it moves into wfdos_common.* later, my import path changes. One-line fix when that happens.

**Estimated effort:** 0.5 hours.

**Risks:** Low.

### §3.12 scripts/phase_b_task6_placement_report.py

**Current purpose:** Reads from `cohort_matches`, `gap_analyses`, `match_narratives`, `students`, `jobs_enriched` (all WSB-tenant) to produce a markdown placement report at `docs/cohort1_placement_report.md`. Aggregate findings + per-apprentice sections.

**Problems with current code:**

- All reads go through direct psycopg2. Could use `session_scope(wsb_tenant_id)` + SQL via SQLAlchemy, but no functional advantage for a read-only report generator.
- `years_from_work` calc: local utility, no overlap with wfdos_common.
- Logging + settings + PG_CONFIG: same boilerplate.
- Tenant lookup: same §Arch Decision 1.

**Proposed rewrite approach:** **ADAPT (boilerplate only).** This is a pure read-only report generator; touching the DB access pattern yields nothing.

**Specific changes:** boilerplate.

**Architectural tensions:** None.

**Estimated effort:** 0.5 hours.

**Risks:** None.

---

## §4. Consolidated architectural decisions

### Arch Decision 1 — Tenant model: UUID-FK (mine) vs string-ID (Gary's)

**Options:**

1. **UUID-FK wins, Gary's middleware adds a resolver step.** My `tenants` table stays; `TenantResolver` middleware looks up `tenants.code` from `Host`/`X-Tenant-Id` header and sets `request.state.tenant_id` to the UUID string representation. All my Phase A/B data stays valid. Gary updates `wfdos_common.db.middleware` to do the lookup — small change.

2. **String-ID wins, my migration gets reworked.** Change my `tenant_id UUID REFERENCES tenants(id)` columns to `tenant_id TEXT NOT NULL`. Drop the `tenants` table. Rewrite backfill to use string codes (`'cfa'`, `'wsb'`). Rewrite all my Phase B `WHERE tenant_id = <UUID>` queries. Multi-hour rework if any live Phase B data needs migrating.

3. **Both coexist deliberately.** `tenants` table for audit/lookup purposes; `request.state.tenant_id` as string. Application code picks the right one per context. Highest complexity; hardest to reason about. Don't recommend.

**Trade-offs:**
- Option 1: preserves Phase A/B investments, adds one lookup per request. Gary might object because he didn't design for a DB-backed tenant lookup; he explicitly kept tenants as "ambient labels" in #16.
- Option 2: cleaner alignment with Gary's model; requires rework of Phase A/B data. The rework is mechanical but not free.
- Option 3: flexible; too-flexible; avoid.

**Recommendation:** I'm not supposed to recommend, per your instruction. Both 1 and 2 are defensible. Depends on whether Gary wants a `tenants` DB entity eventually (his #16 TODO hints yes).

### Arch Decision 2 — My migrations 014/016 relationship to Gary's canonical schema

**Options:**

1. **Canonical schema is amended** to include `tenants`, `cohort_matches`, `embeddings`, `jobs_enriched`, `jobs_raw`, `match_narratives` with appropriate PK types (matching live DB — UUID where live uses UUID, INT where live uses INT). Canonical becomes authoritative.
2. **Canonical stays aspirational**, live DB remains as-is with my migrations. `docs/refactor/` documents the divergence; nothing forces convergence until a platform-wide schema-alignment project.
3. **My migrations replay into canonical** as bootstrap statements (docker-compose init). Simpler variation of option 1.

**Trade-offs:**
- Option 1: correct, heavy. Requires PK-type decision (UUID? BIGSERIAL?) across ~6 tables; touches live-DB migration plan.
- Option 2: pragmatic; canonical schema's value is limited to greenfield local dev. Acceptable given Phase B work is recent and stable.
- Option 3: best for local-dev parity; requires the BIGSERIAL-vs-UUID alignment regardless.

### Arch Decision 3 — Use Gary's Pydantic StudentProfile model?

Currently blocked by the INT-vs-UUID PK mismatch (§1.5). `StudentProfile.id: int` vs live DB `students.id: UUID`. Using the model would require either:
- Gary changes the model's `id` field to `str | int | uuid.UUID`.
- Live DB students.id gets migrated to BIGSERIAL (major change; ~every FK updates).
- I skip the model and keep dict-based Phase B row handling.

**Recommendation:** skip the model for now; revisit if/when canonical schema and live DB align.

### Arch Decision 4 — LLM adapter swap scope

Three places where my code calls chat-gpt41mini via direct HTTP:
1. `llm_extract_skills` in `phase_b_task4_gap_analyses.py` (mine — swap to `wfdos_common.llm.complete`).
2. `_call_chat_json` in `match_narrative.py` (Phase 2G, not mine — Ritu/Gary's decision).
3. `extract_job_description` in `backfill_embeddings.py` (pre-existing, not mine — Gary/Ritu's decision).

**Where adapter does NOT fit:** `embed_text` (embeddings API), resume-PDF parsing (Gemini `inline_data`). These stay on direct SDK.

**Recommendation:** swap #1 as part of my rewrite (0.5 hour). Flag #2 and #3 for separate discussion.

### Arch Decision 5 — GPG-sign existing commits?

Gary's CLAUDE.md says GPG is mandatory. My 33 commits on `feature/finance-cockpit` are unsigned. Options:

1. **Rebase my branch onto current origin/development** — rebase creates new commits, which get signed if GPG is configured. Loses nothing; aligns with policy.
2. **Merge origin/development into feature/finance-cockpit** — my existing commits stay unsigned; the merge commit is new and gets signed. Partial compliance; Gary may object.
3. **Leave as-is, document the exception** — non-compliant; likely not acceptable per "Never use ... to bypass" language.

**Recommendation:** option 1 is cleanest; combine with the integration rebase (see §5 execution order). Configure GPG before starting.

---

## §5. Proposed execution order

Assuming §Arch Decisions resolved, here's a risk-minimizing sequence:

1. **Agree on §Arch Decisions 1–5** (discussion, not code). Block rewrites until settled.
2. **Verify `wfdos_common.config.PG_CONFIG` compat shim works** by pointing one simple script (`phase_b_task6_placement_report.py` — pure read, no writes) at `from wfdos_common.config import PG_CONFIG` and running. Confirms the shim path is valid without risk.
3. **Rewrite migrations 014 + 016 based on §Arch Decision 1 outcome** (either KEEP or REPLACE both in lockstep). Apply against a throwaway DB first if REPLACE path.
4. **Adapt the boilerplate across all 8 Python scripts in one pass** (settings import, PG_CONFIG import, structured logging). Minimal risk; mostly sed-able edits. ~4 hours.
5. **Swap `llm_extract_skills` in task4 to `wfdos_common.llm.complete`** (§3.10). Test Phase A/B end-to-end (27 gap analyses should still produce the same rows). ~1 hour.
6. **Adapt `phase_a_fetch_sharepoint_resumes.py`** to use `wfdos_common.graph.auth` (§3.4). Test SharePoint fetch for 9 resumes still works. ~1.5 hours.
7. **Defer**: anything that needs new wfdos_common helpers (generic folder download, tenant-aware matching, etc.) — raise as separate Gary-side PRs, not in my rewrite.
8. **Rebase feature/finance-cockpit onto current origin/development** with the rewrite commits baked in. Resolve the 2 textual conflicts flagged in `integration_recon.md` (.gitignore, agents/assistant/api.py). ~2 hours.
9. **Run the full Phase B pipeline** (Tasks 1–7) against the rebased tree to verify end-to-end. Compare row counts and spot-check narratives against pre-rebase output. ~1 hour.
10. **Final commit + push.** Ensure GPG-signed.

**Total: ~12–18 hours** plus discussion time for §Arch Decisions.

---

## §6. Things I noticed that don't fit the other steps

### §6.1 Opportunities to benefit from Gary's foundation in future phases

- **`@read_only` decorator** for any future read-only staff dashboards I build — gives auth + DB-write-protection for free.
- **`@llm_gated` decorator** for any LLM-consuming endpoints (narrative regeneration, gap-analysis recompute from the UI). Auto-gracefully degrades if LLM creds missing.
- **`wfdos_common.testing` fixtures** — I could retrofit Phase B with `wfdos_db_session` + `wfdos_llm_stub` to make the 6 Phase B scripts re-runnable in CI against synthetic data. Significant value if Cohort 2 lands.
- **`wfdos_common.graph.sharepoint`** — useful when I extend to pulling additional SharePoint artifacts (Alma's 19-district job postings, etc.). Stay on the library rather than re-rolling httpx clients.
- **`settings.tenancy.default_tenant_id` + `BrandConfig`** — if the placement report ever becomes a branded portal artifact (per-customer white-label), brand config is ready to plug in.

### §6.2 Patterns my code uses that would be cleaner with the foundation

- **Structured logging (not print)** — immediate quality win. JSON logs with tenant_id/user_id auto-attached lets me grep by apprentice or by cohort without parsing text.
- **Typed errors (`wfdos_common.errors`)** — my scripts currently `raise RuntimeError(...)` or just let exceptions propagate. Typed errors give consistent exit codes and integration with any future monitoring.
- **`ConfigurationError` from `settings.require(*paths)`** — fails fast if required config is missing. Cleaner than my scattered `if not os.getenv(...): raise RuntimeError`.

### §6.3 Things missing from this proposal that the conversation with Gary should cover

- **Whether `backfill_embeddings.py` and `match_narrative.py` get adapter-migrated.** Both have direct Azure OpenAI calls that could use `wfdos_common.llm`. Both are not in my "my 11 files" set, so I can't propose rewrites; but they're in the same functional space.
- **Whether `agents/job_board/api.py` + `data_source.py` get migrated to `wfdos_common.db`.** My Phase B matching query adapts the pattern; if the upstream gets tenant-aware, my duplicate goes away. Gary's #22c migrated 5 portal APIs but skipped job_board (not a portal API). When does it get its turn?
- **Port 8012 collision** (from `integration_recon.md`). Foundation-adjacent: laborpulse is Gary's new service; job_board is mine. Someone moves.
- **`integrate/grant-compliance-scaffold` disjoint branch** — separate integration problem. Its own rewrite proposal would include its own tenant model, its own Alembic migrations, its own grant_compliance FastAPI app. Out of scope for this doc but part of the full landscape.

### §6.4 Self-corrections and uncertainties

- I stated `settings.graph.tenant_id` exists — I saw the class name `GraphSettings` but didn't read the body. Field names may differ (could be `azure_tenant_id` or similar). Verify before writing `settings.graph.tenant_id` in a rewrite.
- I stated `settings.llm.gemini_api_key` probably exists — didn't confirm. Gemini creds may not be in settings at all; stay on `os.getenv("GEMINI_API_KEY")` unless verified.
- `wfdos_common.graph.sharepoint._get_token()` — I inferred from the `_get_token` symbol being in the module. Whether it's actually exported publicly or stays as a private helper — unverified.
- Gary's `settings.tenancy` class — I saw `TenancySettings` implied in middleware code ("`settings.tenancy.default_tenant_id`") but didn't inspect the class. Shape of any `tenants` list / mapping is unverified.
- `wfdos_common.auth`'s `SessionMiddleware` shape I know from `agents/assistant/api.py` diff; hadn't inspected its own code for subtleties like cookie domain configuration.

Each uncertainty is small and would surface during the actual rewrite. Flag so you know what to verify before trusting the specific swap.

---

## §7. Summary table — all 11 files (scripts/015 excluded as nonexistent)

| File | Approach | Est. hours | Main swap |
|---|---|---:|---|
| scripts/014-tenants-seed.sql | KEEP (conditional) / REPLACE | 0 or 2–3 | §Arch Decision 1 |
| scripts/015-tenant-id-jobs-raw.sql | N/A — file doesn't exist | — | — |
| scripts/016-cohort-matches.sql | KEEP (conditional) / MINOR | 0 or 1 | Same as 014 |
| phase_a_fetch_sharepoint_resumes.py | ADAPT | 1.5 | `wfdos_common.graph.auth` + settings + logging |
| phase_a_parse_cohort1_resumes.py | ADAPT | 1.5 | PG_CONFIG shim + settings + logging; Gemini stays direct |
| phase_a_ingest_elpaso_jobs.py | ADAPT | 1 | PG_CONFIG shim + settings + logging; RAPIDAPI_KEY stays direct |
| phase_b_task1_apprentice_embeddings.py | ADAPT (light) | 0.5 | Logging only |
| phase_b_task2_job_embeddings.py | ADAPT (light) | 0.5 | Logging only; flag `backfill_embeddings.py` for Gary |
| phase_b_task3_matching.py | KEEP + boilerplate | 0.5 | Match SQL stays; logging swap |
| phase_b_task4_gap_analyses.py | ADAPT | 1–1.5 | `wfdos_common.llm.complete` for skill extraction |
| phase_b_task5_narratives.py | ADAPT (light) | 0.5 | Logging only; flag `match_narrative.py` for Gary |
| phase_b_task6_placement_report.py | ADAPT (light) | 0.5 | Logging only |

**Total per-file effort: 7.5–10.5 hours** (low estimate assumes KEEP on 014/016; high assumes REPLACE).
**Plus §5 integration rebase: 2–3 hours.**
**Plus §Arch Decisions discussion time: un-estimable but gating.**

**Grand total ~12–18 hours of execution** once decisions are settled.

---

*End of rewrite proposals. No code modified. No commits. Document is at `docs/rewrite_proposals.md` on `feature/finance-cockpit` worktree, uncommitted.*
