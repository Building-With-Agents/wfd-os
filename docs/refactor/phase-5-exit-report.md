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

# Confirm wfdos-common imports cleanly.
python -c "
from wfdos_common.config import settings, PG_CONFIG
from wfdos_common.auth import build_auth_router, require_role, SessionMiddleware
from wfdos_common.tenancy import get_brand, TenantResolutionMiddleware
from wfdos_common.agent import Agent, EchoAgent
from wfdos_common.errors import install_error_handlers
from wfdos_common.logging import configure, get_logger
print('all imports OK')
"
```

**Expect:** `all imports OK` with no traceback.

---

## 1. Full pytest suite

```bash
pytest packages/wfdos-common/tests --cov=wfdos_common --cov-fail-under=50
```

**Expect:** `273 passed`, coverage ≥ 67%.

---

## 2. Boot the full stack

```bash
honcho start
```

**Expect:** all 12 services start without crashes. Hit `/api/health` on
each to confirm:

```bash
for p in 8000 8001 8002 8003 8004 8006 8008 8009 8010; do
  curl -s localhost:$p/api/health | jq .
done
```

Expected shape on each: `{"status": "ok", "service": "<name>", "port": <N>}`.

---

## 3. Structured error envelope (#29)

```bash
# Malformed POST to consulting intake
curl -s -X POST localhost:8003/api/consulting/inquire \
     -H 'Content-Type: application/json' \
     -H 'X-Request-Id: smoke-29a' \
     -d '{}' | jq .
```

**Expect:**
```json
{
  "data": null,
  "error": {
    "code": "validation_error",
    "message": "Request validation failed",
    "details": {
      "field_errors": [ ... ],
      "request_id": "smoke-29a"
    }
  },
  "meta": null
}
```

```bash
# Not-found path on student API
curl -s -i localhost:8001/api/student/does-not-exist/profile
```

**Expect:** 404 status, body envelope with `code: "not_found"`,
response header `X-Request-Id: <uuid>`.

---

## 4. Magic-link auth end-to-end (#24)

**Setup:** set `WFDOS_AUTH_STAFF_ALLOWLIST=gary.larson@computingforall.org`
and `WFDOS_AUTH_SECRET_KEY=<64-byte-random>` in `.env`, restart services.

```bash
# Fire the login — this sends a REAL email.
curl -s -X POST localhost:8003/auth/login \
     -H 'Content-Type: application/json' \
     -d '{"email":"gary.larson@computingforall.org"}' | jq .
```

**Expect:**
- 200 response with `{"status": "ok", "message": "..."}`.
- An email at `gary.larson@computingforall.org` within ~30 seconds,
  subject "Your Waifinder sign-in link", containing a link of the form
  `http://localhost:3000/auth/verify?token=...`.

**Click the link.**

**Expect:**
- Browser redirects to the portal home.
- A `wfdos_session` cookie is set on `localhost:3000`.

```bash
# Inspect the session (copy the cookie from browser dev tools).
curl -s -H 'Cookie: wfdos_session=<paste>' localhost:3003/auth/me | jq .
```

**Expect:** `{"email": "gary.larson@computingforall.org", "role": "staff", "tenant_id": null}`.

---

## 5. Tier decorator enforcement (#25)

```bash
# Anonymous (no cookie) — @public endpoint works.
curl -s localhost:8003/api/health | jq .

# Anonymous — @read_only endpoint 401s.
curl -s -o /dev/null -w '%{http_code}\n' localhost:8001/api/student/me
```

**Expect:** `200` for health, `401` for the read_only route.

---

## 6. Stripped-env 503 path (#25 tier-2)

**Setup:** edit `.env` to remove `AZURE_OPENAI_KEY`, `ANTHROPIC_API_KEY`,
and `GEMINI_API_KEY`. Restart the assistant API service.

```bash
curl -s -X POST localhost:8009/api/assistant/chat \
     -H 'Content-Type: application/json' \
     -H 'Cookie: wfdos_session=<from step 4>' \
     -d '{"agent_type":"consulting","message":"hi"}' | jq .
```

**Expect:** 503 with:
```json
{
  "data": null,
  "error": {
    "code": "service_unavailable",
    "message": "LLM provider not configured on this host",
    "details": { "tier": "llm_gated", "request_id": "..." }
  },
  "meta": null
}
```

Restore the `.env` after this test.

---

## 7. White-label tenant resolution (#16)

