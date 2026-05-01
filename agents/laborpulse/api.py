"""LaborPulse — FastAPI service (port 8015).

  POST /api/laborpulse/query     — workforce-development Q&A, request/
                                    response JSON. Proxies to JIE
                                    `POST /analytics/query` and returns
                                    the assembled answer.
  POST /api/laborpulse/feedback  — thumbs-up/down write to qa_feedback
  GET  /api/health               — liveness

Tiering (#25):
  - /query + /feedback are @llm_gated; roles allow workforce-development
    + staff + admin.
  - /health is @public.

Mock mode:
  When `settings.jie.base_url` is empty, `/api/laborpulse/query` returns
  a canned Borderplex-flavored answer after an 8-12s simulated synthesis
  delay. This is the dev + demo-rehearsal path — it keeps the frontend
  rendering realistically without requiring a live JIE. The mock runs
  only when `JIE_BASE_URL` is unset; setting it (even to an unreachable
  host) switches to the real-proxy path, which then 503s if JIE is down.
  Each mock invocation logs `laborpulse.query.mock` at INFO so a
  production deploy accidentally running in mock mode is greppable.

Run:
  uvicorn agents.laborpulse.api:app --port 8015
"""

from __future__ import annotations

import asyncio
import random
import uuid
from typing import Any, Optional

import psycopg2
import psycopg2.extras
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.laborpulse.client import query as jie_query
from wfdos_common.auth import (
    Session,
    SessionMiddleware,
    llm_gated,
    require_role,
)
from wfdos_common.config import PG_CONFIG, settings
from wfdos_common.errors import ValidationFailure, install_error_handlers
from wfdos_common.logging import (
    RequestContextMiddleware,
    configure as configure_logging,
    current_context,
    get_logger,
)
from wfdos_common.tenancy import TenantResolutionMiddleware

configure_logging(service_name="laborpulse")
log = get_logger(__name__)


app = FastAPI(title="LaborPulse Q&A Proxy", version="0.1.0")

# Middleware order matters: request-context first (so all downstream
# logs + envelopes pick up request_id), then tenancy (populates
# request.state.tenant_id), then session (populates request.state.user),
# then CORS last so the preflight response still gets request-id
# headers.
app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    TenantResolutionMiddleware,
    default_tenant_id=settings.tenancy.default_tenant_id,
)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.auth.secret_key,
    cookie_name=settings.auth.cookie_name,
    max_age_seconds=settings.auth.session_ttl_seconds,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.platform.allowed_origins,
    allow_origin_regex=settings.platform.allowed_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)
install_error_handlers(app)


# ---------------------------------------------------------------------------
# Request / response shapes
# ---------------------------------------------------------------------------


_ALLOWED_ROLES = ("workforce-development", "staff", "admin")


