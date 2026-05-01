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
    MetaData,
    String,
    Text,
    JSON,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


# All grant-compliance tables live in the `grant_compliance` Postgres schema,
# kept separate from wfd-os's other schemas (public, etc.) so we can grant
# row-level privileges on audit_log independently and hand an auditor
# read-only access to this schema alone. Setting schema on the metadata
# here propagates to every model below without needing per-table
# __table_args__. See agents/grant-compliance/CLAUDE.md and Step 0 of the
# QB ingestion migration plan.
#
# SQLite (used by some tests with in-memory DBs) ignores schema qualifiers
# gracefully; Postgres respects them. Production and dev-against-Postgres
# land all tables under `grant_compliance.*`.
class Base(DeclarativeBase):
    metadata = MetaData(schema="grant_compliance")


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


class QbOAuthToken(Base):
    """Persisted QB OAuth credentials for a single QB realm (company).

    A realm corresponds to one QuickBooks Online company file. In the current
    architecture we expect a single realm per deployment (one org's books),
    but the schema supports multi-realm if the platform ever needs it.

    Security note: access_token and refresh_token are stored in plaintext
    today. This is TOLERABLE only while QB_ENVIRONMENT=sandbox — sandbox
    data is synthetic. For production, the `_refuse_production_without_encryption_key`
    guard in config.py refuses to start. Before flipping to production:
      1. Set ENCRYPTION_KEY to a Fernet key
      2. Wrap access_token / refresh_token getters/setters with Fernet
         encrypt/decrypt in a property
      3. Migrate any existing rows through the new encryption
    See CLAUDE.md "Enforced constraints" and the "Before Step 1" section
    in README for context.
    """

    __tablename__ = "qb_oauth_tokens"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    realm_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    # Tokens: plaintext in sandbox, encrypted in production (see class docstring).
    access_token: Mapped[str] = mapped_column(Text, nullable=False)
    refresh_token: Mapped[str] = mapped_column(Text, nullable=False)
    # Intuit returns access_token with 3600s TTL (1 hour) and refresh_token
    # with ~100 day TTL. We track both expiries so the refresh path can
    # detect when the refresh_token itself is close to expiring.
    access_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    refresh_token_expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    # QB_ENVIRONMENT at the time of authorization. Sanity-check at use:
    # if this says "sandbox" but current settings say "production", we
    # refuse to use the token. Prevents token leak across environments.
    environment: Mapped[str] = mapped_column(String(20), nullable=False)
    # The Intuit user whose consent created this token. Informational —
    # used for audit trail. Set to dev_user_email or similar at callback.
    authorized_by: Mapped[Optional[str]] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    # Manually flagged as revoked (e.g. Ritu revokes Waifinder's access at Intuit).
    # Also set when a refresh fails with "invalid_grant" — the refresh chain
    # is broken, need to re-authorize.
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))


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
    # Count of QB Attachable entities (invoice PDFs, receipts, etc.) that
    # reference this transaction. Populated by quickbooks.sync.sync_attachables.
    # Zero means no linked documentation. Powers the Audit Readiness tab's
    # Documentation Gap stat via queries.transactions_without_documentation.
    attachment_count: Mapped[int] = mapped_column(
        Integer, default=0, server_default="0", nullable=False
    )
    # Timestamp of the last Compliance Monitor scan for this transaction.
    # Stamped by ComplianceMonitor.scan_transaction on every evaluation,
    # regardless of whether a flag is raised. Lets the Audit Readiness
    # allowable_costs computation use a fresh denominator — only scans
    # within the freshness window count toward the readiness percentage,
    # so stale or never-scanned transactions don't inflate the score.
    last_scanned_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True, default=None
    )

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


# ---------------------------------------------------------------------------
# Compliance Requirements Agent — Mode A output sets and Mode B Q&A log
# Spec: agents/grant-compliance/docs/compliance_requirements_agent_spec.md
# Corpus: agents/grant-compliance/data/regulatory_corpus/
# ---------------------------------------------------------------------------


