"""/reports — generate and finalize funder report drafts."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.agents.reporting import ReportingAgent
from grant_compliance.api.schemas import ReportDraftOut, ReportDraftRequest
from grant_compliance.audit.log import write_entry
from grant_compliance.db.models import Grant, ReportDraft
from grant_compliance.db.session import get_db

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("", response_model=list[ReportDraftOut])
def list_reports(db: Session = Depends(get_db)) -> list[ReportDraft]:
    return list(db.execute(select(ReportDraft).order_by(ReportDraft.generated_at.desc())).scalars())


@router.post("", response_model=ReportDraftOut)
def generate_report(body: ReportDraftRequest, db: Session = Depends(get_db)) -> ReportDraft:
    grant = db.get(Grant, body.grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")

    agent = ReportingAgent(db)
    try:
        if body.report_type == "SF-425":
            draft = agent.draft_sf425(grant, body.period_start, body.period_end)
        else:
            draft = agent.draft_foundation_narrative(grant, body.period_start, body.period_end)
    except RuntimeError as e:
        # Blocker flags exist
        raise HTTPException(status_code=409, detail=str(e)) from e
    db.commit()
    return draft


@router.get("/{report_id}", response_model=ReportDraftOut)
def get_report(report_id: str, db: Session = Depends(get_db)) -> ReportDraft:
    report = db.get(ReportDraft, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report


@router.post("/{report_id}/finalize", response_model=ReportDraftOut)
def finalize_report(
    report_id: str,
    finalizer_email: str,
    db: Session = Depends(get_db),
) -> ReportDraft:
    """Mark a report draft as finalized. After this it should be exported and
    submitted to the funder out-of-band; we don't auto-submit.
    """
    report = db.get(ReportDraft, report_id)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    if report.finalized_at is not None:
        raise HTTPException(status_code=409, detail="Already finalized")

    report.finalized_at = datetime.now(timezone.utc)
    report.finalized_by = finalizer_email

    write_entry(
        db=db,
        actor=finalizer_email,
        actor_kind="human",
        action="report.finalize",
        target_type="report_draft",
        target_id=report.id,
        outputs={"snapshot_id": report.snapshot_id, "report_type": report.report_type},
    )
    db.commit()
    return report
