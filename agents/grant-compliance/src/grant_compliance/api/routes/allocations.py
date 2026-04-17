"""/allocations — the human review queue for proposed allocations.

This is the human-in-the-loop gate. Nothing posts to QB or feeds a report
until approved here.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.audit.log import write_entry
from grant_compliance.api.schemas import (
    AllocationDecision,
    AllocationOut,
    AllocationProposeManual,
)
from grant_compliance.db.models import Allocation, AllocationStatus, Transaction
from grant_compliance.db.session import get_db

router = APIRouter(prefix="/allocations", tags=["allocations"])


@router.get("/queue", response_model=list[AllocationOut])
def review_queue(db: Session = Depends(get_db)) -> list[Allocation]:
    """All proposed allocations awaiting human decision, oldest first."""
    stmt = (
        select(Allocation)
        .where(Allocation.status == AllocationStatus.proposed)
        .order_by(Allocation.proposed_at.asc())
    )
    return list(db.execute(stmt).scalars())


@router.post("/manual", response_model=AllocationOut)
def propose_manual(
    body: AllocationProposeManual, db: Session = Depends(get_db)
) -> Allocation:
    """A human directly proposes an allocation (no agent involvement)."""
    txn = db.get(Transaction, body.transaction_id)
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    allocation = Allocation(
        transaction_id=body.transaction_id,
        grant_id=body.grant_id,
        amount_cents=body.amount_cents,
        budget_category=body.budget_category,
        rationale=body.rationale,
        proposed_by=body.proposer_email,
        status=AllocationStatus.proposed,
    )
    db.add(allocation)
    db.flush()
    write_entry(
        db=db,
        actor=body.proposer_email,
        actor_kind="human",
        action="allocation.propose.manual",
        target_type="allocation",
        target_id=allocation.id,
        inputs=body.model_dump(),
    )
    db.commit()
    return allocation


@router.post("/{allocation_id}/decide", response_model=AllocationOut)
def decide(
    allocation_id: str,
    body: AllocationDecision,
    db: Session = Depends(get_db),
) -> Allocation:
    """Approve or reject a proposed allocation. Recorded in the audit log."""
    allocation = db.get(Allocation, allocation_id)
    if not allocation:
        raise HTTPException(status_code=404, detail="Allocation not found")
    if allocation.status != AllocationStatus.proposed:
        raise HTTPException(
            status_code=409, detail=f"Allocation is already {allocation.status.value}"
        )

    if body.decision == "approve":
        if body.adjusted_amount_cents is not None:
            allocation.amount_cents = body.adjusted_amount_cents
        if body.adjusted_budget_category is not None:
            allocation.budget_category = body.adjusted_budget_category
        allocation.status = AllocationStatus.approved
    else:
        allocation.status = AllocationStatus.rejected

    allocation.decided_by = body.decider_email
    allocation.decided_at = datetime.now(timezone.utc)

    write_entry(
        db=db,
        actor=body.decider_email,
        actor_kind="human",
        action=f"allocation.{body.decision}",
        target_type="allocation",
        target_id=allocation.id,
        inputs=body.model_dump(),
        note=body.note,
    )
    db.commit()
    return allocation
