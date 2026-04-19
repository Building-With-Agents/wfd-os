# LaborPulse — workforce-development director Q&A

**Audience:** any engineer or operator touching the `/laborpulse` flow,
the `agents/laborpulse/` service, or the May 7 Borderplex demo.

## One-paragraph summary

LaborPulse is the marketing name for the workforce-development director
Q&A. It's a **thin JSON API** on wfd-os that calls the Job Intelligence
Engine's (`job-intelligence-engine` repo) `POST /analytics/query`
endpoint, waits for the full answer, and returns a single response
dict. Authentication + tenant resolution + feedback capture all live on
the wfd-os side; JIE stays stateless about who's asking.

The first deployment is Borderplex (El Paso + Ciudad Juárez + Las
Cruces + Doña Ana) because that's where our JIE data and the May 7
demo audience live.

## Architecture

```
┌──────────────────────────────┐
│  Browser — director session  │
│  GET https://talent.borderplexwfs.org/laborpulse
└──────────────┬───────────────┘
               │  POST /api/laborpulse/query
               │  cookie: wfdos_session (role=workforce-development)
               ▼
┌──────────────────────────────────────────────────┐
│  nginx edge (infra/edge/nginx/wfdos-platform.conf)│
│  Host → X-Tenant-Id: borderplex                   │
│  proxy_read_timeout 300s (JIE synthesis 15-45s)   │
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
│                                                   │
│  If settings.jie.base_url is set:                │
│     await jie_query(...)         (real pathway)  │
│  Else:                                            │
│     await _mock_query(question)  (mock pathway)  │
└──────────────┬───────────────────────────────────┘
               ▼
┌──────────────────────────────────────────────────┐
│  (real)   job-intelligence-engine                 │
│           POST {JIE_BASE_URL}/analytics/query     │
│           receives X-Tenant-Id + X-User-Email     │
│                                                   │
│  (mock)   asyncio.sleep(8-12s) + canned answer    │
└──────────────┬───────────────────────────────────┘
               ▼
  Returns QueryResponse JSON:
    { conversation_id, answer, evidence, confidence,
      follow_up_questions, cost_usd, sql_generated }
               ▼
┌──────────────────────────────────────────────────┐
│  Browser — renders the complete answer           │
│  portal/student/app/laborpulse/LaborPulseClient  │
│  Loading skeleton rotates stage text every 4.5s  │
│  while waiting.                                   │
│  Thumbs-up/down → POST /api/laborpulse/feedback  │
└──────────────────────────────────────────────────┘
```

## Response assembly

JIE's `/analytics/query` emits a series of framed events during its
pipeline (Intent → Route → SQL → Synthesize → Cite → Follow-up). The
LaborPulse client (`agents/laborpulse/client.py`) consumes the full
response body, folds each event into one accumulator dict, and returns
the assembled result. The folding rules:

| Event    | Behavior on accumulator |
|----------|-----------------------------|
| `answer` | Append `text` / `delta` to `answer` string |
| `evidence` | Append to `evidence` list (flattens `items: [...]` payloads) |
| `confidence` | Set `confidence` to `level` or `text` |
| `followup` / `follow_up` | Append `question` / extend with `questions` list |
| `sql` | Set `sql_generated` to `sql` / `query` / `text` |
| `done` | Set `conversation_id` + `cost_usd` |
| _unknown_ | Silently ignored — keeps wfd-os decoupled from JIE event-vocabulary changes |

Malformed data payloads are tolerated: if JIE emits a bare text token
without JSON wrapping (common for streamed answer tokens), the client
treats the raw string as `{"text": ...}` and appends to `answer`.

## Mock mode

When `settings.jie.base_url` is empty the endpoint switches to a mock
pathway — an 8-12s `asyncio.sleep` followed by a canned
Borderplex-flavored response shaped like the real `QueryResponse`. The
mock exists so the frontend renders realistically in dev + demo
rehearsal without needing a live JIE.

Invariants:

- **Always visibly mock.** `confidence: "mock"` + the string `[MOCK]`
  at the start of `answer`. `conversation_id` starts with `mock-`.
- **Logged.** Each invocation emits `laborpulse.query.mock` at INFO
  with the chosen delay, so accidental prod-mode-mock deploys are
  greppable.
- **`/api/health` signals it.** `{jie_configured: false}` when
  `JIE_BASE_URL` is empty; production deploy checks include this field.
- **Feedback works.** Thumbs-up/down on a mock answer writes
  `qa_feedback` rows with `confidence = "mock"` and
  `conversation_id` starting `mock-`, so mock-era feedback can be
  filtered out later.

## Roles + auth

- **`workforce-development`** — the fourth role (issue #59). Env var
  `WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST` comma-separated emails.
- `staff` and `admin` also have access (useful during demos when Gary
  or Ritu is driving).
- `student` is explicitly rejected with 403 so an allowlist collision
  can't silently promote a student into LaborPulse tier.

Unauthenticated → 401 envelope; wrong role → 403; JIE unreachable /
timeout / 5xx → 503 envelope with `error.details.upstream = "jie"`;
JIE 4xx (bad question) → 422 envelope. All via the #29 envelope handler.

## qa_feedback table

Lives in wfd-os Postgres (system of record per CLAUDE.md). Schema:

```sql
id              BIGSERIAL PK
tenant_id       TEXT NOT NULL     -- from request.state.tenant_id (#16)
user_email      TEXT NOT NULL     -- from request.state.user.email (#24)
user_role       TEXT NOT NULL     -- 'workforce-development' | 'staff' | 'admin'
conversation_id TEXT NOT NULL     -- JIE-assigned turn id (or 'mock-...' in mock mode)
question        TEXT NOT NULL
answer_snapshot TEXT              -- assembled final answer, for re-review
rating          SMALLINT CHECK IN (-1, 1)
comment         TEXT
cost_usd        NUMERIC(10,6)     -- JIE-reported; 0.0 in mock mode
confidence      TEXT              -- 'low' | 'medium' | 'high' | 'mock'
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

## Running it locally

### Mock mode (no JIE required)

```bash
# 1. Leave JIE_BASE_URL unset in .env; set the allowlist:
echo 'WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST=gary.larson@computingforall.org' >> .env

# 2. Boot just the LaborPulse service + portal:
honcho start laborpulse-api portal

# 3. Visit http://localhost:3000/laborpulse, log in via /auth/login +
#    the magic-link email, ask a question. Expect ~10s wait, then a
#    Borderplex-flavored answer with [MOCK] prefix.
```

### Real JIE mode

```bash
echo 'JIE_BASE_URL=http://localhost:8080' >> .env
# Boot JIE locally on 8080 per that repo's README, then:
honcho start laborpulse-api portal
```

### Inspect feedback

```bash
psql -U wfdos -d wfdos -c \
  "SELECT tenant_id, user_email, user_role, rating, confidence
   FROM qa_feedback ORDER BY id DESC LIMIT 5;"
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
- Remove the mock pathway (or gate it behind `WFDOS_ENV=dev`) once
  JIE is live end-to-end and `confidence == "mock"` feedback rows stop
  appearing in production.
