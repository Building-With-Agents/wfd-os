"""Pydantic record shapes for the contracts bootstrap importer.

These mirror the SQLAlchemy models in db/models.py but represent Excel-
loaded records before persistence — the data has been parsed and validated
but not yet given UUIDs or persisted. The importer maps these one-to-one
onto SQLAlchemy rows, then writes audit_log entries.

Money values arrive in dollars (Excel-friendly) and are converted to
cents at import time to match engine convention. Dates arrive as ISO
strings or Python date objects; the loader normalizes both.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from grant_compliance.db.models import (
    AmendmentType,
    ComplianceClassification,
    ContractStatus,
    ContractType,
    PaymentBasis,
    ProcurementMethod,
    TerminatedBy,
)


class ContractRecord(BaseModel):
    """One row from the Contracts sheet.

    `record_key` is a stable in-spreadsheet identifier (often the vendor
    display name) used to wire amendments and terminations to the parent
    contract. It does NOT become the database primary key — the importer
    generates UUIDs at persist time and returns a record_key → contract_id
    map for the amendment/termination linking.
    """

    model_config = ConfigDict(extra="forbid")

    record_key: str = Field(..., min_length=1)
    vendor_name_display: str = Field(..., min_length=1)
    vendor_legal_entity: str = Field(..., min_length=1)
    vendor_qb_names: list[str] = Field(default_factory=list)

    contract_type: ContractType
    compliance_classification: ComplianceClassification = (
        ComplianceClassification.unclassified
    )
    classification_rationale: Optional[str] = None

    # Promoted to v1 per 2026-04-30 spec amendment. Default `unknown`
    # so contracts whose method Krista hasn't yet confirmed are visibly
    # un-classified rather than silently mis-attributed.
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

    @field_validator("vendor_qb_names", mode="before")
    @classmethod
    def _split_pipe_delimited(cls, v: object) -> list[str]:
        # Excel cells often hold "Name1|Name2|Name3" — accept either a
        # native list or a pipe-delimited string and produce a clean list.
        if v is None or v == "":
            return []
        if isinstance(v, list):
            return [str(s).strip() for s in v if str(s).strip()]
        return [s.strip() for s in str(v).split("|") if s.strip()]


class AmendmentRecord(BaseModel):
    """One row from the Amendments sheet.

    `contract_record_key` references a ContractRecord.record_key in the
    Contracts sheet. The importer resolves it to a contract_id at
    persistence time.
    """

    model_config = ConfigDict(extra="forbid")

    contract_record_key: str = Field(..., min_length=1)
    amendment_number: int = Field(..., ge=1)
    amendment_type: AmendmentType

    executed_date: Optional[date] = None
    effective_date: Optional[date] = None
    previous_value_cents: Optional[int] = Field(None, ge=0)
    new_value_cents: Optional[int] = Field(None, ge=0)
    previous_end_date: Optional[date] = None
    new_end_date: Optional[date] = None
    summary_of_changes: Optional[str] = None
    document_link: Optional[str] = None


class TerminationRecord(BaseModel):
    """One row from the Terminations sheet.

    `contract_record_key` references a ContractRecord.record_key in the
    Contracts sheet. One-to-one with the parent Contract; the importer
    enforces the unique constraint.
    """

    model_config = ConfigDict(extra="forbid")

    contract_record_key: str = Field(..., min_length=1)
    terminated_by: TerminatedBy
    termination_date: Optional[date] = None
    termination_reason: Optional[str] = None
    termination_correspondence_link: Optional[str] = None
    final_reconciliation_link: Optional[str] = None
    closeout_findings: Optional[str] = None


class LoadedBundle(BaseModel):
    """Aggregate result of the loader — what one Excel file produces."""

    model_config = ConfigDict(extra="forbid")

    contracts: list[ContractRecord]
    amendments: list[AmendmentRecord]
    terminations: list[TerminationRecord]

    @property
    def contract_record_keys(self) -> set[str]:
        return {c.record_key for c in self.contracts}

    def validate_cross_references(self) -> list[str]:
        """Return a list of validation errors (empty if cross-refs are clean).

        Specifically: every amendment / termination must reference a
        record_key that exists in the contracts list. We surface this
        instead of crashing so the loader can report all missing keys
        in one pass.
        """
        errors: list[str] = []
        keys = self.contract_record_keys
        for a in self.amendments:
            if a.contract_record_key not in keys:
                errors.append(
                    f"Amendment {a.amendment_number} references unknown "
                    f"contract record_key '{a.contract_record_key}'"
                )
        for t in self.terminations:
            if t.contract_record_key not in keys:
                errors.append(
                    f"Termination references unknown contract record_key "
                    f"'{t.contract_record_key}'"
                )
        # Multiple terminations per contract not allowed.
        seen: set[str] = set()
        for t in self.terminations:
            if t.contract_record_key in seen:
                errors.append(
                    f"Multiple terminations for contract record_key "
                    f"'{t.contract_record_key}' — only one allowed"
                )
            seen.add(t.contract_record_key)
        return errors
