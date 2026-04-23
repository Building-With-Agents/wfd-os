"""/compliance — flags and the rule scanner."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.agents.compliance import ComplianceMonitor
from grant_compliance.api.schemas import ComplianceFlagOut, FlagResolution
from grant_compliance.audit.log import write_entry
from grant_compliance.compliance.audit_dimensions import DIMENSIONS
from grant_compliance.compliance.dimension_readiness import (
    COMPUTED_DIMENSIONS,
    COMPUTE_FUNCTIONS,
)
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


@router.get("/dimensions")
def list_dimensions(db: Session = Depends(get_db)) -> dict:
    """Return all six audit-readiness dimensions with computed percentages.

    Each entry carries the canonical static metadata (from
    `audit_dimensions.DIMENSIONS`) plus:
      - `readiness_pct`: integer percent, or null for placeholder
        dimensions / computed dimensions whose denominator is zero.
      - `status`: "computed" or "placeholder". A "computed" dimension
        with `readiness_pct=null` just means no data yet (e.g. no
        recent scans); a "placeholder" dimension has no real formula
        in v1.2 and will not get one until its data model lands.

    Consumed by the Finance Cockpit's Audit Readiness tab. See
    `docs/audit_readiness_tab_spec.md` for the computation formulas.
    """
    dimensions_out: list[dict] = []
    for d in DIMENSIONS:
        compute_fn = COMPUTE_FUNCTIONS[d.id]
        pct = compute_fn(db)
        status = "computed" if d.id in COMPUTED_DIMENSIONS else "placeholder"
        dimensions_out.append({
            "id": d.id,
            "title": d.title,
            "what_auditors_look_for": d.what_auditors_look_for,
            "cfr_citations": list(d.cfr_citations),
            "compliance_supplement_area": d.compliance_supplement_area,
            "owner_role": d.owner_role,
            "default_tone": d.default_tone,
            "readiness_pct": pct,
            "status": status,
        })
    return {
        "dimensions": dimensions_out,
        "computed_at": datetime.now(timezone.utc).isoformat(),
    }
