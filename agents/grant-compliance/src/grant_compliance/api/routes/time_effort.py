"""/time-effort — drafts and certifications."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.agents.time_effort import TimeEffortAgent
from grant_compliance.api.schemas import TimeCertificationCertify, TimeCertificationOut
from grant_compliance.db.models import Employee, Grant, TimeCertification
from grant_compliance.db.session import get_db

router = APIRouter(prefix="/time-effort", tags=["time-effort"])


@router.get("/certifications", response_model=list[TimeCertificationOut])
def list_certifications(db: Session = Depends(get_db)) -> list[TimeCertification]:
    stmt = select(TimeCertification).order_by(
        TimeCertification.period_year.desc(),
        TimeCertification.period_month.desc(),
    )
    return list(db.execute(stmt).scalars())


@router.post("/draft", response_model=TimeCertificationOut)
def draft_certification(
    employee_id: str,
    period_year: int,
    period_month: int,
    grant_ids: list[str],
    db: Session = Depends(get_db),
) -> TimeCertification:
    """Draft a certification for an employee/period across the given grants."""
    employee = db.get(Employee, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    grants = [db.get(Grant, gid) for gid in grant_ids]
    if not all(grants):
        raise HTTPException(status_code=404, detail="One or more grants not found")

    agent = TimeEffortAgent(db)
    cert = agent.draft_certification(
        employee=employee,
        period_year=period_year,
        period_month=period_month,
        assigned_grants=grants,
    )
    db.commit()
    return cert


@router.post("/certifications/{cert_id}/certify", response_model=TimeCertificationOut)
def certify(
    cert_id: str,
    body: TimeCertificationCertify,
    db: Session = Depends(get_db),
) -> TimeCertification:
    cert = db.get(TimeCertification, cert_id)
    if not cert:
        raise HTTPException(status_code=404, detail="Certification not found")
    if cert.certified_at is not None:
        raise HTTPException(status_code=409, detail="Already certified")

    agent = TimeEffortAgent(db)
    try:
        agent.certify(
            cert,
            certifier_email=body.certifier_email,
            method=body.method,
            adjustments=body.adjustments,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    db.commit()
    return cert
