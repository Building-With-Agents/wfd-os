"""/compliance/requirements — Mode A generation, current-set lookup,
historical-set lookup, and Mode B Q&A endpoints.

Spec: agents/grant-compliance/docs/compliance_requirements_agent_spec.md

Endpoints:
  POST /compliance/requirements/generate
       — Mode A. Body: { grant_id, scope?: Scope, force_opus?: bool, invoked_by?: str }.
         Returns the new set_id and a summary.

  GET  /compliance/requirements/current?grant_id=...
       — Returns the current ComplianceRequirementsSet for the grant.

  GET  /compliance/requirements/sets/{set_id}
       — Returns a specific historical set.

  POST /compliance/requirements/qa
       — Mode B. Body: { question, context_hints?, asked_by?, grant_id? }.
         Returns the structured QAResponse.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.compliance_requirements_agent.agent import (
    AgentValidationError,
    ComplianceRequirementsAgent,
)
from grant_compliance.compliance_requirements_agent.schemas import (
    ComplianceArea,
    QARequest,
    QAResponse,
    Scope,
)
from grant_compliance.db.models import (
    ComplianceRequirementRow,
    ComplianceRequirementsSet,
    Grant,
)
from grant_compliance.db.session import get_db


router = APIRouter(prefix="/compliance/requirements", tags=["compliance-requirements"])


# ---------------------------------------------------------------------------
# Request / response shapes (route-level, distinct from agent's domain models)
# ---------------------------------------------------------------------------


class GenerateRequest(BaseModel):
    grant_id: str
    scope: Scope | None = None
    force_opus: bool = Field(
        default=False,
        description="When true, request the Opus alias for higher-quality "
        "structured output. Per spec §'LLM model selection', considered for "
        "the initial Mode A generation only.",
    )
    invoked_by: str | None = None


class GenerateResponse(BaseModel):
    set_id: str
    requirement_count: int
    generated_at: datetime
    model_name: str
    superseded_set_id: str | None = None
    notes: list[str] = []


class RequirementOut(BaseModel):
    requirement_id: str
    compliance_area: str
    regulatory_citation: str
    regulatory_text_excerpt: str
    applicability: dict
    requirement_summary: str
    documentation_artifacts_required: list[str]
    documentation_form_guidance: str | None
    cfa_specific_application: str | None
    severity_if_missing: str

    class Config:
        from_attributes = True


class RequirementsSetOut(BaseModel):
    id: str
    grant_id: str
    generated_at: datetime
    scope: dict
    regulatory_corpus_version: str
    grant_context: dict
    model_name: str
    is_current: bool
    superseded_by_id: str | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_notes: str | None
    requirements: list[RequirementOut]

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Mode A — generate
# ---------------------------------------------------------------------------


@router.post("/generate", response_model=GenerateResponse)
def generate(
    req: GenerateRequest,
    db: Session = Depends(get_db),
) -> GenerateResponse:
    """Trigger a Mode A generation. Synchronous in v1 — the call returns
    when the LLM has produced + validated + persisted the new set.

    The caller should expect this to take 30s–2min depending on the model
    and scope size. v1.1 may move to a job-queue model with a separate
    polling endpoint.
    """
    grant = db.get(Grant, req.grant_id)
    if grant is None:
        raise HTTPException(status_code=404, detail=f"Grant {req.grant_id!r} not found")

    scope = req.scope or Scope(
        compliance_areas=list(ComplianceArea),
        description="Default scope: all in-scope compliance areas.",
    )

    # Find the prior current set (if any) so we can report what got
    # superseded.
    prior_current = db.execute(
        select(ComplianceRequirementsSet).where(
            ComplianceRequirementsSet.grant_id == req.grant_id,
            ComplianceRequirementsSet.is_current.is_(True),
        )
    ).scalar_one_or_none()
    superseded_id = prior_current.id if prior_current else None

    agent = ComplianceRequirementsAgent(db)
    try:
        new_set = agent.generate_set(
            grant=grant,
            scope=scope,
            force_opus=req.force_opus,
            invoked_by=req.invoked_by,
        )
    except AgentValidationError as exc:
        # Validation-failed audit_log entry was already written by the agent.
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Mode A generation produced output that failed validation: {exc}",
        )
    except Exception as exc:
        # Catch-all so the failure-path audit_log entry written by
        # Agent.llm() is preserved when the LLM raises (auth, credit,
        # rate-limit, transient HTTP). Without this, the SQLAlchemy
        # session rolls back when the request handler exits without
        # committing — and the audit row goes with it.
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Mode A generation failed: {type(exc).__name__}: {exc}",
        )
    db.commit()

    notes: list[str] = []
    if any(d.verification == "skeleton" for d in agent.corpus.documents):
        notes.append(
            "Corpus contains skeleton (un-populated) sections. The agent's "
            "output reflects the populated portion of the corpus only. See "
            "agents/grant-compliance/data/regulatory_corpus/README.md "
            "v1.1 follow-ups for the gap list."
        )

    return GenerateResponse(
        set_id=new_set.id,
        requirement_count=len(new_set.requirements),
        generated_at=new_set.generated_at,
        model_name=new_set.model_name,
        superseded_set_id=superseded_id,
        notes=notes,
    )


# ---------------------------------------------------------------------------
# Current + historical lookup
# ---------------------------------------------------------------------------


@router.get("/current", response_model=RequirementsSetOut)
def get_current(
    grant_id: str = Query(..., description="Grant id whose current set to return"),
    db: Session = Depends(get_db),
) -> ComplianceRequirementsSet:
    current = db.execute(
        select(ComplianceRequirementsSet).where(
            ComplianceRequirementsSet.grant_id == grant_id,
            ComplianceRequirementsSet.is_current.is_(True),
        )
    ).scalar_one_or_none()
    if current is None:
        raise HTTPException(
            status_code=404,
            detail=f"No current ComplianceRequirementsSet for grant {grant_id!r}. "
            f"Run POST /compliance/requirements/generate first.",
        )
    return current


@router.get("/sets/{set_id}", response_model=RequirementsSetOut)
def get_set(
    set_id: str,
    db: Session = Depends(get_db),
) -> ComplianceRequirementsSet:
    obj = db.get(ComplianceRequirementsSet, set_id)
    if obj is None:
        raise HTTPException(status_code=404, detail=f"Set {set_id!r} not found")
    return obj


@router.get("/sets", response_model=list[dict])
def list_sets(
    grant_id: str = Query(...),
    db: Session = Depends(get_db),
) -> list[dict]:
    """List all sets for a grant, newest first. Returns summaries only."""
    rows = db.execute(
        select(ComplianceRequirementsSet)
        .where(ComplianceRequirementsSet.grant_id == grant_id)
        .order_by(ComplianceRequirementsSet.generated_at.desc())
    ).scalars().all()
    return [
        {
            "id": r.id,
            "generated_at": r.generated_at.isoformat(),
            "is_current": r.is_current,
            "superseded_by_id": r.superseded_by_id,
            "model_name": r.model_name,
            "regulatory_corpus_version": r.regulatory_corpus_version,
            "requirement_count": len(r.requirements),
            "reviewed_by": r.reviewed_by,
            "reviewed_at": r.reviewed_at.isoformat() if r.reviewed_at else None,
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# Mode B — Q&A
# ---------------------------------------------------------------------------


class QAEndpointRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    context_hints: dict | None = None
    asked_by: str | None = None
    grant_id: str | None = Field(
        default=None,
        description="Optional. When provided, the agent loads this grant's "
        "current ComplianceRequirementsSet and includes a summary in the "
        "prompt so Mode B can reference Mode A output coherently.",
    )


@router.post("/qa", response_model=QAResponse)
def qa(
    req: QAEndpointRequest,
    db: Session = Depends(get_db),
) -> QAResponse:
    """Mode B Q&A. Returns a structured response. Refusals (legal-opinion
    or out-of-scope questions) come back with `refused: true` rather than
    HTTP error — the structured refusal is itself the answer per spec.
    """
    grant: Optional[Grant] = None
    if req.grant_id:
        grant = db.get(Grant, req.grant_id)
        if grant is None:
            raise HTTPException(status_code=404, detail=f"Grant {req.grant_id!r} not found")

    agent_request = QARequest(
        question=req.question,
        context_hints=req.context_hints,
        asked_by=req.asked_by,
    )
    agent = ComplianceRequirementsAgent(db)
    try:
        response, _log_row = agent.answer_question(request=agent_request, grant=grant)
    except AgentValidationError as exc:
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Mode B response failed validation: {exc}",
        )
    except Exception as exc:
        # Catch-all so the failure-path audit_log entry written by
        # Agent.llm() is preserved on transient API errors.
        db.commit()
        raise HTTPException(
            status_code=502,
            detail=f"Mode B query failed: {type(exc).__name__}: {exc}",
        )
    db.commit()
    return response
