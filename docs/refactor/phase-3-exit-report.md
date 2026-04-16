# Phase 3 exit report — observability + packaging + endpoint validation

**Branch:** `phase-3-exit-gate` (stacked on `issue-29-endpoint-validation` →
`issue-27-per-service-packaging` → `issue-28-wfdos-common-testing` →
`issue-23-wfdos-common-logging` → `phase-2-exit-gate`).

**Scope delivered (4 issues, 4 PRs, all stacked):**

| # | Issue | Branch | PR | Status |
|---|---|---|---|---|
| 1 | #23 — structured logging | `issue-23-wfdos-common-logging` | #44 | ✅ |
| 2 | #28 — pytest fixtures plugin | `issue-28-wfdos-common-testing` | #45 | ✅ |
| 3 | #27 — per-service pyproject + sys.path elimination | `issue-27-per-service-packaging` | #46 | ✅ |
| 4 | #29 — structured error envelope + typed exceptions | `issue-29-endpoint-validation` | #47 | ✅ |

None of these have been merged to `master` per Gary's stacked-branch
strategy — they stack on each other, and the overall refactor merges
as a unit at the Phase-5 exit gate.

## Test + coverage snapshot

| Baseline (Phase 2 exit) | Phase 3 exit |
|---|---|
| 83 tests passing | **172 tests passing** |
| 55% coverage | **59.83% coverage** |
| Coverage floor: 50% | Coverage floor: 50% (Phase 4 target: 60%, Phase 5: 70%) |

Growth by issue:

| After | Tests | Coverage |
|---|---|---|
| #23 | 97 (+14 logging) | 54% |
| #28 | 112 (+14 fixtures plugin) | 56.93% |
| #27 | 140 (+28 pg_config + agent imports) | 57.75% |
| #29 | 172 (+32 errors + service envelopes) | 59.83% |

## Acceptance-criteria deltas

### #23 — structured logging

- **`wfdos_common.logging`** module with `configure(service_name, log_format, log_level)`,
  ContextVars for `tenant_id`/`user_id`/`request_id`/`service_name`, and
  `RequestContextMiddleware` that reads or generates `X-Request-Id` and
  echoes it in the response header.
- **Bare `except:` across `agents/`: 0** (baseline 13). All replaced with
  typed `except Exception:` + structured error logs.
- **`print()` migration in priority dirs:**
  - `agents/portal/`: **0** (baseline ~5) ✅
  - `agents/scoping/pipeline.py`: 0 (was 26); other scoping modules have
    22 prints remaining — incremental cleanup (not in #23 scope per plan
    prioritization).
  - `agents/market-intelligence/ingest/runner.py`: 34 prints remain;
    runner is CLI-shaped (progress output to stdout). Plan explicitly
    listed only 3 print() sites for this dir — the 34 are long-tail
    operator-facing output not intended as structured logs.

### #28 — pytest fixtures plugin (`wfdos_common.testing`)

- Pytest plugin registered via `[project.entry-points.pytest11]` in
  `wfdos-common/pyproject.toml`, so every consumer that `pip install -e
  packages/wfdos-common` gets the fixtures automatically with zero
  `conftest.py` wiring.
- Fixtures shipped: `wfdos_tenant_id`, `wfdos_db_engine`, `wfdos_db_session`,
  `wfdos_llm_stub`, `wfdos_graph_stub`, `wfdos_auth_client`,
  `reset_wfdos_logging` (autouse).
- 14 meta-tests in `test_testing_plugin.py` lock the fixture contracts so
  future regressions are caught.
- CI coverage floor bumped with `--cov-fail-under=50` in `.github/workflows/ci.yml`.

### #27 — per-service pyproject + sys.path elimination

- **Root `pyproject.toml`** declares `wfdos-monorepo` with `agents*` as
  the namespace package. `pip install -e .` at repo root resolves every
  `agents.X.Y` import with zero runtime sys.path manipulation.
- **9 per-service `pyproject.toml` files** — `apollo`, `assistant`,
  `grant`, `market-intelligence`, `marketing`, `portal`, `profile`,
  `reporting`, `scoping`. Each declares service-specific runtime deps
  for deployment isolation.
- **`sys.path.insert` call sites in agents/ *.py: 27 → 3** (the 3
  remaining are in the dashed `agents/market-intelligence/` folder which
  can't be a Python package by that name; tracked in its pyproject.toml
  for a future rename).