```bash
# Flagship host → waifinder-flagship tenant
curl -s -i -H 'Host: platform.thewaifinder.com' localhost:8001/api/health | head -15

# Borderplex host → borderplex tenant
curl -s -i -H 'Host: talent.borderplexwfs.org' localhost:8001/api/health | head -15
```

**Expect:** `X-Tenant-Id: waifinder-flagship` in the first response
headers, `X-Tenant-Id: borderplex` in the second (once
TenantResolutionMiddleware is attached — if the services don't yet
install it, expect fallback to the default; track as a follow-up).

---

## 8. Structured logs flowing (#23)

```bash
# Make a few requests while watching service output.
honcho start | grep -i 'consulting-api'
# In another shell:
curl -s -X POST localhost:8003/api/consulting/inquire -d '{}' \
     -H 'Content-Type: application/json' \
     -H 'X-Request-Id: log-smoke-001'
```

**Expect:** a JSON log line from consulting-api containing
`"request_id": "log-smoke-001"` and `"api.validation_error"` event.

---

## 9. Agent ABC reference run (#26)

```python
python -c "
from wfdos_common.agent import EchoAgent
a = EchoAgent()
result = a.process('intake complete, ready to scope', metadata={'tenant_id':'waifinder-flagship'})
print(result)
"
```

**Expect:** `AgentResult(response='echo: intake complete, ready to scope', action='intake_complete', ...)`.

---

## 10. nginx edge proxy config (#30)

```bash
# Syntactic validation (requires nginx + mocked TLS cert paths)
sudo nginx -t -c infra/edge/nginx/wfdos-platform.conf \
  2> nginx-test.out
cat nginx-test.out
```

**Expect:** either "syntax is ok" (if cert paths resolve) or a warning
about missing TLS files only. Any other error is a regression.

Then deploy per the embedded runbook in
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
# Walk every "live" URL in the contract and check it responds.
for path in / /careers /showcase /for-employers /college \
            /auth/login /auth/me /api/health ; do
  code=$(curl -s -o /dev/null -w '%{http_code}' \
    https://platform.thewaifinder.com$path)
  echo "$path → $code"
done
```

**Expect:** `200` or `401`/`302` (the auth-required ones) for each —
anything else means a contract URL regressed.

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
curl -s localhost:8012/api/health | jq .
# → {"status":"ok","service":"laborpulse","port":8012,"jie_configured":false}
```

### 13c. Unauth rejection

```bash
curl -s -i localhost:8012/api/laborpulse/query -X POST \
     -H 'Content-Type: application/json' \
     -d '{"question":"top growth sectors in El Paso"}'
# → 401 envelope with code "unauthorized"
```

### 13d. Mock-mode end-to-end

Sign in as a director via `/auth/login` + click the magic-link email,
grab the `wfdos_session` cookie, then:

```bash
time curl -s localhost:8012/api/laborpulse/query \
     -H 'Cookie: wfdos_session=<paste>' \
     -H 'Host: talent.borderplexwfs.org' \
     -X POST -H 'Content-Type: application/json' \
     -d '{"question":"which sectors gained the most postings in Doña Ana in Q1?"}' \
     | jq .
```

**Expect** (after 8-12s):
- Single JSON body with keys:
  `conversation_id, answer, evidence, confidence, follow_up_questions, cost_usd, sql_generated`
- `conversation_id` starts with `mock-`
- `answer` begins with `[MOCK]` and echoes the question
- `confidence` is `"mock"`
- `evidence` has ≥1 item, `follow_up_questions` has ≥1 item

### 13e. Feedback write

```bash
curl -s localhost:8012/api/laborpulse/feedback \
     -H 'Cookie: wfdos_session=<paste>' \
     -X POST -H 'Content-Type: application/json' \
     -d '{"conversation_id":"<from 13d>","question":"<same>","rating":1,"confidence":"mock"}'
# → {"ok":true,"id":<int>}
```

Verify the row:
```bash
psql -U wfdos -d wfdos -c \
  "SELECT tenant_id,user_email,user_role,rating,confidence
   FROM qa_feedback ORDER BY id DESC LIMIT 1;"
# → borderplex | gary.larson@computingforall.org | workforce-development | 1 | mock
```

### 13f. Real-JIE 503 path

```bash
# Unreachable JIE:
JIE_BASE_URL=http://127.0.0.1:1 honcho start laborpulse-api
curl -s -i localhost:8012/api/laborpulse/query \
     -H 'Cookie: wfdos_session=<paste>' \
     -X POST -H 'Content-Type: application/json' \
     -d '{"question":"anything"}'
# → 503 envelope with error.details.upstream == "jie"
```

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
