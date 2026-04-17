"""/compliance — flags and the rule scanner."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.agents.compliance import ComplianceMonitor
from grant_compliance.api.schemas import ComplianceFlagOut, FlagResolution
from grant_compliance.audit.log import write_entry
from grant_compliance.db.models import ComplianceFlag, FlagStatus
from grant_compliance.db.session import get_db

router = APIRouter(prefix="/compliance", tags=["compliance"])


@router.get("/flags", response_model=list[ComplianceFlagOut])
def list_flags(
    status: str | None = None,
    severity: str | None = None,
    db: Session = Depends(get_db),
) -> list[ComplianceFlag]:
    stmt = select(ComplianceFlag).order_by(ComplianceFlag.raised_at.desc())
    if status:
        stmt = stmt.where(ComplianceFlag.status == status)
    if severity:
        stmt = stmt.where(ComplianceFlag.severity == severity)
    return list(db.execute(stmt).scalars())


@router.post("/scan")
def scan_all(db: Session = Depends(get_db)) -> dict[str, int]:
    """Run the rule engine over every transaction. Idempotent."""
    monitor = ComplianceMonitor(db)
    new_flags = monitor.scan_all_unscanned()
    db.commit()
    return {"new_flags": new_flags}


@router.post("/flags/{flag_id}/resolve", response_model=ComplianceFlagOut)
def resolve_flag(
    flag_id: str,
    body: FlagResolution,
    db: Session = Depends(get_db),
) -> ComplianceFlag:
    flag = db.get(ComplianceFlag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")

    status_map = {
        "resolve": FlagStatus.resolved,
        "waive": FlagStatus.waived,
        "acknowledge": FlagStatus.acknowledged,
    }
    flag.status = status_map[body.resolution]
    if body.resolution in ("resolve", "waive"):
        flag.resolved_at = datetime.now(timezone.utc)
        flag.resolved_by = body.resolver_email
    flag.resolution_note = body.note

    write_entry(
        db=db,
        actor=body.resolver_email,
        actor_kind="human",
        action=f"compliance.flag.{body.resolution}",
        target_type="compliance_flag",
        target_id=flag.id,
        inputs=body.model_dump(),
    )
    db.commit()
    return flag


@router.get("/flags/{flag_id}/explain")
def explain_flag(flag_id: str, db: Session = Depends(get_db)) -> dict[str, str]:
    """Use the LLM to draft a plain-language explanation of the flag."""
    flag = db.get(ComplianceFlag, flag_id)
    if not flag:
        raise HTTPException(status_code=404, detail="Flag not found")
    monitor = ComplianceMonitor(db)
    text = monitor.explain_flag(flag)
    db.commit()
    return {"explanation": text}
