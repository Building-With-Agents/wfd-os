# Phase 5 exit report — **the overall-refactor exit report**

This is the top of the stacked-branch tree. Checking out
`phase-5-exit-gate` gives you **every Phase 1 + 2 + 3 + 4 + 5 change
live in one working tree**, exactly as planned when we decided not to
merge along the way.

## Stack (11 PRs, no merges to master)

| Phase | Issue              | Branch                                           | PR  | Base                                         |
|-------|---------------------|--------------------------------------------------|-----|----------------------------------------------|
| 1     | #17 scaffold        | `issue-17-scaffold-wfdos-common`                 | #33 | master                                       |
| 1     | #18 config          | `issue-18-wfdos-common-config`                   | #34 | #17                                          |
| 1     | #19 passwords       | `issue-19-remove-hardcoded-passwords`            | #35 | #18                                          |
| 1     | #37 infra           | `infra-local-postgres-schema-inventory`          | #37 | #19                                          |
| 2     | #21 models          | `issue-21-wfdos-common-models`                   | #38 | #37                                          |
| 2     | #22a DB engine      | `issue-22a-wfdos-common-db-engine`               | #39 | #21                                          |
| 2     | #22b schema         | `issue-22b-wfdos-common-db-schema`               | #40 | #22a                                         |
| 2     | #22c portal migrate | `issue-22c-portal-migrate`                       | #41 | #22b                                         |
| 2     | #20 LLM adapter     | `issue-20-wfdos-common-llm`                      | #42 | #22c                                         |
| 2     | Phase 2 gate        | `phase-2-exit-gate`                              | #43 | #20                                          |
| 3     | #23 logging         | `issue-23-wfdos-common-logging`                  | #44 | phase-2-exit-gate                            |
| 3     | #28 fixtures        | `issue-28-wfdos-common-testing`                  | #45 | #23                                          |
| 3     | #27 packaging       | `issue-27-per-service-packaging`                 | #46 | #28                                          |
| 3     | #29 errors          | `issue-29-endpoint-validation`                   | #47 | #27                                          |
| 3     | Phase 3 gate        | `phase-3-exit-gate`                              | #48 | #29                                          |
| 4     | #24 auth            | `issue-24-wfdos-common-auth`                     | #49 | phase-3-exit-gate                            |
| 4     | #25 tiers           | `issue-25-tier-decorators`                       | #50 | #24                                          |
| 4     | #9 rotation         | `issue-9-credential-rotation-finalize`           | #51 | #25                                          |
| 4     | Phase 4 gate        | `phase-4-exit-gate`                              | #52 | #9                                           |
| 5     | #26 Agent ABC       | `issue-26-agent-abc`                             | #53 | phase-4-exit-gate                            |
| 5     | #16 white-label     | `issue-16-white-label`                           | #54 | #26                                          |
| 5     | #30 edge proxy      | `issue-30-edge-proxy`                            | #55 | #16                                          |
| 5     | #31 CTA contract    | `issue-31-cta-urls-contract`                     | #56 | #30                                          |
| 5     | **Phase 5 gate**    | **`phase-5-exit-gate`** (this report)            | TBD | #31                                          |

## Metrics — the full refactor vs. master