class ComplianceRequirementsSet(Base):
    """A Mode A generation run's output — a comprehensive structured
    documentation requirements specification for a specific grant.

    Each set is keyed by a stable `set_id` (UUID) and is immutable once
    written. New runs do not delete old sets; instead they set
    `superseded_by_id` on the prior set so the audit trail of how the
    requirements specification evolved is preserved. The `is_current`
    flag is set on exactly one set per grant at a time (the active one
    the cockpit displays); the supersede operation flips this in a
    single transaction.

    Reproducibility: the full prompt text, model name, and full LLM
    response are stored alongside the parsed requirements so any
    specific run is reproducible later. This extends the engine's
    audit_log discipline to LLM-generated structured artifacts.
    """

    __tablename__ = "compliance_requirements_sets"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    grant_id: Mapped[str] = mapped_column(
        ForeignKey("grants.id"), nullable=False, index=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )

    # Scope of the generation: which compliance areas, contracts, engagement
    # the run covered. JSON because the shape is a structured object
    # (ComplianceArea[], contract_ids[], engagement_id?).
    scope: Mapped[dict] = mapped_column(JSON, default=dict)

    # Provenance of the regulatory corpus the agent worked from.
    regulatory_corpus_version: Mapped[str] = mapped_column(String(100), nullable=False)

    # Snapshot of the CFA-specific facts the agent used to tailor output —
    # contract counts, classifications, thresholds in play. Lets a later
    # reader understand what assumptions drove the specifics.
    grant_context: Mapped[dict] = mapped_column(JSON, default=dict)

    # LLM call audit trail
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)
    model_response_text: Mapped[Optional[str]] = mapped_column(Text)  # full raw response
    prompt_text: Mapped[Optional[str]] = mapped_column(Text)  # full prompt sent
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(64))
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)

    # Versioning
    superseded_by_id: Mapped[Optional[str]] = mapped_column(
        ForeignKey("compliance_requirements_sets.id"),
        nullable=True,
    )
    is_current: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Human review (per spec §"Determinism and reproducibility" — Mode A
    # output is a draft until reviewed). Optional fields.
    reviewed_by: Mapped[Optional[str]] = mapped_column(String(255))
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    review_notes: Mapped[Optional[str]] = mapped_column(Text)

    requirements: Mapped[list["ComplianceRequirementRow"]] = relationship(
        back_populates="set", cascade="all, delete-orphan"
    )


class ComplianceRequirementRow(Base):
    """One requirement record within a ComplianceRequirementsSet.

    The row's content matches the spec's Requirement schema. Each row
    must cite a specific CFR section (regulatory_citation) and include
    a verbatim or paraphrased excerpt (regulatory_text_excerpt) so the
    requirement is auditable against the source corpus.
    """

    __tablename__ = "compliance_requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    set_id: Mapped[str] = mapped_column(
        ForeignKey("compliance_requirements_sets.id"), nullable=False, index=True
    )
    requirement_id: Mapped[str] = mapped_column(String(100), nullable=False)
    compliance_area: Mapped[str] = mapped_column(String(50), nullable=False, index=True)

    regulatory_citation: Mapped[str] = mapped_column(String(255), nullable=False)
    regulatory_text_excerpt: Mapped[str] = mapped_column(Text, nullable=False)

    # Applicability: structured object {applies_to, threshold_value?, circumstance_description?}
    applicability: Mapped[dict] = mapped_column(JSON, default=dict)

    requirement_summary: Mapped[str] = mapped_column(Text, nullable=False)
    documentation_artifacts_required: Mapped[list] = mapped_column(JSON, default=list)
    documentation_form_guidance: Mapped[Optional[str]] = mapped_column(Text)
    cfa_specific_application: Mapped[Optional[str]] = mapped_column(Text)

    severity_if_missing: Mapped[str] = mapped_column(String(20), nullable=False)

    set: Mapped[ComplianceRequirementsSet] = relationship(back_populates="requirements")


class ComplianceQALog(Base):
    """One Mode B Q&A interaction. Every Mode B query is logged: the
    question, the structured response, the model used, the prompt, and
    the timestamp. Per spec §"Open questions" #3 — Ritu confirmed the
    recommendation to retain Mode B exchanges for review/audit.
    """

    __tablename__ = "compliance_qa_log"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    asked_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, index=True
    )
    asked_by: Mapped[Optional[str]] = mapped_column(String(255))
    question: Mapped[str] = mapped_column(Text, nullable=False)

    # Optional caller-supplied hints (e.g., a contract_id) that the agent
    # may use to scope its reply.
    context_hints: Mapped[dict] = mapped_column(JSON, default=dict)

    # The structured response — answer, citations, relevant_existing_requirements,
    # caveats, out_of_scope_warning — stored as JSON to match the QAResponse
    # Pydantic schema.
    response: Mapped[dict] = mapped_column(JSON, default=dict)

    # Whether the response was a structured refusal (legal-opinion or
    # out-of-scope question). True ⇒ Mode B declined; the response field
    # carries the structured refusal.
    refused: Mapped[bool] = mapped_column(Boolean, default=False)

    # LLM call audit trail
    model_name: Mapped[Optional[str]] = mapped_column(String(100))
    model_response_text: Mapped[Optional[str]] = mapped_column(Text)
    prompt_text: Mapped[Optional[str]] = mapped_column(Text)
    prompt_hash: Mapped[Optional[str]] = mapped_column(String(64))
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer)