class QueryBody(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    # Ties a follow-up chip click back to the original turn for JIE-side
    # memory continuity. Optional — first question in a conversation
    # omits it.
    conversation_id: Optional[str] = Field(default=None, max_length=128)


class QueryResponse(BaseModel):
    conversation_id: Optional[str] = None
    answer: str
    evidence: list[dict[str, Any]] = Field(default_factory=list)
    confidence: Optional[str] = None
    follow_up_questions: list[str] = Field(default_factory=list)
    cost_usd: Optional[float] = None
    sql_generated: Optional[str] = None


class FeedbackBody(BaseModel):
    conversation_id: str = Field(min_length=1, max_length=128)
    question: str = Field(min_length=1, max_length=4000)
    rating: int = Field(description="+1 for thumbs-up, -1 for thumbs-down")
    answer_snapshot: Optional[str] = Field(default=None, max_length=16000)
    comment: Optional[str] = Field(default=None, max_length=4000)
    cost_usd: Optional[float] = None
    confidence: Optional[str] = Field(
        default=None,
        description="JIE-reported: 'low' | 'medium' | 'high'",
        max_length=16,
    )


class FeedbackResponse(BaseModel):
    ok: bool
    id: Optional[int] = None


class HealthResponse(BaseModel):
    status: str
    service: str
    port: int
    jie_configured: bool


# ---------------------------------------------------------------------------
# Mock answer — used when JIE_BASE_URL is unset
# ---------------------------------------------------------------------------


def _mock_answer_for(question: str) -> dict[str, Any]:
    """Return a Borderplex-flavored canned answer shaped like QueryResponse.

    The answer text echoes the question so a demo feels conversational;
    confidence is deliberately the literal string "mock" so consumers +
    grep can distinguish mock from real responses. The `answer` body also
    contains the marker `[MOCK]` for the same reason.
    """
    return {
        "conversation_id": f"mock-{uuid.uuid4()}",
        "answer": (
            f"[MOCK] Here's a simulated answer to: {question}\n\n"
            "Across the Borderplex region in Q1 2026 the strongest job-posting "
            "growth was in Manufacturing (+18% YoY, driven by nearshoring to "
            "Ciudad Juárez) and Healthcare Support (+12%). Digital roles — "
            "particularly in Customer Service, Data Analysis, and IT Support "
            "— grew 9% as logistics and healthcare employers modernized "
            "back-office workflows. El Paso remains the posting volume "
            "leader, but Doña Ana County saw the fastest percentage growth "
            "in healthcare. Training pipelines are tightest for bilingual "
            "medical-support roles."
        ),
        "evidence": [
            {
                "source": "lightcast_postings_2026Q1",
                "text": "Borderplex region: 12,840 active postings, +14% vs Q4 2025.",
            },
            {
                "source": "bls_oes_nm_doña_ana",
                "text": "Healthcare Support occupations in Doña Ana grew 11.8% YoY.",
            },
            {
                "source": "cfa_skills_registry",
                "text": "Bilingual + medical-terminology combo scarce in supply pool.",
            },
        ],
        "confidence": "mock",
        "follow_up_questions": [
            "Which employers drove the Q1 manufacturing growth?",
            "What are the median wages for bilingual medical-support roles?",
            "How does Doña Ana's healthcare growth compare to El Paso's?",
        ],
        "cost_usd": 0.0,
        "sql_generated": (
            "-- [MOCK] representative query\n"
            "SELECT industry, COUNT(*) AS postings, ... "
            "FROM jobs_2026q1 WHERE region IN ('el_paso','dona_ana','cd_juarez') "
            "GROUP BY industry ORDER BY postings DESC;"
        ),
    }


async def _mock_query(question: str) -> dict[str, Any]:
    """Sleep for a realistic JIE synthesis time (8-12s) then return the
    canned mock. Log so accidental prod-mode-mock deploys are findable."""
    delay = random.uniform(8.0, 12.0)
    log.info("laborpulse.query.mock", delay_seconds=round(delay, 2))
    await asyncio.sleep(delay)
    return _mock_answer_for(question)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/api/laborpulse/query", response_model=QueryResponse)
@llm_gated(roles=_ALLOWED_ROLES)
async def query_endpoint(
    request: Request,
    body: QueryBody,
    user: Session = Depends(require_role(*_ALLOWED_ROLES)),
) -> QueryResponse:
    """Post the director's question to JIE, assemble the SSE body into a
    single response dict, return it. If JIE is not configured on this
    host, return a Borderplex-flavored mock answer after a simulated
    synthesis delay. All errors flow through the #29 envelope handler.
    """
    tenant_id = getattr(request.state, "tenant_id", settings.tenancy.default_tenant_id)
    request_id = current_context().get("request_id")

    log.info(
        "laborpulse.query.start",
        tenant_id=tenant_id,
        user_email=user.email,
        user_role=user.role,
        question_preview=body.question[:120],
        mode="mock" if not settings.jie.base_url else "live",
    )

    if not settings.jie.base_url:
        result = await _mock_query(body.question)
    else:
        result = await jie_query(
            base_url=settings.jie.base_url,
            api_key=settings.jie.api_key,
            question=body.question,
            tenant_id=tenant_id,
            user_email=user.email,
            request_id=request_id,
            conversation_id=body.conversation_id,
            timeout_seconds=float(settings.jie.streaming_read_timeout_seconds),
        )

    log.info(
        "laborpulse.query.complete",
        tenant_id=tenant_id,
        user_email=user.email,
        conversation_id=result.get("conversation_id"),
        answer_length=len(result.get("answer") or ""),
        evidence_count=len(result.get("evidence") or []),
        cost_usd=result.get("cost_usd"),
    )
    return QueryResponse(**result)


@app.post("/api/laborpulse/feedback", response_model=FeedbackResponse)
@llm_gated(roles=_ALLOWED_ROLES)
def feedback_endpoint(
    request: Request,
    body: FeedbackBody,
    user: Session = Depends(require_role(*_ALLOWED_ROLES)),
) -> FeedbackResponse:
    """Write one qa_feedback row. Always 200 on success; validation
    errors on bad rating flow through the envelope handler."""
    if body.rating not in (-1, 1):
        raise ValidationFailure(
            "rating must be -1 or 1",
            details={"field": "rating", "actual": body.rating},
        )

    tenant_id = getattr(request.state, "tenant_id", settings.tenancy.default_tenant_id)

    conn = psycopg2.connect(**PG_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO qa_feedback (
                    tenant_id, user_email, user_role, conversation_id,
                    question, answer_snapshot, rating, comment,
                    cost_usd, confidence
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    tenant_id,
                    user.email,
                    user.role,
                    body.conversation_id,
                    body.question,
                    body.answer_snapshot,
                    body.rating,
                    body.comment,
                    body.cost_usd,
                    body.confidence,
                ),
            )
            row = cur.fetchone()
            feedback_id = row[0] if row else None
            conn.commit()
    finally:
        conn.close()

    log.info(
        "laborpulse.feedback.written",
        feedback_id=feedback_id,
        tenant_id=tenant_id,
        user_email=user.email,
        user_role=user.role,
        rating=body.rating,
        conversation_id=body.conversation_id,
    )
    return FeedbackResponse(ok=True, id=feedback_id)


@app.get("/api/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="laborpulse",
        port=8012,
        jie_configured=bool(settings.jie.base_url),
    )
