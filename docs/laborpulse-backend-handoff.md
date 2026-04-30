# LaborPulse — backend handoff + future architecture

**Audience:** JIE backend team + wfd-os contributors picking up the
LaborPulse track.
**Status:** Draft — captured during the 2026-04-20 phase-5 live smoke
against the mock response.
**Source-of-truth doc:** `docs/laborpulse.md` (architecture + mock mode
+ role model). This doc is the *handoff* — what has to be built, in
what order.

---

## TL;DR

1. **Short-term (unblock real data):** JIE implements
   `POST /analytics/query` returning JSON with a fixed shape. wfd-os
   swaps its current SSE-parsing client for a plain JSON call. No UX
   change — the existing form page starts showing real Borderplex
   data instead of `[MOCK]`.
2. **Medium-term (UX upgrade):** the LaborPulse page becomes a **chat
   widget** identical to the "CFA Advisor" widget already rendered
   in the portal footer (`portal/student/components/ChatWidget.tsx`).
   Workforce-development persona joins the 6 existing agents on
   `assistant-api` (:8009) as the 7th.
3. **Long-term (commercial):** a **separate entitlement layer** holds
   the per-tenant paid coverage (regions, topic scopes, monthly
   budgets). wfd-os middleware reads it, classifies each question,
   and either forwards to JIE or returns a 402/403 envelope. Nginx
   handles raw rate-limiting; entitlement handles semantic scoping.

---

## Part 1 — Today's state (reference)

### Request path (live)

```
browser                     :3000
  └─ POST /api/laborpulse/query  (Next.js rewrite)
       └─ laborpulse-api      :8012
            ├─ SessionMiddleware       — reads wfdos_session cookie
            ├─ TenantResolutionMiddleware — Host → tenant_id
            ├─ @llm_gated(roles=(workforce-development, staff, admin))
            └─ branch:
                 • JIE_BASE_URL unset  → _mock_query (8–12s sleep, canned Borderplex answer)
                 • JIE_BASE_URL set    → agents.laborpulse.client.query(...)
                                          → POST {JIE}/analytics/query (SSE)
```

### Key files

| File                                                | Role |
|-----------------------------------------------------|------|
| `agents/laborpulse/api.py`                          | FastAPI service on :8012, `/query` + `/feedback` + `/api/health` |
| `agents/laborpulse/client.py`                       | SSE-consuming JIE client; folds frames into a single JSON dict |
| `portal/student/app/laborpulse/page.tsx`            | Current form-style page (question input + answer block) |
| `portal/student/components/ChatWidget.tsx`          | Existing chat widget (CFA Advisor) — lines 1-238 |
| `infra/edge/nginx/wfdos-platform.conf`              | nginx rate-limit zones (per-IP) — line 38 `platform_laborpulse` 60r/m |
| `docs/laborpulse.md`                                | Canonical architecture + mock-mode + qa_feedback schema |

### Current response contract (what the browser receives)

```ts
type QueryResponse = {
  conversation_id: string | null;   // "mock-<uuid>" in mock mode
  answer: string;                   // `[MOCK]` prefix when mock
  evidence: Array<{source: string, text: string, ...}>;
  confidence: "low" | "medium" | "high" | "mock" | null;
  follow_up_questions: string[];
  cost_usd: number | null;
  sql_generated: string | null;     // for transparency / audit
};
```

The mock answer uses `confidence: "mock"` + `[MOCK]` in the answer
text so downstream consumers (and grep in logs) can tell mock apart
from real.

---

## Part 2 — Short-term: JIE drop-in contract

Goal: JIE team implements an endpoint wfd-os can call and the current
form page starts showing real data. **No UX change.**

### Endpoint

```
POST {JIE_BASE_URL}/analytics/query
```

### Request headers (set by wfd-os, don't fail without them)

| Header             | Source                                            | Required |
|--------------------|---------------------------------------------------|----------|
| `Content-Type`     | `application/json`                                | yes |
| `X-Tenant-Id`      | `request.state.tenant_id` from TenantResolver     | yes — use for scoping + audit |
| `X-User-Email`     | `request.state.user.email`                        | yes — audit only, not a trust signal |
| `X-Request-Id`     | `current_context().get("request_id")` (uuid)      | yes — propagate in logs |
| `X-API-Key`        | `settings.jie.api_key` (wfd-os → JIE shared secret) | yes — auth |

