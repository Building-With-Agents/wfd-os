"""Pydantic schemas for API request/response bodies."""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from grant_compliance.db.models import (
    AmendmentType,
    ComplianceClassification,
    ContractStatus,
    ContractType,
    PaymentBasis,
    ProcurementMethod,
    TerminatedBy,
)


# ---------------------------------------------------------------------------
# Grants
# ---------------------------------------------------------------------------


class GrantOut(BaseModel):
    id: str
    name: str
    award_number: str | None
    funder_id: str
    period_start: date
    period_end: date
    total_award_cents: int
    indirect_rate_pct: float | None
    closed: bool

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Transactions
# ---------------------------------------------------------------------------


class TransactionOut(BaseModel):
    id: str
    qb_id: str
    qb_type: str
    txn_date: date
    vendor_name: str | None
    memo: str | None
    amount_cents: int

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Allocations
# ---------------------------------------------------------------------------


class AllocationOut(BaseModel):
    id: str
    transaction_id: str
    grant_id: str
    amount_cents: int
    budget_category: str | None
    status: str
    rationale: str | None
    confidence: float | None
    proposed_by: str
    proposed_at: datetime
    decided_by: str | None
    decided_at: datetime | None

    class Config:
        from_attributes = True


class AllocationDecision(BaseModel):
    """Body for approving or rejecting a proposed allocation."""

    decision: str = Field(..., pattern="^(approve|reject)$")
    decider_email: str
    note: str | None = None
    # If approve, optionally adjust the amount before approving
    adjusted_amount_cents: int | None = None
    adjusted_budget_category: str | None = None


class AllocationProposeManual(BaseModel):
    """Body for a human to propose an allocation directly (no agent)."""

    transaction_id: str
    grant_id: str
    amount_cents: int
    budget_category: str | None = None
    rationale: str
    proposer_email: str


# ---------------------------------------------------------------------------
# Compliance
# ---------------------------------------------------------------------------


class ComplianceFlagOut(BaseModel):
    id: str
    transaction_id: str | None
    allocation_id: str | None
    rule_id: str
    rule_citation: str
    message: str
    severity: str
    status: str
    raised_at: datetime
    resolved_at: datetime | None
    resolved_by: str | None
    resolution_note: str | None

    class Config:
        from_attributes = True


class FlagResolution(BaseModel):
    resolution: str = Field(..., pattern="^(resolve|waive|acknowledge)$")
    resolver_email: str
    note: str


# ---------------------------------------------------------------------------
# Time & effort
# ---------------------------------------------------------------------------


class TimeCertificationOut(BaseModel):
    id: str
    employee_id: str
    period_year: int
    period_month: int
    splits: dict[str, float]
    drafted_at: datetime
    certified_by: str | None
    certified_at: datetime | None
    rationale: str | None

    class Config:
        from_attributes = True


class TimeCertificationCertify(BaseModel):
    certifier_email: str
    method: str = "click"
    adjustments: dict[str, float] | None = None


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class ReportDraftOut(BaseModel):
    id: str
    grant_id: str
    report_type: str
    period_start: date
    period_end: date
    payload: dict
    snapshot_id: str
    generated_at: datetime
    finalized_at: datetime | None
    finalized_by: str | None

    class Config:
        from_attributes = True


class ReportDraftRequest(BaseModel):
    grant_id: str
    report_type: str = Field(..., pattern="^(SF-425|foundation_narrative)$")
    period_start: date
    period_end: date


# ---------------------------------------------------------------------------
# Contracts inventory
# Spec: agents/grant-compliance/docs/contracts_inventory_spec.md
# ---------------------------------------------------------------------------


class ContractAmendmentOut(BaseModel):
    """Response body for one ContractAmendment row."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    amendment_number: int
    amendment_type: AmendmentType
    executed_date: Optional[date] = None
    effective_date: Optional[date] = None
    previous_value_cents: Optional[int] = None
    new_value_cents: Optional[int] = None
    previous_end_date: Optional[date] = None
    new_end_date: Optional[date] = None
    summary_of_changes: Optional[str] = None
    document_link: Optional[str] = None
    record_created_at: datetime


class ContractTerminationDetailOut(BaseModel):
    """Response body for the optional ContractTerminationDetail row."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    contract_id: str
    terminated_by: TerminatedBy
    termination_date: Optional[date] = None
    termination_reason: Optional[str] = None
    termination_correspondence_link: Optional[str] = None
    final_reconciliation_link: Optional[str] = None
    closeout_findings: Optional[str] = None
    record_created_at: datetime


