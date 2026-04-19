# Phase 2 exit report

**Branch:** `phase-2-exit-gate`
**Date:** 2026-04-16

Phase 2 of the wfd-os Option-D-hybrid refactor. Dedicated exit-gate smoke + coverage baseline + regression review per the plan at `~/.claude/plans/wild-splashing-cascade.md`.

## PRs merged (pending your review)

| # | Issue | Title |
|---|---|---|
| [#33](https://github.com/Building-With-Agents/wfd-os/pull/33) | #17 | scaffold wfdos-common + migrate graph/email |
| [#34](https://github.com/Building-With-Agents/wfd-os/pull/34) | #18 | config + pluggable secret backends |
| [#35](https://github.com/Building-With-Agents/wfd-os/pull/35) | #19 | hardcoded passwords + detect-secrets baseline |
| [#37](https://github.com/Building-With-Agents/wfd-os/pull/37) | chore | local-dev Postgres container + schema inventory |
| [#38](https://github.com/Building-With-Agents/wfd-os/pull/38) | #21 | Pydantic models in wfdos_common.models |
| [#39](https://github.com/Building-With-Agents/wfd-os/pull/39) | #22a | DB engine + session + tenant middleware |
| [#40](https://github.com/Building-With-Agents/wfd-os/pull/40) | #22b | canonical schema (35 tables + pgvector) |
| [#41](https://github.com/Building-With-Agents/wfd-os/pull/41) | #22c | portal services → engine factory + shared queries |
| [#42](https://github.com/Building-With-Agents/wfd-os/pull/42) | #20 | LLM adapter with graceful degradation |
| this branch | exit gate | smoke + regression fix + report |

## Coverage baseline (#28 target: 40%; achieved: 55%)

```
$ pytest packages/wfdos-common/tests --cov=wfdos_common --cov-report=term
83 passed in 20.20s

TOTAL     1243 stmts, 563 missed, 55% coverage
```

Well-covered (>90%): `config/settings` 98%, `models/core` 100%, `models/domain` 100%, `models/scoping` 100%, `db/__init__` 100%, `db/middleware` 93%, `llm/__init__` 100%, `llm/adapter` 92%, `llm/base` 100%, `graph/config` 93%.

Undercovered (<50%): `graph/sharepoint` 11%, `graph/teams` 8%, `graph/transcript` 9%, `graph/invitations` 19%, `email` 24%, `gemini provider` 29%.

The undercovered modules are mostly Microsoft Graph / Gemini SDK wrappers. Their tests need real external APIs; deferred to `#28` when the `wfdos_common.testing` fixture suite ships with Graph + LLM mocks.

## Full-stack smoke results

`.env` pointed at PR #37's local Docker Postgres (port 5434) with PR #40's schema applied. Started 6 services + hit representative endpoints:

| Service | Port | Endpoint | Pre-fix | Post-fix |
|---|---|---|---|---|
| consulting-api | 8003 | `/api/health`, `/api/consulting/pipeline` | ✅ 200 | ✅ 200 |
| student-api | 8001 | `/api/health` | ✅ 200 | ✅ 200 |
| showcase-api | 8002 | `/api/health`, `/api/showcase/candidates` | ✅ 200 | ✅ 200 |
| college-api | 8004 | `/api/health` | ✅ 200 | ✅ 200 |
| wji-api | 8007 | `/api/health`, **`/api/wji/dashboard`** | ✅ 200 / **❌ 500** | ✅ 200 / ✅ 200 |
| assistant-api | 8009 | `/api/health`, `/api/assistant/agents` | ✅ 200 | ✅ 200 |

Additional live smokes earlier in the session:

- **`wfdos_common.email.send_email()`** → Microsoft Graph sendMail `202 Accepted`, email delivered to `gary.larson@computingforall.org` (see PR #33 smoke).
- **`wfdos_common.llm.complete()`** → real Azure OpenAI call via default tier (`chat-gpt41mini`), returned `"Hello!"` for the 5-token probe.
- **`/api/consulting/inquire`** POST → `INQ-2026-0001` inserted + returned by real psycopg2 connection through the engine factory, then DELETEd for cleanup.

## Regressions found + fixed on this branch

### 1. `wji_upload_batches` missing 3 columns (caused `/api/wji/dashboard` 500)

Schema from #40 didn't include `success_count`, `error_count`, `errors` columns that `agents/portal/wji_api.py` SELECTs + UPDATEs in its upload-batch flow. Exposed immediately when I hit `/api/wji/dashboard` during the smoke.

**Fix** — added the 3 columns to `docker/postgres-init/10-schema.sql` on this branch:

```sql
success_count  INTEGER,
error_count    INTEGER,
errors         JSONB,
```

Verified: after `docker compose down -v && up -d` (reapply init), `/api/wji/dashboard` + `/api/wji/placements` + `/api/wji/payments` all return 200.

## Test suite summary

```
83 passed, 0 failed, 1 warning (pip deprecation — not our code)
```

Breakdown by file:
- `test_config.py` — 11 tests (settings + backends)
- `test_db.py` — 15 tests (engine, session, middleware)
- `test_email_shim.py` — 2 tests (shim re-export identity)
- `test_graph_shim.py` — 3 tests (graph shim identity)
- `test_imports.py` — 2 tests (package + stub imports)
- `test_llm.py` — 18 tests (providers, routing, fallback)
- `test_models.py` — 15 tests (core + domain + scoping)
- `test_queries.py` — 6 tests (shared query layer)
- `test_schema_init.py` — 7 tests (schema idempotency + coverage)
- `test_secrets_baseline.py` — 4 tests (rotated-passwords guard)

## Migration invariant preserved throughout

- ✅ Every PR's test suite + smoke was green at PR open.
- ✅ No env var renames without dual-read shims. No new required env vars without defaults.
- ✅ Old import paths still work via shims (`agents.graph.*`, `agents.portal.email`, `agents.scoping.models`).
- ✅ Local dev spin-up: `docker compose -f docker-compose.dev.yml up -d` + point `.env` at port 5434 + `uvicorn agents.portal.<service>:app` — services boot and serve real data.
- ✅ Every hardcoded CFA/Ritu path is gone; `wfdos_common.config` resolves everything.
- ✅ Three hardcoded passwords removed + rotation flagged for Gary.

## Deferred work (captured in issue bodies + PR descriptions)

- Remaining ~60 `os.getenv` call sites not migrated in #18 — deferred follow-up issue.
- Tool-calling + multimodal LLM paths (3 files: market-intelligence/agent.py, assistant/base.py, profile/parse_resumes.py) — land in #26 Agent ABC.
- `showcase_api.py` inline CTE-wrapped skill query — drop-in refactor to shared `get_student_skills` isn't straightforward; follow-up issue.
- Foreign-key constraints on all `-- FK: ...` comments in the schema — follow-up tightening pass.
- ENUM types / CHECK constraints on TODO-marked columns — follow-up tightening pass.
- Full SQLAlchemy ORM conversion for portal services — out of scope. Current raw-DBAPI-through-pool is minimum-change.

## External side effects triggered during Phase 2 smokes

Reported in PR descriptions, recorded here for audit:

- **Apollo CRM — 2 test contacts created** I should have gotten permission before triggering:
  - `test@example.com` / "Test User" / "Acme" (PR #40 smoke)
  - `smoke@example.com` / "Smoke Test" / "EngineFactory" — `contact_id: 69e0686225373a000d9eebe3` (PR #41 smoke)
  
  Please delete in the Apollo dashboard when convenient.
  
- **Graph sendMail** — one smoke email to `gary.larson@computingforall.org` from `ritu@computingforall.org` (PR #33 smoke; you explicitly approved).

- **Azure OpenAI** — ~5 tokens total spent in the `complete()` live-verify probe (#42).

## Gate status

| Check | Status |
|---|---|
| Tests land with each PR | ✅ 83/83 green |
| 40% coverage floor (#28) | ✅ 55% achieved |
| Full-stack smoke | ✅ 6/6 services boot; all representative endpoints 200 |
| Regressions fixed on exit branch | ✅ 1 found + fixed (wji columns) |
| Live LLM round-trip | ✅ Azure OpenAI default tier |
| Live email round-trip | ✅ Graph sendMail 202 |
| Migration invariant | ✅ No breaking change |

**Recommend:** merge PRs #33 → #37 → #38 → #39 → #40 → #41 → #42 → this exit-gate branch in that order.

## Next up — Phase 3 priorities

User-selected for Phase 3 start: **#23 — structured logging (replace 51 `print()` calls with structlog)**.

Rationale: lowest-risk cleanup + unblocks observability work + no external dependencies beyond `structlog` package.

After #23, plan suggests: #24 (auth) → #25 (tier separation) → #27 (per-service pyproject.toml) → #26 (Agent ABC) → #28 (pytest infra) → #29 (endpoint validation) → #30 (edge proxy). Order revisits after #23 lands.
