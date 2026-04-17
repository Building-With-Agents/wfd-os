# LaborPulse — workforce-development director Q&A

**Audience:** any engineer or operator touching the `/laborpulse` flow,
the `agents/laborpulse/` service, or the May 7 Borderplex demo.

## One-paragraph summary

LaborPulse is the marketing name for the workforce-development director
Q&A. It's a **thin wfd-os surface** around the Job Intelligence Engine's
(`job-intelligence-engine` repo) streaming `POST /analytics/query`
endpoint. The director types a question at
`https://talent.borderplexwfs.org/laborpulse`, wfd-os authenticates the
session + resolves the tenant, proxies the SSE chunk-by-chunk from JIE,
and captures thumbs-up/down feedback into the wfd-os `qa_feedback`
table.

The first deployment is Borderplex (El Paso + Ciudad Juárez + Las
Cruces + Doña Ana) because that's where our JIE data and the May 7 demo
audience live.

## Architecture

```
┌──────────────────────────────┐
│  Browser — director session  │
│  GET https://talent.borderplexwfs.org/laborpulse
└──────────────┬───────────────┘
               │  fetch POST /api/laborpulse/query
               │  cookie: wfdos_session (role=workforce-development)
               ▼
┌──────────────────────────────────────────────────┐
│  nginx edge (infra/edge/nginx/wfdos-platform.conf)│
│  Host → X-Tenant-Id: borderplex                   │
│  proxy_buffering off (SSE)                        │
│  proxy_read_timeout 300s                          │
│  limit_req zone=platform_laborpulse               │
└──────────────┬───────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────┐
│  agents/laborpulse/api.py (FastAPI, port 8012)   │
│  RequestContextMiddleware → request_id           │
│  TenantResolutionMiddleware → borderplex         │
│  SessionMiddleware → request.state.user          │
│  @llm_gated(roles=("staff","admin",              │
│                    "workforce-development"))     │
│  peek first SSE chunk to surface startup errors  │
│  return StreamingResponse(text/event-stream)     │
└──────────────┬───────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────┐
│  job-intelligence-engine                          │
│  POST {JIE_BASE_URL}/analytics/query              │
│  receives X-Tenant-Id + X-User-Email              │
│  pipeline: Intent → Route → SQL → Synthesize      │
│           → Cite → Follow-up                      │
│  yields SSE events: answer / evidence /           │
│           confidence / followup / done            │
└──────────────────────────────────────────────────┘
               ▲
               │ (same stream, byte-for-byte)
               ▼
┌──────────────────────────────────────────────────┐
│  Browser — progressive render in                  │
│  portal/student/app/laborpulse/LaborPulseClient   │
│  → thumbs-up/down → POST /api/laborpulse/feedback │
└──────────────────────────────────────────────────┘
```

## Roles + auth

- **`workforce-development`** — the new fourth role from #59. Env var
  `WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST` comma-separated emails.
- `staff` and `admin` also have access (useful during demos when Gary
  or Ritu is driving).
- `student` is explicitly rejected with 403 so an allowlist collision
  can't silently promote a student into LaborPulse tier.

Unauthenticated → 401 envelope; wrong role → 403 envelope; missing JIE
config → 503 envelope with `error.details.upstream = "jie"` — all
through the #29 envelope handler.

## qa_feedback table

Lives in wfd-os Postgres (system of record per CLAUDE.md). Schema:

```sql
id              BIGSERIAL PK
tenant_id       TEXT NOT NULL     -- from request.state.tenant_id (#16)
user_email      TEXT NOT NULL     -- from request.state.user.email (#24)
user_role       TEXT NOT NULL     -- 'workforce-development' | 'staff' | 'admin'
conversation_id TEXT NOT NULL     -- JIE-assigned turn id
question        TEXT NOT NULL
answer_snapshot TEXT              -- assembled final answer
rating          SMALLINT CHECK IN (-1, 1)
comment         TEXT
cost_usd        NUMERIC(10,6)     -- JIE-reported
confidence      TEXT              -- JIE-reported 'low'|'medium'|'high'
created_at      TIMESTAMPTZ DEFAULT NOW()
```

Indexes: `(tenant_id, created_at DESC)` for tenant-scoped dashboards,
`(rating)` for grouping thumbs-up vs down, `(conversation_id)` for
joining with JIE-side traces when debugging a specific turn.

## JIE-side dependency

LaborPulse forwards `X-Tenant-Id` to JIE. JIE must accept that header
and scope its SQL accordingly, or the first tenant with data after
Borderplex leaks rows cross-tenant. Open a paired JIE ticket before
any second-tenant rollout; Borderplex-only deploy is safe until then
(there's only one tenant's data in the mirror).

## Streaming invariants

- **No buffering at the edge.** `proxy_buffering off` in nginx. If this
  flips back on, the director sees the answer arrive in one chunk after
  the whole thing synthesizes — demo-ending.
- **`X-Accel-Buffering: no`** also set on the FastAPI response to pin
  it even if a future nginx change flips the default back.
- **First-chunk peek.** `api.py` reads one chunk from JIE synchronously
  before handing control to FastAPI's StreamingResponse. This is how
  ServiceUnavailableError / ValidationFailure from JIE get routed
  through the #29 envelope; once the StreamingResponse is returned,
  exceptions reach the client as a truncated body, not an envelope.
- **Byte-for-byte passthrough.** wfd-os never parses or reframes JIE's
  SSE wire format. If JIE changes its `event:` names tomorrow, the
  frontend (LaborPulseClient.tsx) picks up whatever JIE emits.

## Running it locally

```bash
# 1. Set the env.
echo 'JIE_BASE_URL=http://localhost:8080' >> .env
echo 'WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST=gary.larson@computingforall.org' >> .env

# 2. Boot JIE locally (separate repo) on 8080, then boot wfd-os:
honcho start laborpulse-api portal

# 3. Log in as the director via /auth/login, click the email link, land
#    on / with a wfdos_session cookie. Navigate to /laborpulse and ask
#    a Borderplex question.

# 4. Inspect the feedback row:
psql -U wfdos -d wfdos -c \
  "SELECT tenant_id, user_email, user_role, rating, confidence FROM qa_feedback ORDER BY id DESC LIMIT 5;"
```

## Follow-up issues after smoke

- JIE-side `X-Tenant-Id` scoping (paired ticket on the JIE repo).
- Move the brand header on the `/laborpulse` page to pull from
  `request.state.brand` once the Next.js portal exposes a per-request
  brand context (#16 groundwork, needs one more wiring pass).
- Migrate the allowlist from env CSV to the `tenants` DB table when
  LaborPulse ships to a second client (currently Borderplex-only).
- Golden-question eval harness that replays a canned set of director
  questions against a test JIE and asserts answer shape + cost ceiling
  — calibration work for Week 9 of the curriculum.
