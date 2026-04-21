# Refactor + feature artifacts — index

**Read this first every session.** Then load only the specific
per-phase / per-feature MDs you need for the current task. The plan
file at `~/.claude/plans/wild-splashing-cascade.md` is the strategic
router; this file is the tactical map.

## Phase status

| Phase | Status | Scope (one line) | Exit report | Representative PRs |
|---|---|---|---|---|
| 1 — Package foundation | ✅ COMPLETE | scaffold `wfdos-common`, config + secrets, remove hardcoded passwords | — (predates convention; see PR bodies) | #33, #34, #35, #37 |
| 2 — Shared primitives | ✅ COMPLETE | Pydantic models, multi-tenant DB engine + canonical schema, LLM adapter | [`phase-2-exit-report.md`](./phase-2-exit-report.md) | #38, #39, #40, #41, #42, #43 |
| 3 — Observability + packaging | ✅ COMPLETE | structured logging, pytest fixtures, per-service pyproject, endpoint validation | [`phase-3-exit-report.md`](./phase-3-exit-report.md) | #44, #45, #46, #47, #48 |
| 4 — Security + auth | ✅ COMPLETE | magic-link auth, tier decorators, credential-rotation runbook | [`phase-4-exit-report.md`](./phase-4-exit-report.md) | #49, #50, #51, #52 |
| 5 — Product + infra cut-over | ✅ COMPLETE | Agent ABC, white-label, edge proxy, CTA contract | [`phase-5-exit-report.md`](./phase-5-exit-report.md) | #53, #54, #55, #56, #57 |
| LaborPulse Q&A | ✅ COMPLETE (pending smoke) | workforce-development role + Q&A endpoint + mock mode | [`laborpulse-exit-report.md`](./laborpulse-exit-report.md) | #60, #61 |

None of these PRs are merged to `master` yet; the stacked-branch
strategy keeps everything composable until Gary signs off on the
full stack. See the plan file for the squash-merge order.

## Module → phase map

When debugging a specific module, jump directly to the MD that
introduced it.

### `packages/wfdos-common/wfdos_common/`

| Module | Phase | Doc |
|---|---|---|
| `config/` (settings, secrets, pg_config) | 1 | PR #34; `docs/config/identity-migration.md` |
| `graph/`, `email/` | 1 | PR #33 |
| `models/` (core, domain, scoping) | 2 | `phase-2-exit-report.md` |
| `db/` (engine, session, tenant middleware, queries) | 2 | `phase-2-exit-report.md` |
| `llm/` (adapter + provider routing) | 2 | `phase-2-exit-report.md` |
| `logging.py` (structlog + ContextVars + middleware) | 3 | `phase-3-exit-report.md` |
| `testing/plugin.py` (shared pytest fixtures) | 3 | `phase-3-exit-report.md` |
| `errors.py` (envelope handlers + typed exceptions) | 3 | `phase-3-exit-report.md`, `issue-29-migration.md` |
| `auth/` (tokens, allowlist, middleware, dependencies, routes, tiers) | 4 | `phase-4-exit-report.md` |
| `tenancy.py` (white-label brand config) | 5 | `phase-5-exit-report.md`, `docs/white-label-config.md` |
| `agent/` (Agent ABC + ToolRegistry) | 5 | `phase-5-exit-report.md` |

### `agents/`

| Service | Phase | Doc |
|---|---|---|
| `portal/{student,showcase,consulting,college,wji}_api.py` | 3-4 (migrated) | `phase-3-exit-report.md` (errors), `phase-4-exit-report.md` (auth) |
| `assistant/` | 3-4 | `phase-3-exit-report.md`, `phase-4-exit-report.md` |
| `apollo/`, `marketing/`, `reporting/` | 3-4 | `phase-3-exit-report.md` |
| `scoping/` | 2-3 | `phase-2-exit-report.md` (models), `phase-3-exit-report.md` |
| `market-intelligence/` | 1-4 (various migrations) | PR bodies + `phase-3-exit-report.md` |
| `grant/` | 1-4 | PR bodies + `phase-4-exit-report.md` |
| `profile/` | 1-3 | PR bodies + `phase-3-exit-report.md` |
| `laborpulse/` | LaborPulse | `laborpulse-exit-report.md`, `docs/laborpulse.md` |

### `infra/`

| Artifact | Phase | Doc |
|---|---|---|
| `edge/nginx/wfdos-platform.conf` | 5 | `phase-5-exit-report.md` |
| `nginx/wfd-os.conf` (legacy single-tenant) | pre-refactor | `infra/nginx/README.md` |

### `scripts/smoke/`

Cross-platform Python smoke scripts referenced from every §N in
`phase-5-exit-report.md`. Organized by phase/feature:

| Subdir          | Scripts                                                      | Exit-report § |
|-----------------|---------------------------------------------------------------|---------------|
| `bootstrap/`    | `imports.py`, `pytest.py`, `healthchecks.py`                  | §0, §1, §2    |
| `errors/`       | `validation_envelope.py`, `not_found_envelope.py`             | §3            |
| `auth/`         | `login.py`, `me.py`, `tier_readonly_rejects_unauth.py`, `stripped_env_503.py` | §4–§6 |
| `tenancy/`      | `host_tenant.py`                                              | §7            |
| `agent/`        | `echo.py`                                                     | §9            |
| `edge/`         | `nginx_t.py`                                                  | §10           |
| `cta/`          | `contract_urls.py`                                            | §11           |
| `laborpulse/`   | `health.py`, `mock_query.py`, `feedback.py`, `jie_503.py`     | §13           |

