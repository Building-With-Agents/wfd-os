"""Bootstrap importer — persists a LoadedBundle to the engine database.

Service layer (per CLAUDE.md "All database writes go through a service
layer, never directly from a route"). The API routes for /contracts and
the CLI entrypoint both call into this module.

Audit log discipline: every Contract / ContractAmendment /
ContractTerminationDetail row written here writes a paired audit_log
entry via grant_compliance.audit.log.write_entry. Bootstrap entries
carry full provenance — the actor (typically the email of the staff
member running the import), the source file path, and the loaded
record's record_key — so the trail back to the originating Excel row
is preserved.

Failure path: importer rolls back on any error and writes a single
"contracts.bootstrap.failed" audit_log entry (extending the failure-
path capture pattern from commit 188f931). Partial imports are not
committed.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from grant_compliance.audit.log import write_entry
from grant_compliance.contracts_bootstrap.schemas import (
    AmendmentRecord,
    ContractRecord,
    LoadedBundle,
    TerminationRecord,
)
from grant_compliance.db.models import (
    Contract,
    ContractAmendment,
    ContractTerminationDetail,
    Grant,
)


@dataclass(frozen=True)
class ImportResult:
    """Summary of what was persisted."""

    contracts_created: int
    amendments_created: int
    terminations_created: int
    record_key_to_contract_id: dict[str, str]


class ImporterError(RuntimeError):
    """Raised on importer-level problems (grant not found, etc.)."""


def import_bundle(
    db: Session,
    *,
    bundle: LoadedBundle,
    grant_id: str,
    actor: str,
    source_path: str,
) -> ImportResult:
    """Persist the bundle. Caller is responsible for db.commit().

    The importer issues db.flush() per row but does NOT commit — the
    caller wraps the whole bundle in a single transaction so a partial
    failure rolls back everything. The CLI uses one transaction per
    import; the API uses one transaction per request.

    Raises ImporterError on logical failures (missing grant). Raises
    sqlalchemy / pydantic errors on structural problems — the caller
    should catch broadly and write a "contracts.bootstrap.failed"
    audit entry on rollback.
    """
    grant = db.get(Grant, grant_id)
    if grant is None:
        raise ImporterError(f"Grant not found: grant_id={grant_id}")

    record_key_to_contract_id: dict[str, str] = {}

    for cr in bundle.contracts:
        contract = _create_contract_row(
            db,
            record=cr,
            grant_id=grant_id,
            actor=actor,
            source_path=source_path,
        )
        record_key_to_contract_id[cr.record_key] = contract.id

    for ar in bundle.amendments:
        contract_id = record_key_to_contract_id[ar.contract_record_key]
        _create_amendment_row(
            db,
            record=ar,
            contract_id=contract_id,
            actor=actor,
            source_path=source_path,
        )

    for tr in bundle.terminations:
        contract_id = record_key_to_contract_id[tr.contract_record_key]
        _create_termination_row(
            db,
            record=tr,
            contract_id=contract_id,
            actor=actor,
            source_path=source_path,
        )

    return ImportResult(
        contracts_created=len(bundle.contracts),
        amendments_created=len(bundle.amendments),
        terminations_created=len(bundle.terminations),
        record_key_to_contract_id=record_key_to_contract_id,
    )


def write_failure_entry(
    db: Session,
    *,
    actor: str,
    source_path: str,
    grant_id: str,
    error_message: str,
) -> None:
    """Record a bootstrap failure in audit_log so the trail isn't lost.

    Mirrors the failure-path capture pattern introduced in 188f931 for
    LLM calls. The caller writes this AFTER rolling back the failed
    import and BEFORE committing the audit row's own transaction.
    """
    write_entry(
        db=db,
        actor=actor,
        actor_kind="human",
        action="contracts.bootstrap.failed",
        target_type="grant",
        target_id=grant_id,
        inputs={"source_path": source_path},
        outputs={"error": error_message},
        note="Bootstrap import rolled back; no contracts persisted.",
    )
    db.commit()


# ---------- per-row writers ----------


def _create_contract_row(
    db: Session,
    *,
    record: ContractRecord,
    grant_id: str,
    actor: str,
    source_path: str,
) -> Contract:
    contract = Contract(
        grant_id=grant_id,
        vendor_name_display=record.vendor_name_display,
        vendor_legal_entity=record.vendor_legal_entity,
        vendor_qb_names=record.vendor_qb_names,
        contract_type=record.contract_type,
        compliance_classification=record.compliance_classification,
        classification_rationale=record.classification_rationale,
        procurement_method=record.procurement_method,
        original_executed_date=record.original_executed_date,
        original_effective_date=record.original_effective_date,
        current_end_date=record.current_end_date,
        original_contract_value_cents=record.original_contract_value_cents,
        current_contract_value_cents=record.current_contract_value_cents,
        status=record.status,
        payment_basis=record.payment_basis,
        payment_basis_detail=record.payment_basis_detail,
        executed_contract_link=record.executed_contract_link,
        scope_of_work_summary=record.scope_of_work_summary,
        notes=record.notes,
        record_updated_by=actor,
    )
    db.add(contract)
    db.flush()  # assigns contract.id

    write_entry(
        db=db,
        actor=actor,
        actor_kind="human",
        action="contract.create.bootstrap",
        target_type="contract",
        target_id=contract.id,
        inputs={
            "source_path": source_path,
            "record_key": record.record_key,
            "vendor_name_display": record.vendor_name_display,
            "vendor_legal_entity": record.vendor_legal_entity,
            "contract_type": record.contract_type.value,
            "compliance_classification": record.compliance_classification.value,
            "procurement_method": record.procurement_method.value,
            "original_value_cents": record.original_contract_value_cents,
            "current_value_cents": record.current_contract_value_cents,
            "status": record.status.value,
        },
        outputs={"contract_id": contract.id},
    )
    return contract


def _create_amendment_row(
    db: Session,
    *,
    record: AmendmentRecord,
    contract_id: str,
    actor: str,
    source_path: str,
) -> ContractAmendment:
    amendment = ContractAmendment(
        contract_id=contract_id,
        amendment_number=record.amendment_number,
        amendment_type=record.amendment_type,
        executed_date=record.executed_date,
        effective_date=record.effective_date,
        previous_value_cents=record.previous_value_cents,
        new_value_cents=record.new_value_cents,
        previous_end_date=record.previous_end_date,
        new_end_date=record.new_end_date,
        summary_of_changes=record.summary_of_changes,
        document_link=record.document_link,
    )
    db.add(amendment)
    db.flush()

    write_entry(
        db=db,
        actor=actor,
        actor_kind="human",
        action="contract_amendment.create.bootstrap",
        target_type="contract_amendment",
        target_id=amendment.id,
        inputs={
            "source_path": source_path,
            "contract_id": contract_id,
            "amendment_number": record.amendment_number,
            "amendment_type": record.amendment_type.value,
            "previous_value_cents": record.previous_value_cents,
            "new_value_cents": record.new_value_cents,
        },
        outputs={"amendment_id": amendment.id},
    )
    return amendment


def _create_termination_row(
    db: Session,
    *,
    record: TerminationRecord,
    contract_id: str,
    actor: str,
    source_path: str,
) -> ContractTerminationDetail:
    termination = ContractTerminationDetail(
        contract_id=contract_id,
        terminated_by=record.terminated_by,
        termination_date=record.termination_date,
        termination_reason=record.termination_reason,
        termination_correspondence_link=record.termination_correspondence_link,
        final_reconciliation_link=record.final_reconciliation_link,
        closeout_findings=record.closeout_findings,
    )
    db.add(termination)
    db.flush()

    write_entry(
        db=db,
        actor=actor,
        actor_kind="human",
        action="contract_termination.create.bootstrap",
        target_type="contract_termination_detail",
        target_id=termination.id,
        inputs={
            "source_path": source_path,
            "contract_id": contract_id,
            "terminated_by": record.terminated_by.value,
            "termination_date": (
                record.termination_date.isoformat()
                if isinstance(record.termination_date, date)
                else None
            ),
        },
        outputs={"termination_id": termination.id},
    )
    return termination


# ---------- API-driven writers (single-row create / update via endpoints) ----------


def create_contract_from_record(
    db: Session,
    *,
    record: ContractRecord,
    grant_id: str,
    actor: str,
) -> Contract:
    """Create a single contract via the API path (not bootstrap).

    Same audit discipline; different action label so the audit trail
    distinguishes API creates from bulk bootstrap creates.
    """
    grant = db.get(Grant, grant_id)
    if grant is None:
        raise ImporterError(f"Grant not found: grant_id={grant_id}")

    contract = Contract(
        grant_id=grant_id,
        vendor_name_display=record.vendor_name_display,
        vendor_legal_entity=record.vendor_legal_entity,
        vendor_qb_names=record.vendor_qb_names,
        contract_type=record.contract_type,
        compliance_classification=record.compliance_classification,
        classification_rationale=record.classification_rationale,
        procurement_method=record.procurement_method,
        original_executed_date=record.original_executed_date,
        original_effective_date=record.original_effective_date,
        current_end_date=record.current_end_date,
        original_contract_value_cents=record.original_contract_value_cents,
        current_contract_value_cents=record.current_contract_value_cents,
        status=record.status,
        payment_basis=record.payment_basis,
        payment_basis_detail=record.payment_basis_detail,
        executed_contract_link=record.executed_contract_link,
        scope_of_work_summary=record.scope_of_work_summary,
        notes=record.notes,
        record_updated_by=actor,
    )
    db.add(contract)
    db.flush()

    write_entry(
        db=db,
        actor=actor,
        actor_kind="human",
        action="contract.create.api",
        target_type="contract",
        target_id=contract.id,
        inputs={
            "vendor_name_display": record.vendor_name_display,
            "vendor_legal_entity": record.vendor_legal_entity,
            "contract_type": record.contract_type.value,
            "compliance_classification": record.compliance_classification.value,
            "procurement_method": record.procurement_method.value,
        },
        outputs={"contract_id": contract.id},
    )
    return contract


def update_contract_from_record(
    db: Session,
    *,
    contract: Contract,
    record: ContractRecord,
    actor: str,
) -> Contract:
    """Update a single contract via the API path. Records the previous
    field values in the audit_log inputs so before/after is reconstructible.
    """
    before = {
        "vendor_name_display": contract.vendor_name_display,
        "vendor_legal_entity": contract.vendor_legal_entity,
        "vendor_qb_names": list(contract.vendor_qb_names or []),
        "contract_type": contract.contract_type.value,
        "compliance_classification": contract.compliance_classification.value,
        "procurement_method": contract.procurement_method.value,
        "current_contract_value_cents": contract.current_contract_value_cents,
        "current_end_date": (
            contract.current_end_date.isoformat()
            if isinstance(contract.current_end_date, date)
            else None
        ),
        "status": contract.status.value,
        "payment_basis": contract.payment_basis.value,
    }

    contract.vendor_name_display = record.vendor_name_display
    contract.vendor_legal_entity = record.vendor_legal_entity
    contract.vendor_qb_names = record.vendor_qb_names
    contract.contract_type = record.contract_type
    contract.compliance_classification = record.compliance_classification
    contract.classification_rationale = record.classification_rationale
    contract.procurement_method = record.procurement_method
    contract.original_executed_date = record.original_executed_date
    contract.original_effective_date = record.original_effective_date
    contract.current_end_date = record.current_end_date
    contract.original_contract_value_cents = record.original_contract_value_cents
    contract.current_contract_value_cents = record.current_contract_value_cents
    contract.status = record.status
    contract.payment_basis = record.payment_basis
    contract.payment_basis_detail = record.payment_basis_detail
    contract.executed_contract_link = record.executed_contract_link
    contract.scope_of_work_summary = record.scope_of_work_summary
    contract.notes = record.notes
    contract.record_updated_by = actor
    from datetime import datetime as _dt
    from datetime import timezone as _tz
    contract.record_updated_at = _dt.now(_tz.utc)
    db.flush()

    write_entry(
        db=db,
        actor=actor,
        actor_kind="human",
        action="contract.update.api",
        target_type="contract",
        target_id=contract.id,
        inputs={"before": before},
        outputs={
            "contract_id": contract.id,
            "after": {
                "vendor_name_display": contract.vendor_name_display,
                "vendor_legal_entity": contract.vendor_legal_entity,
                "contract_type": contract.contract_type.value,
                "compliance_classification": contract.compliance_classification.value,
                "procurement_method": contract.procurement_method.value,
                "current_contract_value_cents": contract.current_contract_value_cents,
                "status": contract.status.value,
            },
        },
    )
    return contract