### Request body

```json
{
  "question": "Which sectors gained the most postings in Doña Ana in Q1?",
  "conversation_id": "abc123-def456"
}
```

`conversation_id` is **optional**. First message in a conversation
omits it. Follow-up chip clicks pass back the `conversation_id`
returned in the prior response.

### Response — recommended: JSON (not SSE)

The wfd-os boundary exposes JSON to the browser. Gary's direction:
"treat SSE at the wfd-os boundary as if it never existed" (see memory
`feedback_laborpulse_json_only.md`). Applying the same logic to the
JIE → wfd-os boundary simplifies everything:

```json
{
  "conversation_id": "abc123-def456",
  "answer": "Across the Borderplex region in Q1 2026 ...",
  "evidence": [
    {"source": "lightcast_postings_2026Q1", "text": "12,840 active postings, +14% vs Q4 2025"},
    {"source": "bls_oes_nm_doña_ana",        "text": "Healthcare Support occupations grew 11.8% YoY"}
  ],
  "confidence": "medium",
  "follow_up_questions": [
    "Which employers drove the Q1 manufacturing growth?",
    "What are the median wages for bilingual medical-support roles?"
  ],
  "cost_usd": 0.032,
  "sql_generated": "SELECT industry, COUNT(*) ... FROM jobs_2026q1 ..."
}
```

Required status codes:

| Status | Meaning                        | wfd-os behavior                                 |
|--------|--------------------------------|-------------------------------------------------|
| 200    | Synthesized answer             | wrap in `APIEnvelope` and return to browser     |
| 400    | Question rejected (unparseable, too broad, empty) | `ValidationFailure` envelope to browser   |
| 401    | API key invalid                | `ServiceUnavailableError`, alert on-call        |
| 403    | Tenant lacks entitlement (see Part 4) | pass through — browser shows upgrade CTA |
| 429    | Rate-limited at JIE            | map to 503 with `details.upstream="jie"`        |
| 5xx    | JIE internal failure           | map to 503 with `details.upstream="jie"`        |

### wfd-os client change required

`agents/laborpulse/client.py` currently expects SSE (`resp.aiter_text`
+ `_fold_frame_into` + per-event parsing). Two options:

- **A.** JIE emits JSON → **delete SSE parsing in wfd-os** (~70 lines
  removed, just `resp = await client.post(...); return resp.json()`).
- **B.** JIE keeps SSE → wfd-os client unchanged.

**Recommendation: A.** Matches Gary's JSON-native direction; simpler
both ways; identical latency (JIE synthesizes on its side and flushes
the final payload).

### JIE side work summary (short-term)

1. New endpoint `POST /analytics/query` accepting the header + body
   above, returning the JSON above.
2. Wire up the existing `run_analytics_qna` pipeline (see
   `analytics/api/routes.py:307-310`, `routing.py:403+`).
3. Accept `conversation_id` for multi-turn memory; return a new one
   or the same one. **Not implemented today** (the existing endpoint
   uses `correlation_id` only).
4. Propagate `X-Tenant-Id` / `X-User-Email` / `X-Request-Id` into
   JIE's structured logs so cross-system tracing works.

---

## Part 3 — Medium-term: chat widget (not a form)

### What changes UX-wise

Drop the form-style `/laborpulse` page. The workforce-development
persona becomes the **7th conversational agent** served by
`assistant-api` on :8009, reached through the existing chat widget.

The chat widget already exists and is mounted globally in the portal
(`portal/student/app/layout.tsx`). It:

- Floats bottom-right everywhere except `/cfa/ai-consulting/chat` +
  `/internal` (where the full-page chat takes over).
- POSTs to `/api/assistant/chat` with `{session_id, agent_type, message}`.
- Persists session across messages; new session on route change.
- Renders server-suggested follow-ups as quick-reply chips.

### What has to be built on wfd-os