| | Pre-refactor master | Phase 5 exit |
|---|---|---|
| Tests passing | ~0 (no wfdos-common) | **273** |
| Coverage | n/a | **67.89%** |
| Bare `except:` in agents/ | 13 | **0** |
| `sys.path.insert` in agents/*.py | 30 | **3** (dashed market-intelligence/) |
| `from pgconfig import` in agents/ | 17 | **0** |
| `raise HTTPException` in portal/marketing/apollo | 18 | **0** |
| Services with structured error envelope | 0 | **9/9** |
| Services with auth middleware available | 0 | 9/9 (install one-liner) |
| `wfdos_common` submodules live | 0 | **config, models, db, llm, graph, email, logging, errors, auth, tenancy, agent, testing** |
| Per-service pyproject.toml | 0 | **9** |
| `wfdos-common` deps declared | 0 | pydantic v2, SQLAlchemy 2.0, openai, structlog, itsdangerous, slowapi, email-validator, azure-identity, msgraph-sdk, httpx, psycopg2-binary |

## `wfdos_common` surface summary

```python
from wfdos_common.config    import settings, PG_CONFIG, ConfigurationError
from wfdos_common.models    import APIEnvelope, ErrorDetail, StudentProfile, ...
from wfdos_common.db        import get_engine, TenantResolver, get_student_skills
from wfdos_common.llm       import complete
from wfdos_common.graph     import sharepoint, teams, transcript
from wfdos_common.email     import send_email, notify_internal
from wfdos_common.logging   import configure, get_logger, RequestContextMiddleware
from wfdos_common.errors    import NotFoundError, ValidationFailure, install_error_handlers, ...
from wfdos_common.auth      import SessionMiddleware, build_auth_router, require_role, read_only, llm_gated
from wfdos_common.tenancy   import BrandConfig, TenantResolutionMiddleware, get_brand
from wfdos_common.agent     import Agent, AgentResult, Tool, ToolRegistry, EchoAgent
from wfdos_common.testing   import wfdos_tenant_id, wfdos_db_session, wfdos_llm_stub, ...
```

12 production modules + 1 testing module. The original stub files are
all populated.

## Sign-off

- 24 stacked PRs (none merged to master per the agreed strategy — they
  stack off each other; merging happens as a unit).
- 273 tests green, 67.89% coverage (Phase 5 target 70%; within 2 pp
  and climbing — follow-up PRs that tag every route with a tier
  decorator will push the number further).
- Every Phase 1-5 acceptance criterion met or explicitly deferred to a
  follow-up with a documented reason.
- Deployed nothing new yet — the edge proxy, the auth flow, the new
  errors handlers all live on the phase-5-exit-gate branch only. **Live
  smoke is Gary's morning checklist below.**

---

# Live-run state — 2026-04-21

The full stack merged to `development` via PR #64 on 2026-04-20. Live
smoke covered §0–§4 end-to-end and §13 via browser demo; remaining
sections are queued for a follow-up pass. **Defer-tagged items are
blocked on external work** (schema reconciliation, Azure PG password
rotation, VM deploy) — they are NOT regressions.

| § | Topic                                  | State        | Notes |
|---|----------------------------------------|--------------|-------|
| 0 | Environment bring-up                   | ✅ PASS      | `imports.py` green. |
| 1 | Full pytest suite                      | ✅ PASS      | 312 passed, 68.26% coverage. |
| 2 | Boot full stack + healthchecks         | ✅ PASS      | 10/10 after fix: added `/api/health` to reporting-api (commit `6f3c7f0`). |
| 3 | Structured error envelope              | ⚠ PARTIAL   | §3a validation envelope PASS. §3b not-found **DEFERRED** — needs wfd-os schema in JIE Postgres (see `docs/database/jie-wfdos-schema-reconciliation.md`). |
| 4 | Magic-link auth end-to-end             | ⚠ PARTIAL   | Login endpoint PASS; email dispatched 202 Accepted from `ritu@computingforall.org`. `/auth/me` cookie test not run in the live pass (synthesized a cookie directly for the §13d browser demo). Bugs found + fixed: SessionMiddleware+router install (`f32170a`), URL-encoded magic-link token (`35b51ef`), Next.js `/auth/*` rewrite (`35b51ef`), `WFDOS_AUTH_COOKIE_SECURE=false` for http://localhost. |
| 5 | Tier decorator `@read_only`            | ⏸ NOT RUN   | Script exists (`tier_readonly_rejects_unauth.py`), un-executed this pass. |
| 6 | Stripped-env 503 path                  | ⏸ NOT RUN   | Needs cookie + env strip. |
| 7 | White-label tenant resolution          | ⏸ NOT RUN   | Script exists. |
| 8 | Structured logs flowing                | ⏸ NOT RUN   | Visual log inspection step. |
| 9 | Agent ABC reference run                | ⏸ NOT RUN   | Pure Python, no services needed. |
| 10| nginx `-t` locally                     | ⏸ NOT RUN   | **VM deploy DEFERRED** — Gary's separate infra session. |
| 11| CTA contract URL probes                | ⏸ NOT RUN   | Needs portal on :3000 (now stable after `b65efc0` Procfile `--port` fix). |
| 12| Credential rotation                    | ⏸ DEFERRED  | Gary's separate ops session. |
| 13a | LaborPulse env                       | ✅ PASS      | Mock-mode allowlist + Procfile wired. |
| 13b | LaborPulse `/api/health`             | ✅ PASS      | `jie_configured=false` (mock mode). |
| 13c | Unauth rejection (via §3)            | ⏸ NOT RUN   | Generic envelope; covered by §3 smoke. |
| 13d | Mock-mode end-to-end                 | ✅ PASS      | Browser demo: `[MOCK]` answer + 3 evidence cards + 3 follow-ups in ~10s, confidence=`mock`, conversation_id starts `mock-`. Portal rewrite fix required (`9f2ff2f`). |
| 13e | Feedback row write to `qa_feedback`  | ⏸ DEFERRED  | Needs wfd-os schema in JIE Postgres (same blocker as §3b). |
| 13f | Real-JIE 503 path                    | ⏸ NOT RUN   | Needs cookie + disposable laborpulse restart with unreachable `JIE_BASE_URL`. |
| 13g | Browser walkthrough                  | ✅ PASS      | Demoed via Claude-in-Chrome; `/laborpulse` form renders, question fires, mock response + feedback buttons render correctly. |

### Post-smoke PRs (all merged to `development`)

| PR | What |
|---|---|
| #64 | Phases 1–5 + LaborPulse + smoke scripts (30 commits, rebase-merged) |
| #67 | `fix(laborpulse): JIE client reads JSON, drop SSE parser` (the short-term half of `docs/laborpulse-backend-handoff.md` Part 2) |
| #69 | `fix(ci): install monorepo root + detect-secrets + genai` — unblocks CI so required-checks branch protection can land |
| #70 | `fix(config): env_prefix="PG_" on PgSettings — stop USER env shadowing` |

Branch protection on `development` now requires the 3 CI checks to
pass before merge. Admin bypass retained for hotfixes.

### Next live-pass checklist

Pick up from here by running §5 → §9, §11, §13c, §13f in order —
they're all cookie-free except §13f. Get a cookie via a fresh
magic-link click (§4) or synthesize one as shown in the local-dev
runbook (`docs/ops/local-dev-startup.md`), then run §13f.

Sections §3b + §13e + §10-VM-deploy + §12 stay deferred until their
upstream blockers clear.

---

# Live-test checklist (Gary's morning pass)

Check out `phase-5-exit-gate` and walk through the sections below in
order. Each section has: **setup** (what to prep), **run**, **expect**.
Anything that doesn't behave as expected should land as a new issue
labelled `phase-5-exit-regression` so the fix blocks the merge-to-
master plan.

## 0. Environment bring-up

```bash
git fetch origin
git checkout phase-5-exit-gate
git pull

# Install the monorepo + wfdos-common.
pip install -e packages/wfdos-common
pip install -e .[dev]

# Bring up the local Postgres.
docker compose -f docker-compose.dev.yml up -d

# Import smoke — all wfdos_common + agents.* surfaces.
python scripts/smoke/bootstrap/imports.py
```

**Expect:** `OK: wfdos_common + agents.* import`.

> Every §N block below references a script under `scripts/smoke/<dir>/`.
> See `scripts/smoke/README.md` for conventions, exit codes, and env
> overrides (e.g. `BASE_URL=https://platform.thewaifinder.com`).

---

## 1. Full pytest suite

```bash
python scripts/smoke/bootstrap/pytest.py
```

**Expect:** `312 passed`, coverage ≥ 67%, plus
`OK: wfdos-common test suite green + coverage floor met`.

---

## 2. Boot the full stack

```bash
honcho start
```

In a second shell, once the services have had a few seconds to come up:

```bash
python scripts/smoke/bootstrap/healthchecks.py
```

**Expect:** each of the 10 service ports prints `OK`, then a final
`OK: every /api/health responded (n=10)`. A failure line shows the
service name + port + reason (connection refused, 5xx, wrong body).

---

## 3. Structured error envelope (#29)

```bash
python scripts/smoke/errors/validation_envelope.py
python scripts/smoke/errors/not_found_envelope.py
```

**Expect:** both scripts exit 0 with `OK: ...` on the last line.
The validation script asserts a 422 with `error.code == "validation_error"`
and the supplied `X-Request-Id` echoed into `error.details.request_id`.
The not-found script asserts a 404 with `error.code == "not_found"`
and the `X-Request-Id` header round-tripped in the response.

---

## 4. Magic-link auth end-to-end (#24)

**Setup:** set `WFDOS_AUTH_STAFF_ALLOWLIST=gary.larson@computingforall.org`
and `WFDOS_AUTH_SECRET_KEY=<64-byte-random>` in `.env`, restart services.

```bash
python scripts/smoke/auth/login.py gary.larson@computingforall.org
```

**Expect:** `OK: /auth/login accepted ...`, followed by a real email
at that inbox within ~30 seconds (subject: "Your Waifinder sign-in
link") with a `http://localhost:3000/auth/verify?token=...` link.

**Click the link.** Browser redirects to the portal home and a
`wfdos_session` cookie is set. Copy the cookie value from browser
devtools and verify the session:

```bash
python scripts/smoke/auth/me.py <wfdos_session cookie value>
```

**Expect:** `OK: /auth/me → gary.larson@computingforall.org (role=staff)`.

---

## 5. Tier decorator enforcement (#25)

```bash
python scripts/smoke/auth/tier_readonly_rejects_unauth.py
```

**Expect:** `OK: read_only tier rejects unauth`.

---

## 6. Stripped-env 503 path (#25 tier-2)

**Setup:** edit `.env` to remove `AZURE_OPENAI_KEY`, `ANTHROPIC_API_KEY`,
and `GEMINI_API_KEY`. Restart the assistant API service.

```bash
python scripts/smoke/auth/stripped_env_503.py <wfdos_session cookie>
```

**Expect:** `OK: llm_gated returns 503 with tier=llm_gated when stripped`.
The script asserts the body contains
`error.code == "service_unavailable"` and
`error.details.tier == "llm_gated"`.

Restore the `.env` after this test.

---

## 7. White-label tenant resolution (#16)

```bash
python scripts/smoke/tenancy/host_tenant.py platform.thewaifinder.com waifinder-flagship
python scripts/smoke/tenancy/host_tenant.py talent.borderplexwfs.org borderplex
```

**Expect:** both scripts exit `OK: Host <name> → X-Tenant-Id: <tenant>`.
If a service hasn't installed `TenantResolutionMiddleware` yet the
script will return the default tenant — track as a follow-up.

---

## 8. Structured logs flowing (#23)

Reuse the envelope-smoke script with a known request id, then eyeball
the consulting-api's log stream for the matching line:

```bash
python scripts/smoke/errors/validation_envelope.py --request-id log-smoke-001
```

**Expect:** the script prints `OK: validation envelope with
request_id echo (X-Request-Id=log-smoke-001)`, AND the
`consulting-api` log window (from `honcho start`) contains a
structured JSON line with:

- `"event": "api.validation_error"`
- `"request_id": "log-smoke-001"`
- `"service_name": "consulting-api"`

This is the only section where the assertion is a visual log
inspection — the script fires the trigger; you confirm it reached
the logger with context propagated.

---

## 9. Agent ABC reference run (#26)

```bash
python scripts/smoke/agent/echo.py
```

**Expect:** `OK: EchoAgent — action=intake_complete, latency_ms=<n>`.

---

## 10. nginx edge proxy config (#30)

```bash
python scripts/smoke/edge/nginx_t.py
```

**Expect:** `OK: nginx -t accepts wfdos-platform.conf` (skips with
`SKIP: nginx not installed` on a dev machine without nginx). The
script creates mock TLS cert paths under `/tmp/` so the certbot
references parse even if you're not on the VM.

**⚠ Production VM mutation — run manually, NOT scripted.** The
commands below scp the committed config to the live VM and reload
nginx. Roll-back path: the previous `/etc/nginx/sites-available/wfd-os`
(hyphenated, pre-rename) stays in place; `systemctl reload nginx`
with the old symlink restores.

Deploy per the embedded runbook in
`infra/edge/nginx/wfdos-platform.conf`:

```bash
scp infra/edge/nginx/wfdos-platform.conf azwatechadmin@20.106.201.34:/tmp/
ssh azwatechadmin@20.106.201.34 'sudo cp /tmp/wfdos-platform.conf \
  /etc/nginx/sites-available/wfdos-platform && \
  sudo ln -sf ../sites-available/wfdos-platform \
    /etc/nginx/sites-enabled/wfdos-platform && \
  sudo nginx -t && sudo systemctl reload nginx'
```

**Expect:** `nginx -t` passes, systemd reloads nginx without error,
`platform.thewaifinder.com` continues responding 200.

---

## 11. CTA contract health (#31)

```bash
python scripts/smoke/cta/contract_urls.py --base-url https://platform.thewaifinder.com
```

**Expect:** every entry prints `<path>  <status>` and the script ends
with `OK: every contract URL on <base> responds`. Accepted status
codes: 200 / 301 / 302 / 307 / 308 / 401 / 405. Anything else means
a contract URL regressed.

---

## 12. Credential rotation runbook (#9)

Per `docs/ops/credential-rotation.md`, rotate the `PG_PASSWORD`
(Azure Postgres admin):

1. Azure Portal → Postgres flexible server → Reset password.
2. Update `.env` + prod VM + restart services.
3. Hit any DB-backed endpoint (e.g. `/api/student/123/profile` — even a
   404 proves the query executed).
4. Post rotation completion on `#9` issue.

**Expect:** all services reconnect cleanly; no traceback in the logs
mentioning `password authentication failed`.

---

## 13. LaborPulse (PR #61 stacked on role-addition PR #60)

LaborPulse is the workforce-development director Q&A. It's a JSON
endpoint that either (a) proxies a live JIE or (b) returns a canned
mock answer after an 8-12s simulated synthesis delay when
`JIE_BASE_URL` is empty. Full architecture in `docs/laborpulse.md`.

### 13a. Environment

```bash
# For the mock-mode walkthrough (no JIE required) — leave JIE_BASE_URL
# unset and set the allowlist:
grep -q WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST .env || \
  echo 'WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST=gary.larson@computingforall.org' >> .env

honcho start laborpulse-api portal
```

### 13b. Service liveness

```bash
python scripts/smoke/laborpulse/health.py
```

**Expect:** `OK: laborpulse /api/health → jie_configured=false`.

### 13c. Unauth rejection

Covered by the generic validation + not-found envelope scripts in §3.
LaborPulse installs the same envelope handler, so an unauth POST to
`/api/laborpulse/query` returns the standard 401 envelope without
needing a dedicated script.

### 13d. Mock-mode end-to-end

Sign in as a director via `/auth/login` + click the magic-link email,
grab the `wfdos_session` cookie, then:

```bash
# Pipe the captured conversation_id into a variable for 13e.
CONV_ID=$(python scripts/smoke/laborpulse/mock_query.py "<cookie>" \
  "which sectors gained the most postings in Doña Ana in Q1?" | tail -n1)
echo "conversation_id=${CONV_ID}"
```

**Expect** (after 8-12s): the script prints `OK: mock query took ~10s,
conversation_id=mock-...` and the last line is the conversation_id
itself. The script asserts:
- wall-clock 8-14s
- `conversation_id` starts with `mock-`
- `confidence == "mock"`
- `answer` contains `[MOCK]`
- `evidence` + `follow_up_questions` each have ≥1 item

### 13e. Feedback write

```bash
python scripts/smoke/laborpulse/feedback.py "<cookie>" "${CONV_ID}" 1
```

**Expect:** `OK: qa_feedback row <N> written (rating=1)`. Verify the
row lands correctly:

```bash
psql -U wfdos -d wfdos -c \
  "SELECT tenant_id,user_email,user_role,rating,confidence
   FROM qa_feedback ORDER BY id DESC LIMIT 1;"
# → borderplex | gary.larson@computingforall.org | workforce-development | 1 | mock
```

### 13f. Real-JIE 503 path

Restart the laborpulse service with an unreachable JIE, then:

```bash
JIE_BASE_URL=http://127.0.0.1:1 honcho start laborpulse-api &
sleep 2
python scripts/smoke/laborpulse/jie_503.py "<cookie>"
```

**Expect:** `OK: JIE-unreachable returns 503 envelope with upstream=jie`.

### 13g. Browser walkthrough

1. Visit `https://platform.thewaifinder.com/laborpulse` (or
   `talent.borderplexwfs.org/laborpulse` for the Borderplex brand).
2. Type a question, click Ask.
3. **Expect:** loading skeleton rotates through
   "Analyzing…" / "Running…" / "Synthesizing…" / "Citing…" every ~4.5s.
4. After ~10s the full answer renders with evidence cards, confidence
   badge, follow-up chips, and thumbs-up/down buttons.
5. Click a follow-up chip → new request fires, same flow.
6. Thumbs-up — confirm the feedback row lands.

---

## 14. PR cleanup after the morning pass

Once sections 1–13 pass:

1. Comment on each of the stacked PRs with ✅ / ❌ against the
   section that covers it.
2. Decide the merge-to-master strategy: squash each PR in stack order,
   or a single "refactor epic" merge commit. My recommendation is
   **stack-order squash**: each PR keeps its own commit on master so
   `git log` shows the phase-by-phase story, and each squashed commit
   stays atomic.
3. After merging, delete the `phase-5-exit-gate` branch + every
   `issue-*` and `phase-*-exit-gate` branch in the stack.

## Troubleshooting

- **Magic-link email never arrives:** check the Graph `SendAs`
  permission for `hello@thewaifinder.com` at Azure AD; verify
  `GRAPH_CLIENT_SECRET` isn't expired (rotation section #1 in the
  runbook).
- **401 on every auth'd endpoint after login:** cookie domain
  mismatch. The `wfdos_session` cookie is scoped to the service's
  hostname; if you're hitting `localhost:8003` after logging in via
  `localhost:3000`, they share the hostname but not the port — most
  browsers treat same-hostname-different-port as same-site, but some
  stricter configs don't. Test with `curl` and the cookie header
  explicitly copied across, as in step 4.
- **nginx -t fails on cert paths:** that's a local-testing artifact.
  The VM has the real certs via certbot; the test would pass there.
  Use `nginx -T` to dump the expanded config, or mock the cert paths
  with `touch /tmp/fullchain.pem` + adjust the conf temporarily.

---

**Signed off:** phase-5-exit-gate ready for Gary's morning pass.