# ---------------------------------------------------------------------------
# Contracts inventory — canonical entity for every K8341 third-party agreement.
# Spec: agents/grant-compliance/docs/contracts_inventory_spec.md
#
# Hub entity that downstream features reference:
#   - Compliance Requirements documentation_status (Session 2) — applicable_target
#     references contract_id when a requirement applies to specific contracts
#   - Monitoring engagements — ContractUnderReview sub-records
#   - Audit Readiness procurement / subrecipient dimensions — sweep contracts
#     filtered by classification
#   - Personnel — Person.vendor_legal_entity loose-couples to
#     Contract.vendor_legal_entity for CFA contractors
# ---------------------------------------------------------------------------


class ContractType(str, enum.Enum):
    training_provider = "training_provider"
    strategic_partner_subrecipient = "strategic_partner_subrecipient"
    cfa_contractor = "cfa_contractor"
    subrecipient_other = "subrecipient_other"
    other = "other"


class ComplianceClassification(str, enum.Enum):
    contractor_200_331b = "contractor_200_331b"
    subrecipient_200_331a = "subrecipient_200_331a"
    unclassified = "unclassified"


class ContractStatus(str, enum.Enum):
    active = "active"
    closed_normally = "closed_normally"
    closed_with_findings = "closed_with_findings"
    terminated_by_cfa = "terminated_by_cfa"
    terminated_by_funder = "terminated_by_funder"


class PaymentBasis(str, enum.Enum):
    per_placement = "per_placement"
    fixed_fee = "fixed_fee"
    time_and_materials = "time_and_materials"
    milestone = "milestone"
    cost_reimbursement = "cost_reimbursement"
    other = "other"


class ProcurementMethod(str, enum.Enum):
    """Categorical procurement method per Contract.

    Promoted from v1.1 to v1 per the 2026-04-30 amendment in
    contracts_inventory_spec.md — needed by the Compliance Requirements
    Display Session 2 documentation status workflow to filter Contracts
    for sole-source-only requirements.

    Only the categorical enum is in v1. The associated artifacts (RFP
    files, evaluations, sole-source justification narratives) remain in
    v1.1 per the deferred section. `unknown` is the bootstrap default
    for contracts whose method has not yet been confirmed by Krista —
    intentionally visible rather than silently mis-classified.
    """

    competitive_rfp = "competitive_rfp"
    competitive_proposals = "competitive_proposals"
    small_purchase = "small_purchase"
    micro_purchase = "micro_purchase"
    sole_source = "sole_source"
    informal = "informal"
    unknown = "unknown"
    not_applicable_subaward = "not_applicable_subaward"


class AmendmentType(str, enum.Enum):
    value_change = "value_change"
    period_extension = "period_extension"
    scope_change = "scope_change"
    termination = "termination"
    other = "other"


class TerminatedBy(str, enum.Enum):
    cfa = "cfa"
    funder = "funder"
    mutual = "mutual"


