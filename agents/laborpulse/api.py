"""LaborPulse — FastAPI service (port 8012).

  POST /api/laborpulse/query     — streaming SSE proxy to JIE
  POST /api/laborpulse/feedback  — thumbs-up/down write to qa_feedback
  GET  /api/health               — liveness

Tiering (#25):
  - /query + /feedback are @llm_gated; roles allow workforce-development
    + staff + admin.
  - /health is @public.

The query route returns a FastAPI StreamingResponse. wfd-os never parses
JIE's SSE frames — they're forwarded byte-for-byte so the frontend sees
exactly what JIE produced. The feedback route writes a row to
qa_feedback in the wfd-os Postgres (system-of-record) tagged with the
resolved tenant_id + user_email + user_role.

Run:
  uvicorn agents.laborpulse.api:app --port 8012
"""

from __future__ import annotations

from typing import Optional

import psycopg2
import psycopg2.extras
from fastapi import Depends, FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from agents.laborpulse.client import stream_query
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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "https://platform.thewaifinder.com",
        "https://talent.borderplexwfs.org",
    ],
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


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@app.post("/api/laborpulse/query")
@llm_gated(roles=_ALLOWED_ROLES)
async def query_endpoint(
    request: Request,
    body: QueryBody,
    user: Session = Depends(require_role(*_ALLOWED_ROLES)),
):
    """Proxy the question to JIE and stream SSE back to the client."""
    tenant_id = getattr(request.state, "tenant_id", settings.tenancy.default_tenant_id)
    request_id = current_context().get("request_id")

    log.info(
        "laborpulse.query.start",
        tenant_id=tenant_id,
        user_email=user.email,
        user_role=user.role,
        question_preview=body.question[:120],
    )

    # Peek the first chunk synchronously so any startup failure (missing
    # base_url, JIE unreachable, JIE 5xx, JIE 4xx) surfaces BEFORE we
    # hand control to StreamingResponse. After headers are flushed, it
    # is too late to route an exception through the envelope handler —
    # the client just sees a truncated body or a bare 500. This peek is
    # the minimum ceremony that lets the #29 envelope still catch
    # upstream errors cleanly.
    gen = stream_query(
        base_url=settings.jie.base_url,
        api_key=settings.jie.api_key,
        question=body.question,
        tenant_id=tenant_id,
        user_email=user.email,
        request_id=request_id,
        conversation_id=body.conversation_id,
        timeout_seconds=float(settings.jie.streaming_read_timeout_seconds),
    )
    first_chunk = await gen.__anext__()

    async def _relay():
        yield first_chunk
        async for chunk in gen:
            yield chunk

    return StreamingResponse(
        _relay(),
        media_type="text/event-stream",
        headers={
            # Disable nginx buffering explicitly so the edge can't
            # accidentally hold chunks even if proxy_buffering isn't off.
            "X-Accel-Buffering": "no",
            "Cache-Control": "no-cache",
        },
    )


@app.post("/api/laborpulse/feedback")
@llm_gated(roles=_ALLOWED_ROLES)
def feedback_endpoint(
    request: Request,
    body: FeedbackBody,
    user: Session = Depends(require_role(*_ALLOWED_ROLES)),
):
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
    return {"ok": True, "id": feedback_id}


@app.get("/api/health")
def health():
    jie_configured = bool(settings.jie.base_url)
    return {
        "status": "ok",
        "service": "laborpulse",
        "port": 8012,
        "jie_configured": jie_configured,
    }
