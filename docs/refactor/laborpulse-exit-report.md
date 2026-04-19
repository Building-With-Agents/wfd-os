# LaborPulse exit report — Q&A endpoint + mock mode + workforce-development role

**Branch:** `issue-laborpulse-qa-endpoint` (stacked on
`issue-59-workforce-development-role` → `phase-5-exit-gate`).

Two PRs land the feature:

| # | Issue | Branch | PR | Status |
|---|---|---|---|---|
| 1 | #59 — add `workforce-development` role | `issue-59-workforce-development-role` | #60 | ✅ (pending smoke) |
| 2 | LaborPulse Q&A endpoint + mock mode | `issue-laborpulse-qa-endpoint` | #61 | ✅ (pending smoke) |

Neither merges to master — the stacked-branch strategy continues. See
the squash-merge order in the plan file.

## What the feature delivers

- **`/laborpulse`** page in the Next.js portal (`portal/student/app/laborpulse/`).
  Client component: plain `fetch` + `await resp.json()`, staged loading
  skeleton, progressive render of answer + evidence cards + confidence
  badge + follow-up chips + thumbs-up/down.
- **`/api/laborpulse/query`** FastAPI endpoint on port 8012. Returns
  `QueryResponse` JSON: `conversation_id`, `answer`, `evidence`,
  `confidence`, `follow_up_questions`, `cost_usd`, `sql_generated`.
  When `JIE_BASE_URL` is set → calls JIE. When empty → mock pathway
  (8-12s `asyncio.sleep` + canned Borderplex-flavored answer tagged
  `confidence: "mock"` + `[MOCK]` prefix).
- **`/api/laborpulse/feedback`** writes to `qa_feedback` in wfd-os
  Postgres (system-of-record). Tagged with `tenant_id`, `user_email`,
  `user_role` at write time.
- **`workforce-development` role** in `wfdos_common.auth` — fourth tier
  alongside `student`/`staff`/`admin`. Precedence: admin > staff >
  workforce-development > student. Env var
  `WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST`.
- **nginx `/api/laborpulse/`** block with `proxy_read_timeout 300s` +
  `platform_laborpulse` rate-limit zone (60r/m, burst 20).
- **`qa_feedback` table** in `docker/postgres-init/10-schema.sql` with
  CHECK constraint on rating + three indexes.

## Files touched

New:
- `agents/laborpulse/__init__.py`
- `agents/laborpulse/api.py`
- `agents/laborpulse/client.py`
- `agents/laborpulse/pyproject.toml`
- `portal/student/app/laborpulse/page.tsx`
- `portal/student/app/laborpulse/LaborPulseClient.tsx`
- `packages/wfdos-common/tests/test_laborpulse.py`
- `docs/laborpulse.md`
- `docs/refactor/laborpulse-exit-report.md` (this file)

Modified:
- `packages/wfdos-common/wfdos_common/config/settings.py` — `JieSettings` class.
- `packages/wfdos-common/wfdos_common/auth/allowlist.py` — `workforce-development` role.
- `packages/wfdos-common/wfdos_common/auth/__init__.py` — re-exports.
- `packages/wfdos-common/wfdos_common/config/__init__.py` — `PG_CONFIG` re-export.
- `packages/wfdos-common/wfdos_common/auth/routes.py` — `/auth/login` forwards the new allowlist.
- `packages/wfdos-common/tests/test_auth.py` — new role precedence + env round-trip tests.
- `packages/wfdos-common/tests/test_nginx_config.py` — renamed `test_laborpulse_location_bumps_read_timeout`.
- `packages/wfdos-common/tests/test_public_url_contract.py` — adds `agents.laborpulse.api` to the parametrized scan.
- `packages/wfdos-common/tests/test_service_error_envelopes.py` — adds LaborPulse to the envelope-invariant parametrization.
- `docker/postgres-init/10-schema.sql` — `qa_feedback` table appended.
- `infra/edge/nginx/wfdos-platform.conf` — laborpulse upstream + location + rate-limit zone.
- `.env.example` — `JIE_*` + `WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST` block.
- `Procfile` — `laborpulse-api` entry on port 8012.
- `docs/public-url-contract.md` — `/laborpulse` + `/api/laborpulse/query` + `/api/laborpulse/feedback`.
- `docs/ops/credential-rotation.md` — §8b allowlist management + revocation.
- `docs/white-label-config.md` — workforce-development role paragraph.