class ContractOut(BaseModel):
    """Response body for one Contract row (list view).

    Includes the computed honesty fields (threshold indicators,
    requires_cost_or_price_analysis, is_active) so callers don't have
    to re-derive them client-side. Per the spec these are computed at
    query time, not stored.
    """

    model_config = ConfigDict(from_attributes=True)

    id: str
    grant_id: str
    vendor_party_id: Optional[str] = None
    vendor_name_display: str
    vendor_legal_entity: str
    vendor_qb_names: list[str]
    contract_type: ContractType
    compliance_classification: ComplianceClassification
    classification_rationale: Optional[str] = None
    procurement_method: ProcurementMethod
    original_executed_date: Optional[date] = None
    original_effective_date: Optional[date] = None
    current_end_date: Optional[date] = None
    original_contract_value_cents: int
    current_contract_value_cents: int
    status: ContractStatus
    payment_basis: PaymentBasis
    payment_basis_detail: Optional[str] = None
    executed_contract_link: Optional[str] = None
    scope_of_work_summary: Optional[str] = None
    notes: Optional[str] = None
    record_created_at: datetime
    record_updated_at: datetime
    record_updated_by: Optional[str] = None

    # Computed honesty fields — see spec §"Computed fields".
    is_above_simplified_acquisition_threshold: bool
    is_above_micro_purchase_threshold: bool
    requires_cost_or_price_analysis: bool
    is_subject_to_subrecipient_monitoring: bool
    is_active: bool
    is_closed: bool


class ContractDetailOut(ContractOut):
    """Detail response body — one Contract plus its amendments + termination."""

    amendments: list[ContractAmendmentOut] = Field(default_factory=list)
    termination_detail: Optional[ContractTerminationDetailOut] = None


class ContractIn(BaseModel):
    """Request body for POST /contracts and PUT /contracts/{id}.

    Same field set as a bootstrap ContractRecord but without the
    spreadsheet-only `record_key`. Money in cents (engine convention) —
    Excel-side dollar conversion happens in the bootstrap loader, not
    here.
    """

    model_config = ConfigDict(extra="forbid")

    vendor_party_id: Optional[str] = None
    vendor_name_display: str = Field(..., min_length=1)
    vendor_legal_entity: str = Field(..., min_length=1)
    vendor_qb_names: list[str] = Field(default_factory=list)
    contract_type: ContractType
    compliance_classification: ComplianceClassification = (
        ComplianceClassification.unclassified
    )
    classification_rationale: Optional[str] = None
    procurement_method: ProcurementMethod = ProcurementMethod.unknown
    original_executed_date: Optional[date] = None
    original_effective_date: Optional[date] = None
    current_end_date: Optional[date] = None
    original_contract_value_cents: int = Field(..., ge=0)
    current_contract_value_cents: int = Field(..., ge=0)
    status: ContractStatus = ContractStatus.active
    payment_basis: PaymentBasis = PaymentBasis.other
    payment_basis_detail: Optional[str] = None
    executed_contract_link: Optional[str] = None
    scope_of_work_summary: Optional[str] = None
    notes: Optional[str] = None

    # Caller email captured in audit_log. Until SSO lands this is
    # supplied by the client; cockpit injects the staff member's email
    # from session context.
    actor: str = Field(..., min_length=1)
    grant_id: str  # required on create; ignored on update


class ContractReconciliationLineOut(BaseModel):
    """One Amendment 1 budget line and its computed actual sum."""

    budget_line: str
    contract_types: list[str]
    expected_cents: int
    actual_cents: int
    contract_count: int
    drift_cents: int  # actual - expected; positive = over budget
    reconciles: bool


class ContractReconciliationOut(BaseModel):
    """Top-level reconciliation result for GET /contracts/reconciliation."""

    grant_id: str
    lines: list[ContractReconciliationLineOut]
    overall_reconciles: bool
    warnings: list[str]