Conventions: `scripts/smoke/README.md`.
Shared helpers: `scripts/smoke/_common.py` (`ok`/`fail`/`skip`/`build_parser`).

### `portal/student/`

| Artifact | Phase | Doc |
|---|---|---|
| `app/` (Next.js 16 + React 19) | pre-refactor + LaborPulse additions | `laborpulse-exit-report.md` for `app/laborpulse/` |

### `docker/postgres-init/`

| Artifact | Phase | Doc |
|---|---|---|
| `10-schema.sql` (35+ tables + pgvector + `qa_feedback`) | 2 + LaborPulse | `docs/database/wfdos-schema-inventory.md` |

## Cross-cutting docs

| Doc | Purpose | Phase |
|---|---|---|
| `CLAUDE.md` (repo root) | Project rules — Azure OpenAI default, LLM tier map, DB protection | 1 (llm-provider.mdc rule added pre-refactor) |
| `docs/ops/credential-rotation.md` | 13-credential rotation runbook + 1Password store decision | 4 |
| `docs/white-label-config.md` | Onboarding a new tenant + BrandConfig schema + role ladder | 5 |
| `docs/laborpulse.md` | LaborPulse architecture + mock mode + role model + qa_feedback schema | LaborPulse |
| `docs/laborpulse-backend-handoff.md` | JIE backend-team contract (short-term) + chat-widget evolution + entitlement/billing layer (long-term) | LaborPulse |
| `docs/database/jie-wfdos-schema-reconciliation.md` | Shared-Postgres plan + port-3000 conflict fix + flatten `dbo.*` → `public.*` recommendation | LaborPulse (deferred) |
| `docs/public-url-contract.md` | Stable URLs marketing CTAs depend on + 90-day deprecation policy | 5 |
| `docs/config/identity-migration.md` | CFA → Waifinder identity override inventory | 1 |
| `docs/database/wfdos-schema-inventory.md` | 35-table canonical schema + per-table status | 2 |
| `docs/refactor/issue-29-migration.md` | Structured error envelope migration pattern | 3 |
| `scripts/smoke/README.md` | Conventions for the 16 Python smoke scripts (cross-platform, argparse, OK:/FAIL:/SKIP: exit semantics) | cross-cutting (used by every phase exit report) |

## Bug-trace shortcuts

| When debugging | Load these files |
|---|---|
| Magic-link email doesn't arrive | `phase-4-exit-report.md` §#24 + `docs/ops/credential-rotation.md` §1-2 (Azure AD + Graph) |
| 401 on every auth'd endpoint after login | `phase-4-exit-report.md` §#24 + `phase-5-exit-report.md` §13.7 (cookie domain mismatch) |
| Wrong role returned on `/auth/me` | `phase-4-exit-report.md` §#24 + `docs/laborpulse.md` §"Roles + auth" + `docs/white-label-config.md` §"Workforce-development role" |
| Tenant resolution misfire (wrong Brand rendered) | `phase-5-exit-report.md` §#16 + `docs/white-label-config.md` |
| LaborPulse answers wrong / mock-mode accidentally running in prod | `laborpulse-exit-report.md` + `docs/laborpulse.md` §"Mock mode" |
| LaborPulse 503 `upstream: jie` | `docs/laborpulse.md` §"JIE-side dependency" + check `JIE_BASE_URL` |
| `qa_feedback` row missing tenant/role | `docs/laborpulse.md` §"qa_feedback table" + `phase-5-exit-report.md` §#16 (TenantResolutionMiddleware) |
| Structured error envelope missing `request_id` | `phase-3-exit-report.md` §#23 (RequestContextMiddleware) + `issue-29-migration.md` |
| Tier decorator 503 under stripped env | `phase-4-exit-report.md` §#25 + `wfdos_common/auth/tiers.py::_require_llm_available` |
| nginx proxy returning 504 mid-request | `phase-5-exit-report.md` §#30 + `infra/edge/nginx/wfdos-platform.conf` (`proxy_read_timeout`) |
| Azure Postgres password rotation in progress | `docs/ops/credential-rotation.md` §7-8 |

## Mark-complete convention

A phase moves to ✅ COMPLETE in this table AND in the top-level phase
table of the plan file (`~/.claude/plans/wild-splashing-cascade.md`)
in the same PR that merges the last exit-gate branch for that phase.

Status changes are one-line plan-file edits — not long rewrites —
because the content lives in the per-phase MD.

## Load policy for future sessions

- **Always load:** this file + the plan file.
- **Load on demand** (follow links above): specific phase exit
  reports, cross-cutting docs.
- **Never load eagerly:** all exit reports + all docs. Defeats the
  purpose of indexing.

## Updating this index

When you add a new module, phase, or cross-cutting doc, update:

1. The phase table (if it's a new phase).
2. The module → phase map (if it's a new module).
3. The cross-cutting docs table (if it's a new ops/white-label/etc
   doc).
4. The bug-trace shortcuts if the new artifact introduces a new
   failure mode.

Keep this file under ~300 lines — it's a map, not a manual.