- **`from pgconfig import` in agents/ *.py: 17 → 0**. Replaced with
  `from wfdos_common.config import PG_CONFIG` via a new lazy
  `_PgConfigDict` shim in `wfdos_common.config.pg_config`.
- `ruff --fix --select F401` cleaned up 45 unused imports unblocked by
  the sys.path removal.

### #29 — structured error envelope + typed exceptions

- **`wfdos_common.errors`** module with `APIError` base + 6 typed
  subclasses (`NotFoundError`, `ValidationFailure`, `ConflictError`,
  `UnauthorizedError`, `ForbiddenError`, `ServiceUnavailableError`) +
  `install_error_handlers(app)` wiring three FastAPI handlers (APIError,
  RequestValidationError, bare Exception).
- **9/9 FastAPI services** wired to the handlers + `RequestContextMiddleware`.
- **`raise HTTPException(...)` in agents/portal + agents/marketing +
  agents/apollo: 18 → 0** ✅
- **`X-Request-Id` echo** — every `error.details.request_id` populated
  automatically from `RequestContextMiddleware` context, so clients can
  quote it when filing a bug.
- **`except Exception` in portal/marketing/apollo: 27** (from 21 at
  baseline — the net went _up_ slightly because I converted a handful of
  `raise HTTPException(400, ...)` patterns into `except Exception as e:
  raise ValidationFailure(...)` to preserve the typed-error story. These
  are now structured: exception type is logged with the stack trace, and
  the client sees the standard envelope. The pure-broad `except
  Exception: pass` anti-pattern stays at zero).

## What's deferred (follow-up tickets)

| Ref | Scope | Why deferred |
|---|---|---|
| scoping prints | 22 `print()` calls in scoping/* outside pipeline.py | Plan only prioritized `pipeline.py`; others are test runners + one-off scripts |
| ingest runner prints | 34 `print()` calls in market-intelligence/ingest/runner.py | Runner is a CLI; stdout output is its primary UX |
| response_model= on 55 routes | Hand-built Pydantic shapes for every service route | `RealDictCursor` output needs per-route field ordering; 2-3 follow-up PRs (per-service) |
| broad `except Exception:` in 4 services | 27 remaining sites | Unhandled-exception handler now catches them with the structured envelope — incremental cleanup |
| market-intelligence dash→underscore rename | Folder rename eliminates the 3 remaining sys.path.insert | Bigger blast radius than #27 wanted to take; good standalone PR |

## Smoke-test plan for Gary at PR review

Since I can't run the full stack locally (requires `.env` secrets +
Docker Postgres), the following smoke tests are owed before Phase 3 merges:

```bash
# 1. Install stack
pip install -e packages/wfdos-common
pip install -e .

# 2. Run wfdos-common test suite
pytest packages/wfdos-common/tests --cov=wfdos_common --cov-fail-under=50
# expected: 172 passed, coverage >= 50%

# 3. Boot the stack via honcho (expects .env)
docker compose -f docker-compose.dev.yml up -d
honcho start

# 4. Hit representative endpoints and confirm structured envelopes
curl -s localhost:8003/api/consulting/inquire -X POST \
     -H "Content-Type: application/json" -d '{}' | jq
# expect: {"data": null, "error": {"code": "validation_error", ...}, "meta": null}

curl -s -D - localhost:8001/api/student/does-not-exist/profile | jq
# expect: 404 with {"data": null, "error": {"code": "not_found", ...}}
# and     X-Request-Id header present

# 5. Unknown-route envelope smoke
curl -s -H "X-Request-Id: test-42" localhost:8003/does-not-exist | jq .error
# expect: error body contains "request_id": "test-42"
```

## Regression triage

None surfaced during the Phase-3 work. The only bug-like behavior I
observed was ruff auto-removing a `import sys` from
`agents/profile/parse_resumes.py` that was still used by `sys.argv` at
line 260 — caught by ruff's `F821` check in the same pass and fixed in
the #27 branch before PR.

## Sign-off

- Full suite green: **172 passed, 0 failed, 59.83% coverage** (above the
  50% floor; trending towards the 60% Phase-4 target).
- All 9 FastAPI services import from a pristine sys.path.
- All 9 FastAPI services produce the structured error envelope on 4xx/5xx.
- 4 stacked PRs open (#44, #45, #46, #47); base chain established per
  the stacked-branch strategy.
- Deferred work documented above + in `docs/refactor/issue-29-migration.md`.

**Next:** Phase 4 kick-off on a new branch `issue-24-wfdos-common-auth`
stacked on `phase-3-exit-gate` (once Gary reviews this report).