| File (new / edit)                                  | Change |
|----------------------------------------------------|--------|
| `agents/assistant/workforce_agent.py` (new)        | New BaseAgent — persona = "workforce-development director helper", tools = LaborPulse query / feedback / scope-info (see Part 4) |
| `agents/assistant/api.py` (edit)                   | Register the new agent in `_REGISTERED_AGENTS` dict (line 105-112) |
| `portal/student/components/ChatWidget.tsx` (edit)  | Extend the path→agent map (line 10-18) — add `/laborpulse` → `workforce-development`, `/dashboard` if directors land there, etc. |
| `agents/laborpulse/api.py` (keep)                  | Still hosts `/query` + `/feedback` as the thin proxy; the agent uses these as tools rather than re-implementing |
| `portal/student/app/laborpulse/page.tsx` (delete or simplify) | Becomes a landing page with domain framing ("Ask about the Borderplex labor market") + auto-opens the widget. Or delete entirely and let the floating widget be the only surface. |

### What has to be built on JIE

- **Multi-turn memory**: the JIE `/analytics/query` must accept
  `conversation_id` and carry forward prior-turn context (answers,
  cited evidence, narrowing of scope). Current implementation has
  `correlation_id` only — that's request-tracing, not conversation.
  Options:
  - JIE owns the conversation store (Redis / Postgres), keyed on
    `conversation_id`.
  - wfd-os owns it (in `agent_conversations` table already in the
    wfd-os schema), forwards compacted history to JIE on each turn.
    Less state on JIE but more network. **Recommendation: JIE owns
    it** — keeps the wfd-os side stateless per turn.
