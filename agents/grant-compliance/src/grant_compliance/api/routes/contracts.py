"""/contracts — the canonical inventory of K8341 third-party agreements.

Spec: agents/grant-compliance/docs/contracts_inventory_spec.md.
Bootstrap (Excel-driven initial population) lives in
grant_compliance.contracts_bootstrap; the routes here serve API-driven
reads and the (single-row) API-driven mutations the spec scopes for v1.

Audit log discipline: every Contract mutation writes through the
service layer (grant_compliance.contracts_bootstrap.importer.*) which
issues the audit_log entries. Routes here are thin — they parse the
request body, build a ContractRecord, and delegate.
"""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.api.schemas import (
    ContractDetailOut,
    ContractIn,
    ContractOut,
    ContractReconciliationLineOut,
    ContractReconciliationOut,
)
from grant_compliance.contracts_bootstrap.importer import (
    ImporterError,
    create_contract_from_record,
    update_contract_from_record,
)
from grant_compliance.contracts_bootstrap.reconciliation import (
    compute_reconciliation,
)
from grant_compliance.contracts_bootstrap.schemas import ContractRecord
from grant_compliance.db.models import (
    ComplianceClassification,
    Contract,
    ContractStatus,
    ContractType,
    ProcurementMethod,
)
from grant_compliance.db.session import get_db


router = APIRouter(prefix="/contracts", tags=["contracts"])


# Threshold constants per the spec §"Computed fields".
SIMPLIFIED_ACQUISITION_THRESHOLD_CENTS = 25_000_000  # $250,000
MICRO_PURCHASE_THRESHOLD_CENTS = 1_000_000  # $10,000


# ---------- list ----------


@router.get("", response_model=list[ContractOut])
def list_contracts(
    grant_id: str = Query(..., description="Grant UUID."),
    contract_type: Optional[ContractType] = Query(None),
    classification: Optional[ComplianceClassification] = Query(None),
    status: Optional[ContractStatus] = Query(None),
    procurement_method: Optional[ProcurementMethod] = Query(None),
    db: Session = Depends(get_db),
) -> list[ContractOut]:
    """List contracts for a grant, optionally filtered.

    Filters are AND-combined. Use the cockpit's filter bar for OR
    semantics — the API operates one-dimension-at-a-time.
    """
    stmt = select(Contract).where(Contract.grant_id == grant_id)
    if contract_type is not None:
        stmt = stmt.where(Contract.contract_type == contract_type)
    if classification is not None:
        stmt = stmt.where(Contract.compliance_classification == classification)
    if status is not None:
        stmt = stmt.where(Contract.status == status)
    if procurement_method is not None:
        stmt = stmt.where(Contract.procurement_method == procurement_method)
    stmt = stmt.order_by(Contract.current_contract_value_cents.desc())

    rows = list(db.execute(stmt).scalars())
    return [_to_out(c) for c in rows]


# ---------- detail ----------


@router.get("/reconciliation", response_model=ContractReconciliationOut)
def reconciliation(
    grant_id: str = Query(..., description="Grant UUID."),
    db: Session = Depends(get_db),
) -> ContractReconciliationOut:
    """Amendment 1 reconciliation for a grant.

    Computed at query time — no stored snapshot. Per the spec, drift
    against per-budget-line totals is surfaced prominently rather than
    silently accepted.
    """
    report = compute_reconciliation(db, grant_id=grant_id)
    return ContractReconciliationOut(
        grant_id=report.grant_id,
        lines=[
            ContractReconciliationLineOut(
                budget_line=line.budget_line,
                contract_types=list(line.contract_types),
                expected_cents=line.expected_cents,
                actual_cents=line.actual_cents,
                contract_count=line.contract_count,
                drift_cents=line.drift_cents,
                reconciles=line.reconciles,
            )
            for line in report.lines
        ],
        overall_reconciles=report.overall_reconciles,
        warnings=list(report.warnings),
    )


@router.get("/{contract_id}", response_model=ContractDetailOut)
def get_contract(
    contract_id: str, db: Session = Depends(get_db)
) -> ContractDetailOut:
    """Fetch one contract with its amendments and termination detail."""
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")

    base = _to_out(contract)
    # Eagerly serialize amendments via the relationship (already ordered).
    amendments = [
        _to_amendment_out(a) for a in contract.amendments
    ]
    termination = (
        _to_termination_out(contract.termination_detail)
        if contract.termination_detail is not None
        else None
    )
    return ContractDetailOut(
        **base.model_dump(),
        amendments=amendments,
        termination_detail=termination,
    )


# ---------- mutations ----------


@router.post("", response_model=ContractOut, status_code=201)
def create_contract(body: ContractIn, db: Session = Depends(get_db)) -> ContractOut:
    """Create a contract via the API. Used after bootstrap for adding
    contracts that surface mid-grant.

    Bootstrap import (Excel-driven, multiple rows) lives in the
    contracts_bootstrap CLI; this endpoint is the single-row API path.
    """
    record = _ContractIn_to_record(body)
    try:
        contract = create_contract_from_record(
            db, record=record, grant_id=body.grant_id, actor=body.actor
        )
    except ImporterError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    db.commit()
    db.refresh(contract)
    return _to_out(contract)