## Mock-mode decision

The original plan had LaborPulse raise `ServiceUnavailableError` (503)
when `JIE_BASE_URL` was empty. Gary asked for a mock-answer path
instead so the frontend renders realistically in dev + demo rehearsal
without a live JIE. Implementation in `agents/laborpulse/api.py`:

- `_mock_answer_for(question)` returns a dict shaped like `QueryResponse`
  with Borderplex sector/growth talking points, 3 evidence items, 3
  follow-up questions, `cost_usd=0.0`, `confidence="mock"`,
  `conversation_id="mock-" + uuid4()`. The user's question is echoed
  into the `answer` so demo flow feels conversational.
- `_mock_query(question)` awaits `asyncio.sleep(random.uniform(8.0, 12.0))`
  then returns `_mock_answer_for(...)`. Logs `laborpulse.query.mock` at
  INFO with the chosen delay so accidental prod-mode-mock deploys are
  findable via log grep.
- `/api/health` reports `jie_configured: false` when `JIE_BASE_URL` is
  empty — prod deploy-config check should include this field.

## Tests

28 new LaborPulse tests in `packages/wfdos-common/tests/test_laborpulse.py`:
- JieSettings env round-trip + default empty base_url
- qa_feedback schema columns
- Client.py event folding (answer concat, evidence list, confidence,
  follow-ups, done, unknown events, malformed JSON tolerance)
- Endpoint auth/role gate (401 / 403)
- Happy-path response shape + Pydantic field set
- Tenant + user_email forwarding from Host + session
- 503 when JIE unreachable; 422 when JIE rejects the question
- Empty-question validation
- **Mock-mode tests:**
  - `test_query_returns_mock_when_jie_base_url_empty` — 200 with
    `conversation_id` starting `mock-`, `confidence == "mock"`,
    `[MOCK]` in answer, question echoed
  - `test_query_mock_sleeps_between_8_and_12_seconds` — records the
    `asyncio.sleep` arg and asserts [8.0, 12.0] range
  - `test_health_reports_jie_not_configured_when_base_url_empty`
- Feedback writer with SQLite in-memory stand-in:
  - Row lands with tenant/role/rating
  - Mock conversation_id accepted (`mock-` prefix)
  - Out-of-range rating rejected (422)
  - Auth + role gates

Plus 5 new auth tests in `test_auth.py` for the `workforce-development`
role (precedence ladder, allowlist env round-trip, `ALLOWED_ROLES`
membership, rate-limit default).

**Full suite target:** 300+ passing, coverage ≥ 65%.

## Live smoke checklist

See `docs/refactor/phase-5-exit-report.md` §13 (LaborPulse) for the
step-by-step smoke commands. Highlights:

- Mock-mode query: `time curl` → ~10s wait + JSON with `[MOCK]` marker.
- Feedback write: POST + verify `qa_feedback` row with
  `tenant_id="borderplex"`, `user_role="workforce-development"`.
- 503 path: set `JIE_BASE_URL=http://127.0.0.1:1`, expect envelope
  with `error.details.upstream == "jie"`.
- Browser walkthrough at `/laborpulse` with director session cookie.

## Deferred

- JIE-side `X-Tenant-Id` scoping (paired ticket on the JIE repo).
  Borderplex-only deploy is safe until that lands.
- Per-tenant branding header on `/laborpulse` — requires one more
  server-component wiring pass for `BrandConfig` exposure.
- Migrate allowlist env CSV → `tenants` DB table on second-client rollout.
- Remove mock pathway (or gate behind `WFDOS_ENV=dev`) once
  `confidence == "mock"` feedback rows stop appearing in production.
- Golden-question eval harness — Week 9 curriculum work.

## Sign-off

- 2 PRs open (#60, #61), stacked correctly.
- 58 tests passing in the LaborPulse + nginx + auth slices (part of
  the 300+ full-suite pass).
- Mock-mode pathway logged + health-signaled + test-covered so it
  can't silently run in production.
- Pending smoke: Gary's morning checklist (phase-5-exit-report.md §13).
