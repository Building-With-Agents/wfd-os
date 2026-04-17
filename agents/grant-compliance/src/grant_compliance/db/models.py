"""SQLAlchemy ORM models. The data contract for the system.

Money is stored as integer cents. Dates are UTC. Audit log is append-only.
"""

from __future__ import annotations

import enum
import uuid
from datetime import date, datetime, timezone
from typing import Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# Funders & Grants
# ---------------------------------------------------------------------------


class FunderType(str, enum.Enum):
    federal = "federal"
    state = "state"
    local = "local"
    foundation = "foundation"
    corporate = "corporate"
    other = "other"


class Funder(Base):
    __tablename__ = "funders"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    funder_type: Mapped[FunderType] = mapped_column(Enum(FunderType), nullable=False)
    # Federal pass-through tracking
    federal_pass_through: Mapped[bool] = mapped_column(Boolean, default=False)
    cfda_number: Mapped[Optional[str]] = mapped_column(String(20))  # e.g. "93.243"
    notes: Mapped[Optional[str]] = mapped_column(Text)

    grants: Mapped[list["Grant"]] = relationship(back_populates="funder")


class Grant(Base):
    __tablename__ = "grants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    funder_id: Mapped[str] = mapped_column(ForeignKey("funders.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    award_number: Mapped[Optional[str]] = mapped_column(String(100))
    # The QuickBooks Class or Project name this grant maps to
    qb_class_name: Mapped[Optional[str]] = mapped_column(String(255))
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    total_award_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    indirect_rate_pct: Mapped[Optional[float]] = mapped_column()  # e.g. 10.0 for de minimis
    indirect_rate_basis: Mapped[Optional[str]] = mapped_column(String(50))  # MTDC, etc.
    scope_of_work: Mapped[Optional[str]] = mapped_column(Text)
    closed: Mapped[bool] = mapped_column(Boolean, default=False)

    funder: Mapped[Funder] = relationship(back_populates="grants")
    budget_lines: Mapped[list["BudgetLine"]] = relationship(back_populates="grant")
    allocations: Mapped[list["Allocation"]] = relationship(back_populates="grant")


class BudgetLine(Base):
    """A single line of an approved grant budget. Snapshot-based.

    A grant can have multiple budget *versions* — only one is active at a time.
    Reports must reference the version active on the report date.
    """

    __tablename__ = "budget_lines"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    grant_id: Mapped[str] = mapped_column(ForeignKey("grants.id"), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[Optional[date]] = mapped_column(Date)  # null = current
    category: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "Personnel"
    subcategory: Mapped[Optional[str]] = mapped_column(String(100))
    budgeted_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)

    grant: Mapped[Grant] = relationship(back_populates="budget_lines")


# ---------------------------------------------------------------------------
# QuickBooks mirror
# ---------------------------------------------------------------------------


class QbAccount(Base):
    """Mirror of a QB chart-of-accounts entry."""

    __tablename__ = "qb_accounts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    qb_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    account_type: Mapped[str] = mapped_column(String(50), nullable=False)
    account_subtype: Mapped[Optional[str]] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class QbClass(Base):
    """Mirror of a QB Class (or Project) — what the org uses to tag by grant."""

    __tablename__ = "qb_classes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    qb_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Transaction(Base):
    """A normalized QB transaction (Bill, Check, Expense, JournalEntry, Paycheck)."""

    __tablename__ = "transactions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    qb_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    qb_type: Mapped[str] = mapped_column(String(50), nullable=False)  # Bill, Check, etc.
    txn_date: Mapped[date] = mapped_column(Date, nullable=False)
    posted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    vendor_name: Mapped[Optional[str]] = mapped_column(String(255))
    memo: Mapped[Optional[str]] = mapped_column(Text)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    qb_class_id: Mapped[Optional[str]] = mapped_column(ForeignKey("qb_classes.id"))
    qb_account_id: Mapped[Optional[str]] = mapped_column(ForeignKey("qb_accounts.id"))
    raw: Mapped[dict] = mapped_column(JSON, default=dict)

    allocations: Mapped[list["Allocation"]] = relationship(back_populates="transaction")
    flags: Mapped[list["ComplianceFlag"]] = relationship(back_populates="transaction")


# ---------------------------------------------------------------------------
# Allocations — the heart of grant accounting
# ---------------------------------------------------------------------------


class AllocationStatus(str, enum.Enum):
    proposed = "proposed"  # Agent proposed, awaiting human review
    approved = "approved"  # Human approved
    rejected = "rejected"  # Human rejected
    superseded = "superseded"  # Replaced by a newer allocation