@router.put("/{contract_id}", response_model=ContractOut)
def update_contract(
    contract_id: str, body: ContractIn, db: Session = Depends(get_db)
) -> ContractOut:
    """Update a contract via the API. Records before/after in audit_log.

    Note: grant_id on the body is ignored for updates — moving a
    contract to a different grant is not in scope and would require
    an explicit re-keying flow.
    """
    contract = db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(status_code=404, detail="Contract not found")

    record = _ContractIn_to_record(body)
    update_contract_from_record(db, contract=contract, record=record, actor=body.actor)
    db.commit()
    db.refresh(contract)
    return _to_out(contract)


# ---------- helpers ----------


def _ContractIn_to_record(body: ContractIn) -> ContractRecord:
    """Convert the API input shape to the bootstrap record shape.

    The two are nearly identical (intentional — the bootstrap and API
    produce the same SQLAlchemy rows). The only field that doesn't
    transfer is `record_key` which is bootstrap-only.
    """
    return ContractRecord(
        record_key=body.vendor_legal_entity,  # placeholder; unused by API path
        vendor_name_display=body.vendor_name_display,
        vendor_legal_entity=body.vendor_legal_entity,
        vendor_qb_names=body.vendor_qb_names,
        contract_type=body.contract_type,
        compliance_classification=body.compliance_classification,
        classification_rationale=body.classification_rationale,
        procurement_method=body.procurement_method,
        original_executed_date=body.original_executed_date,
        original_effective_date=body.original_effective_date,
        current_end_date=body.current_end_date,
        original_contract_value_cents=body.original_contract_value_cents,
        current_contract_value_cents=body.current_contract_value_cents,
        status=body.status,
        payment_basis=body.payment_basis,
        payment_basis_detail=body.payment_basis_detail,
        executed_contract_link=body.executed_contract_link,
        scope_of_work_summary=body.scope_of_work_summary,
        notes=body.notes,
    )


def _to_out(c: Contract) -> ContractOut:
    """Build a ContractOut from a Contract row, computing the spec's
    honesty fields at serialization time.
    """
    is_above_sat = (
        c.current_contract_value_cents >= SIMPLIFIED_ACQUISITION_THRESHOLD_CENTS
    )
    is_above_mpt = (
        c.current_contract_value_cents >= MICRO_PURCHASE_THRESHOLD_CENTS
    )
    requires_cost_analysis = is_above_sat and (
        c.compliance_classification
        == ComplianceClassification.contractor_200_331b
    )
    subject_to_monitoring = (
        c.compliance_classification
        == ComplianceClassification.subrecipient_200_331a
    )
    is_active = c.status == ContractStatus.active
    is_closed = c.status in {
        ContractStatus.closed_normally,
        ContractStatus.closed_with_findings,
        ContractStatus.terminated_by_cfa,
        ContractStatus.terminated_by_funder,
    }

    return ContractOut(
        id=c.id,
        grant_id=c.grant_id,
        vendor_party_id=c.vendor_party_id,
        vendor_name_display=c.vendor_name_display,
        vendor_legal_entity=c.vendor_legal_entity,
        vendor_qb_names=list(c.vendor_qb_names or []),
        contract_type=c.contract_type,
        compliance_classification=c.compliance_classification,
        classification_rationale=c.classification_rationale,
        procurement_method=c.procurement_method,
        original_executed_date=c.original_executed_date,
        original_effective_date=c.original_effective_date,
        current_end_date=c.current_end_date,
        original_contract_value_cents=c.original_contract_value_cents,
        current_contract_value_cents=c.current_contract_value_cents,
        status=c.status,
        payment_basis=c.payment_basis,
        payment_basis_detail=c.payment_basis_detail,
        executed_contract_link=c.executed_contract_link,
        scope_of_work_summary=c.scope_of_work_summary,
        notes=c.notes,
        record_created_at=c.record_created_at,
        record_updated_at=c.record_updated_at,
        record_updated_by=c.record_updated_by,
        is_above_simplified_acquisition_threshold=is_above_sat,
        is_above_micro_purchase_threshold=is_above_mpt,
        requires_cost_or_price_analysis=requires_cost_analysis,
        is_subject_to_subrecipient_monitoring=subject_to_monitoring,
        is_active=is_active,
        is_closed=is_closed,
    )


def _to_amendment_out(a):  # type: ignore[no-untyped-def]
    from grant_compliance.api.schemas import ContractAmendmentOut
    return ContractAmendmentOut.model_validate(a)


def _to_termination_out(t):  # type: ignore[no-untyped-def]
    from grant_compliance.api.schemas import ContractTerminationDetailOut
    return ContractTerminationDetailOut.model_validate(t)
