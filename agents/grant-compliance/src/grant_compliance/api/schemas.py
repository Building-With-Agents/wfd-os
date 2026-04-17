"""Pydantic schemas for API request/response bodies."""

from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


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