- **Session continuity across tools**: if the workforce agent also
  calls non-JIE tools (e.g. wfd-os's own `students` / `employers`
  table for "which of our students are placed in the sectors JIE
  identified?"), the conversation needs shared memory. Keep in
  `agent_conversations` — wfd-os side — and pass relevant JIE context
  as part of each `/analytics/query` call.

---

## Part 4 — Long-term: entitlement + payment layer (encapsulated)

### Principle

**Auth** (who is this user?) already in place via wfdos_common.auth.
**Entitlement** (what did this user's tenant pay for?) is NEW and
lives in its own encapsulated service. Same request, two gates:

```
request
  └─ SessionMiddleware        → request.state.user  {email, role}
  └─ EntitlementMiddleware    → request.state.entitlement  {regions, topics, budget, ...}
  └─ @llm_gated               → enforces role
  └─ @scope_gated             → enforces entitlement (new)
  └─ route handler            → /laborpulse/query
```

### Entitlement shape (proposed)

Stored in a separate service/table; fetched per-request by tenant_id
and cached per-worker for ~5 minutes.

```json
{
  "tenant_id": "borderplex",
  "plan_id": "workforce_pro_2026",
  "active": true,
  "regions": ["borderplex", "el_paso", "dona_ana", "cd_juarez"],
  "topics": ["labor_demand", "skills_gaps", "wage_analysis", "sector_mix"],
  "excluded_topics": ["individual_employer_deep_dives"],
  "monthly_query_budget": 500,
  "monthly_queries_used": 127,
  "monthly_cost_usd_budget": 25.00,
  "monthly_cost_usd_used": 3.14,
  "features": {
    "multi_turn": true,
    "sql_exposure": true,
    "historical_depth_years": 3,
    "evidence_cards": true
  },
  "plan_expires_at": "2026-12-31T23:59:59Z"
}
```

### Where entitlement data lives

**Separate service / separate repo.** wfd-os only reads it. Options:

- **Stripe + a thin `billing-api`**: Stripe is the source-of-truth
  for plan/subscription state. A new `billing-api` microservice
  translates Stripe events → the entitlement JSON above, exposes
  `GET /api/entitlement/{tenant_id}`. Stripe webhooks update a cache.
- **Standalone `wfd-billing` service**: if we want to support
  non-Stripe (purchase orders, grant-funded, CFA-comp)  as first-class.
  Same API shape. Same swappable pattern.
- **Nothing (hardcoded)** for Borderplex-only phase 1: `tenancy.py`
  BrandConfig grows an `entitlement: EntitlementConfig` field with
  the same shape. Migrate to a real service once a second paying
  tenant exists.

**Recommendation**: start with BrandConfig entitlement (zero infra),
define the API shape for the future service in advance, so the
migration is a single `get_entitlement(tenant_id)` function swap.

### Question classification + scope enforcement

Before calling JIE, the workforce agent:

1. Classifies the user's question into one of `entitlement.topics` or
   "out_of_scope". Two implementations:
   - **Rule-based**: keyword + regex taxonomy (`wages|salary` → `wage_analysis`,
     `gap|upskill|training` → `skills_gaps`, etc.). Fast, no LLM cost.
   - **LLM-based**: lightweight Azure OpenAI `chat-gpt41mini` call
     ("classify the following question into one of: ..."). More
     robust for freeform director questions. ~100 tokens, <1 cent.

   **Recommendation**: rule-based fallback, LLM-based primary — if
   the rule confidently tags the question, use it; else ask the LLM.
2. Classifies the question's **region**. If the question names
   "Dallas" and entitlement is `["borderplex","el_paso","dona_ana"]`,
   return 403 with `details.reason="region_not_entitled"` and a body
   suggesting an upgrade CTA.
3. Checks monthly budget (`queries_used`, `cost_usd_used`). 403 with
   `details.reason="budget_exceeded"` if over.

### Coverage-denial response shape

```json
{
  "data": null,
  "error": {
    "code": "scope_not_entitled",
    "message": "Your plan doesn't cover questions about individual-employer deep-dives.",
    "details": {
      "requested_topic": "individual_employer_deep_dives",
      "requested_region": "borderplex",
      "plan_id": "workforce_pro_2026",
      "upgrade_url": "https://thewaifinder.com/pricing?from=scope_denial"
    }
  },
  "meta": null
}
```

Browser (chat widget) renders this as an assistant turn:
> "I can't answer that on your current plan — it covers labor demand
> and skills gaps, not individual-employer deep-dives. You can
> [upgrade here] or try rephrasing at the sector level."

### Rate limiting — nginx already handles this

`infra/edge/nginx/wfdos-platform.conf:38`:

```nginx
limit_req_zone $binary_remote_addr zone=platform_laborpulse:10m rate=60r/m;
```

Applied at `/api/laborpulse/` (line 184) with `burst=20 nodelay`.

Per-IP. Not per-tenant. **This is raw abuse protection, not quota
enforcement** — quota is the `monthly_query_budget` in entitlement
above, enforced inside the app. Keep both layers.

If nginx becomes the quota gate later (e.g. per-API-key zones), add
a second `limit_req_zone` on `$http_x_api_key` (already forwarded by
the proxy). Not needed today.

---

## Part 5 — JIE-side inventory (what the backend team has vs. needs)

From the explore pass over `job-intelligence-engine/`:

| Capability                         | Today                                    | Needed for LaborPulse |
|------------------------------------|------------------------------------------|-----------------------|
| `POST /analytics/query`            | Exists (`analytics/api/routes.py:307-310`) | ✓ reuse, add `conversation_id` |
| Framework                          | FastAPI                                  | ✓ no change |
| Multi-turn memory                  | **Missing** (only `correlation_id` for tracing) | **Add**: store per `conversation_id` |
| Region scoping in query            | **Missing** (endpoint accepts free-text only; `borderplex_subregion` exists in aggregates) | **Add**: `X-Tenant-Id` + region list → SQL filter |
| Topic / intent classification      | Exists per-request via LLM (`routing.py:437-438`) | ✓ reuse; wfd-os side also classifies for entitlement gating before the call |
| Output format                      | JSON (not SSE)                           | ✓ — wfd-os client change trivializes this |
| `AnalyticsQueryResponse` shape     | `{answer, evidence, confidence, cost_breakdown}` | Add `follow_up_questions[]`, `sql_generated`, `conversation_id` |
| Per-tenant accounting              | **Missing**                              | **Add or defer**: cost tracking by tenant (optional — wfd-os can do this from its own logs) |
| Per-API-key auth                   | Unknown — confirm                        | **Add if missing**: required for `X-API-Key` header |

---

## Part 6 — wfd-os-side inventory

| Capability                         | Today | Needed |
|------------------------------------|-------|--------|
| `/api/laborpulse/query` endpoint   | ✓ with mock + SSE-proxy branches | Replace SSE branch with JSON POST, ~20 line change in `client.py` |
| Chat widget                        | ✓ `ChatWidget.tsx` mounted globally; 6 personas | Add `workforce-development` to path→agent map (line 10-18) |
| `assistant-api` 7th persona        | 6 exist (student, employer, college, consulting, youth, staff) | **Add** `agents/assistant/workforce_agent.py` + registry entry (api.py line 105-112) |
| Agent tools                        | Per-persona `@tool()` decorators | Tools for workforce agent: `lp_query(question, conversation_id)`, `lp_feedback(conversation_id, rating)`, `get_entitlement_scope()` |
| Entitlement layer                  | **Missing** | **Add** `wfdos_common.entitlement` module (initial impl reads from `BrandConfig`; API-compatible with future billing service) |
| `@scope_gated` decorator           | **Missing** | **Add** alongside `@llm_gated` — composable |
| Question classifier                | **Missing** | **Add** `wfdos_common.classifier` — rule-based first, LLM fallback |
| Multi-turn storage                 | `agent_conversations` table in wfd-os schema (exists) | Wire to `agents/assistant/base.py` persistence path — already how the 6 agents store history |
| qa_feedback table                  | Exists (blocked on schema reconciliation — see `docs/database/jie-wfdos-schema-reconciliation.md`) | Unblock by landing the wfd-os schema in JIE's Postgres |

---

## Part 7 — Execution order (recommended)

Do these **independently** — each lands value on its own, each is
reversible.

1. **Unblock real data (Part 2)** — JIE exposes JSON endpoint,
   wfd-os client drops SSE parsing. Mock stays as fallback when
   `JIE_BASE_URL` is unset. 1–2 day job per side.
2. **Land schema reconciliation** — per
   `docs/database/jie-wfdos-schema-reconciliation.md`. Unblocks
   `qa_feedback` writes + any wfd-os-side tables the workforce agent
   needs. Standalone PR.
3. **Chat widget for LaborPulse (Part 3)** — new persona on
   assistant-api, delete/simplify the form page, update widget
   path map. 2–3 day job; zero JIE-side changes.
4. **Entitlement in `BrandConfig` (Part 4 hardcoded)** — add
   `entitlement` to `BrandConfig`, write `@scope_gated`, wire into
   `workforce_agent`. Borderplex has one hardcoded plan. 2-day job.
5. **Question classifier** — rule-based pass, LLM fallback. Wire
   into `@scope_gated`. 2-day job.
6. **Extract to `billing-api` service** — only when a second paying
   tenant exists AND self-serve onboarding is a real goal. Copy the
   entitlement JSON shape as the API contract. Week-long job.
7. **Stripe integration** — hangs off the billing service above.
   Only when CFA actually takes a card. Separate repo.

---

## Part 8 — Open design questions (not blocking)

1. **Shared conversation across persons?** If Gary (staff) and a
   workforce-development director at Borderplex both query LaborPulse
   for the same tenant, do they share history? Likely no (privacy),
   but needs a product call.
2. **Workforce-development can see across tenants?** CFA staff (Ritu,
   Gary) might want a multi-tenant view. Role `staff` already gets
   through the `@llm_gated(roles=...)` gate. Entitlement layer might
   need a per-role override.
3. **Language** — Borderplex is heavily Spanish-speaking. If the
   director asks in Spanish, does JIE synthesize in Spanish, or does
   wfd-os translate? Affects classifier + prompt design.
4. **Evidence-card source provenance** — currently free-text `source`
   field (`"lightcast_postings_2026Q1"`). Long-term, each evidence
   card probably wants `{source_type, source_id, url, as_of_date}`
   so the browser can link to the underlying dataset.
5. **SQL exposure** — today `sql_generated` is returned in the
   response. Safe for workforce-development directors, not
   necessarily for all tiers. Make it an `entitlement.features.sql_exposure`
   flag.
6. **Feedback loop to JIE** — `qa_feedback` rows currently land in
   wfd-os Postgres only. Should they also flow back to JIE for
   model-evaluation signal? Probably yes, async, batched nightly.

---

## References

- `docs/laborpulse.md` — canonical architecture (read this first).
- `docs/database/jie-wfdos-schema-reconciliation.md` — blocker for
  `qa_feedback` + workforce agent's own tables.
- `docs/refactor/phase-5-exit-report.md §13` — the live smoke steps
  (§13b/d/f currently pass against mock; §13e needs schema reconciliation).
- `~/.claude/CLAUDE.md` — LLM provider policy (Azure OpenAI default)
  + JIE pipeline-audit-table protection rules.
- Contract smoke script: `scripts/smoke/laborpulse/mock_query.py`
  (asserts `[MOCK]` marker + `confidence == "mock"` + 8–14s wall-clock).
  Update this to also cover the live path once Part 2 lands.