class Contract(Base):
    """A formal agreement under which CFA pays a third party with K8341
    grant funds. See contracts_inventory_spec.md for the complete contract.

    All money is integer cents (BigInteger). Reconciliation against
    Amendment 1 budget lines is computed at query time, not stored.
    """

    __tablename__ = "contracts"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    grant_id: Mapped[str] = mapped_column(
        ForeignKey("grants.id"), nullable=False, index=True
    )

    # Vendor identity. vendor_party_id is reserved for a future parties
    # table (v1.1+ vendor master); for v1, free-text matching against
    # vendor_qb_names handles the AI Engage / Jason Mangold / AIE Group
    # name-variation problem.
    vendor_party_id: Mapped[Optional[str]] = mapped_column(String(36))
    vendor_name_display: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_legal_entity: Mapped[str] = mapped_column(String(255), nullable=False)
    vendor_qb_names: Mapped[list] = mapped_column(JSON, default=list)

    # Classification. compliance_classification follows §200.331 characteristics.
    # `unclassified` is a visible bootstrap state — not silently inferred.
    contract_type: Mapped[ContractType] = mapped_column(
        Enum(ContractType), nullable=False, index=True
    )
    compliance_classification: Mapped[ComplianceClassification] = mapped_column(
        Enum(ComplianceClassification),
        nullable=False,
        default=ComplianceClassification.unclassified,
        index=True,
    )
    classification_rationale: Mapped[Optional[str]] = mapped_column(Text)

    # Procurement method — promoted to v1 per 2026-04-30 amendment.
    # Default `unknown` so any unseen contract is explicitly visible
    # rather than silently mis-classified.
    procurement_method: Mapped[ProcurementMethod] = mapped_column(
        Enum(ProcurementMethod),
        nullable=False,
        default=ProcurementMethod.unknown,
        index=True,
    )

    # Dates
    original_executed_date: Mapped[Optional[date]] = mapped_column(Date)
    original_effective_date: Mapped[Optional[date]] = mapped_column(Date)
    current_end_date: Mapped[Optional[date]] = mapped_column(Date)

    # Money — cents, BigInteger per engine convention. original_* is the
    # value at first execution; current_* reflects accumulated amendments.
    original_contract_value_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )
    current_contract_value_cents: Mapped[int] = mapped_column(
        BigInteger, nullable=False, default=0
    )

    # Status + payment terms
    status: Mapped[ContractStatus] = mapped_column(
        Enum(ContractStatus),
        nullable=False,
        default=ContractStatus.active,
        index=True,
    )
    payment_basis: Mapped[PaymentBasis] = mapped_column(
        Enum(PaymentBasis), nullable=False, default=PaymentBasis.other
    )
    payment_basis_detail: Mapped[Optional[str]] = mapped_column(Text)

    # Documentation
    executed_contract_link: Mapped[Optional[str]] = mapped_column(String(1024))
    scope_of_work_summary: Mapped[Optional[str]] = mapped_column(Text)
    notes: Mapped[Optional[str]] = mapped_column(Text)

    # Provenance
    record_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    record_updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )
    record_updated_by: Mapped[Optional[str]] = mapped_column(String(255))

    amendments: Mapped[list["ContractAmendment"]] = relationship(
        back_populates="contract", cascade="all, delete-orphan",
        order_by="ContractAmendment.amendment_number",
    )
    termination_detail: Mapped[Optional["ContractTerminationDetail"]] = relationship(
        back_populates="contract", uselist=False, cascade="all, delete-orphan",
    )


class ContractAmendment(Base):
    """One row per amendment to a Contract. Chronological by amendment_number.

    Amendments record the before/after values and end dates so the
    history is auditable without scanning prior versions of the parent
    Contract row. The parent Contract.current_contract_value_cents and
    .current_end_date hold the cumulative result.
    """

    __tablename__ = "contract_amendments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    contract_id: Mapped[str] = mapped_column(
        ForeignKey("contracts.id"), nullable=False, index=True
    )
    amendment_number: Mapped[int] = mapped_column(Integer, nullable=False)
    amendment_type: Mapped[AmendmentType] = mapped_column(
        Enum(AmendmentType), nullable=False
    )
    executed_date: Mapped[Optional[date]] = mapped_column(Date)
    effective_date: Mapped[Optional[date]] = mapped_column(Date)
    previous_value_cents: Mapped[Optional[int]] = mapped_column(BigInteger)
    new_value_cents: Mapped[Optional[int]] = mapped_column(BigInteger)
    previous_end_date: Mapped[Optional[date]] = mapped_column(Date)
    new_end_date: Mapped[Optional[date]] = mapped_column(Date)
    summary_of_changes: Mapped[Optional[str]] = mapped_column(Text)
    document_link: Mapped[Optional[str]] = mapped_column(String(1024))
    record_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    contract: Mapped[Contract] = relationship(back_populates="amendments")


class ContractTerminationDetail(Base):
    """Optional one-row-per-terminated-contract record. Only populated when
    Contract.status indicates termination (terminated_by_cfa or
    terminated_by_funder). Closeout findings and correspondence links live
    here so the active-contract row stays focused.
    """

    __tablename__ = "contract_termination_details"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    contract_id: Mapped[str] = mapped_column(
        ForeignKey("contracts.id"), nullable=False, unique=True, index=True
    )
    terminated_by: Mapped[TerminatedBy] = mapped_column(
        Enum(TerminatedBy), nullable=False
    )
    termination_date: Mapped[Optional[date]] = mapped_column(Date)
    termination_reason: Mapped[Optional[str]] = mapped_column(Text)
    termination_correspondence_link: Mapped[Optional[str]] = mapped_column(String(1024))
    final_reconciliation_link: Mapped[Optional[str]] = mapped_column(String(1024))
    closeout_findings: Mapped[Optional[str]] = mapped_column(Text)
    record_created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, nullable=False
    )

    contract: Mapped[Contract] = relationship(back_populates="termination_detail")