class Allocation(Base):
    """A proposal or decision to charge some portion of a transaction to a grant.

    A single transaction can have multiple allocations (split across grants).
    The sum of approved allocation amounts must equal the transaction amount.
    """

    __tablename__ = "allocations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    transaction_id: Mapped[str] = mapped_column(ForeignKey("transactions.id"), nullable=False)
    grant_id: Mapped[str] = mapped_column(ForeignKey("grants.id"), nullable=False)
    amount_cents: Mapped[int] = mapped_column(BigInteger, nullable=False)
    budget_category: Mapped[Optional[str]] = mapped_column(String(100))
    status: Mapped[AllocationStatus] = mapped_column(
        Enum(AllocationStatus), default=AllocationStatus.proposed
    )
    # Why was this proposed? Citation back to budget line, prior txn, or rule
    rationale: Mapped[Optional[str]] = mapped_column(Text)
    confidence: Mapped[Optional[float]] = mapped_column()  # 0..1, set by Classifier
    proposed_by: Mapped[str] = mapped_column(String(100), default="classifier")
    proposed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    decided_by: Mapped[Optional[str]] = mapped_column(String(255))
    decided_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    transaction: Mapped[Transaction] = relationship(back_populates="allocations")
    grant: Mapped[Grant] = relationship(back_populates="allocations")


# ---------------------------------------------------------------------------
# Time & Effort
# ---------------------------------------------------------------------------


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    qb_employee_id: Mapped[Optional[str]] = mapped_column(String(50), unique=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String(255))
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class TimeCertification(Base):
    """A monthly time & effort certification for an employee whose salary is
    charged to one or more federal grants. Required by 2 CFR 200.430.
    """

    __tablename__ = "time_certifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    employee_id: Mapped[str] = mapped_column(ForeignKey("employees.id"), nullable=False)
    period_year: Mapped[int] = mapped_column(Integer, nullable=False)
    period_month: Mapped[int] = mapped_column(Integer, nullable=False)  # 1..12
    # JSON: { grant_id: percent, ... }, summing to 100
    splits: Mapped[dict] = mapped_column(JSON, default=dict)
    drafted_by: Mapped[str] = mapped_column(String(100), default="time_effort_agent")
    drafted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    certified_by: Mapped[Optional[str]] = mapped_column(String(255))
    certified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    signature_method: Mapped[Optional[str]] = mapped_column(String(50))  # "click", "esign", etc.
    rationale: Mapped[Optional[str]] = mapped_column(Text)


# ---------------------------------------------------------------------------
# Compliance Flags
# ---------------------------------------------------------------------------


class FlagSeverity(str, enum.Enum):
    info = "info"
    warning = "warning"
    blocker = "blocker"  # cannot be included in a report until resolved


class FlagStatus(str, enum.Enum):
    open = "open"
    acknowledged = "acknowledged"
    resolved = "resolved"
    waived = "waived"


class ComplianceFlag(Base):
    """A finding from the Compliance Monitor on a transaction or allocation."""

    __tablename__ = "compliance_flags"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    transaction_id: Mapped[Optional[str]] = mapped_column(ForeignKey("transactions.id"))
    allocation_id: Mapped[Optional[str]] = mapped_column(ForeignKey("allocations.id"))
    rule_id: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "UC.200.421"
    rule_citation: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[FlagSeverity] = mapped_column(Enum(FlagSeverity), nullable=False)
    status: Mapped[FlagStatus] = mapped_column(Enum(FlagStatus), default=FlagStatus.open)
    raised_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    resolved_by: Mapped[Optional[str]] = mapped_column(String(255))
    resolution_note: Mapped[Optional[str]] = mapped_column(Text)

    transaction: Mapped[Optional[Transaction]] = relationship(back_populates="flags")


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class ReportDraft(Base):
    """A generated draft of a funder report. Immutable once finalized."""

    __tablename__ = "report_drafts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    grant_id: Mapped[str] = mapped_column(ForeignKey("grants.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(50), nullable=False)  # SF-425, foundation, etc.
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)
    payload: Mapped[dict] = mapped_column(JSON, default=dict)  # the actual report data
    snapshot_id: Mapped[str] = mapped_column(String(36), nullable=False)  # reproducibility
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    finalized_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    finalized_by: Mapped[Optional[str]] = mapped_column(String(255))


# ---------------------------------------------------------------------------
# Audit Log — APPEND ONLY. Never UPDATE or DELETE.
# ---------------------------------------------------------------------------


class AuditLog(Base):
    """Append-only log of every consequential action.

    Writes go through `audit.log.write_entry()`. Do not insert directly.
    """

    __tablename__ = "audit_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    actor: Mapped[str] = mapped_column(String(255), nullable=False)  # user email or agent name
    actor_kind: Mapped[str] = mapped_column(String(20), nullable=False)  # "human" | "agent"
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "allocation.propose"
    target_type: Mapped[Optional[str]] = mapped_column(String(50))
    target_id: Mapped[Optional[str]] = mapped_column(String(36))
    inputs: Mapped[dict] = mapped_column(JSON, default=dict)
    outputs: Mapped[dict] = mapped_column(JSON, default=dict)
    model: Mapped[Optional[str]] = mapped_column(String(100))  # LLM model id if agent
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(64))
    note: Mapped[Optional[str]] = mapped_column(Text)
