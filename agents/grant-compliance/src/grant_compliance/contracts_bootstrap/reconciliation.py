"""Amendment 1 reconciliation for the Contracts inventory.

Computes per-budget-line sums of contract values and compares them to
the Amendment 1 line totals (the canonical budgeted amounts the grant
expects to spend). Drift is surfaced prominently — same honesty
discipline as Personnel.

Per the spec:
    - Sum of current_contract_value_cents for contract_type =
      training_provider OR strategic_partner_subrecipient should
      reconcile to the GJC Contractors line: $2,315,623.07
    - Sum for contract_type = cfa_contractor should reconcile to the
      CFA Contractors line: $1,020,823.40

If the totals don't reconcile, the response surfaces the drift in
cents (signed: positive = under budget, negative = over budget).
A drift threshold of $0.01 (one cent) is treated as zero drift since
it's almost always a floating-point rounding artifact.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.db.models import Contract, ContractType


# Amendment 1 reference totals in cents — per the spec.
GJC_CONTRACTORS_LINE_CENTS = 231_562_307  # $2,315,623.07
CFA_CONTRACTORS_LINE_CENTS = 102_082_340  # $1,020,823.40

# Below this absolute drift, reconciliation passes silently. One cent
# of floating-point rounding is not a real drift event.
RECONCILIATION_TOLERANCE_CENTS = 1


@dataclass(frozen=True)
class BudgetLineReconciliation:
    """One Amendment 1 budget line and its computed actual."""

    budget_line: str  # human label, e.g. "GJC Contractors"
    contract_types: tuple[str, ...]  # ContractType values feeding this line
    expected_cents: int  # Amendment 1 amount
    actual_cents: int  # sum of current_contract_value_cents over the types
    contract_count: int
    drift_cents: int  # actual - expected (positive = over, negative = under)
    reconciles: bool

    def to_dict(self) -> dict:
        return {
            "budget_line": self.budget_line,
            "contract_types": list(self.contract_types),
            "expected_cents": self.expected_cents,
            "actual_cents": self.actual_cents,
            "contract_count": self.contract_count,
            "drift_cents": self.drift_cents,
            "reconciles": self.reconciles,
        }


@dataclass(frozen=True)
class ReconciliationReport:
    """Top-level reconciliation result for a grant."""

    grant_id: str
    lines: list[BudgetLineReconciliation]
    overall_reconciles: bool
    warnings: list[str]  # human-readable drift warnings, surfaced in UI

    def to_dict(self) -> dict:
        return {
            "grant_id": self.grant_id,
            "lines": [line.to_dict() for line in self.lines],
            "overall_reconciles": self.overall_reconciles,
            "warnings": list(self.warnings),
        }


def compute_reconciliation(db: Session, *, grant_id: str) -> ReconciliationReport:
    """Compute the Amendment 1 reconciliation for a grant."""

    gjc_types = (
        ContractType.training_provider,
        ContractType.strategic_partner_subrecipient,
    )
    cfa_types = (ContractType.cfa_contractor,)

    gjc_line = _compute_line(
        db,
        grant_id=grant_id,
        budget_line="GJC Contractors (Amendment 1)",
        contract_types=gjc_types,
        expected_cents=GJC_CONTRACTORS_LINE_CENTS,
    )
    cfa_line = _compute_line(
        db,
        grant_id=grant_id,
        budget_line="CFA Contractors (Amendment 1)",
        contract_types=cfa_types,
        expected_cents=CFA_CONTRACTORS_LINE_CENTS,
    )

    lines = [gjc_line, cfa_line]
    overall = all(line.reconciles for line in lines)

    warnings: list[str] = []
    for line in lines:
        if not line.reconciles:
            direction = "over" if line.drift_cents > 0 else "under"
            warnings.append(
                f"{line.budget_line}: actual ${line.actual_cents / 100:,.2f} is "
                f"{direction} expected ${line.expected_cents / 100:,.2f} by "
                f"${abs(line.drift_cents) / 100:,.2f} "
                f"({line.contract_count} contract{'s' if line.contract_count != 1 else ''})"
            )

    return ReconciliationReport(
        grant_id=grant_id,
        lines=lines,
        overall_reconciles=overall,
        warnings=warnings,
    )


def _compute_line(
    db: Session,
    *,
    grant_id: str,
    budget_line: str,
    contract_types: tuple[ContractType, ...],
    expected_cents: int,
) -> BudgetLineReconciliation:
    stmt = select(Contract).where(
        Contract.grant_id == grant_id,
        Contract.contract_type.in_(contract_types),
    )
    contracts = list(db.execute(stmt).scalars())
    actual_cents = sum(c.current_contract_value_cents for c in contracts)
    drift_cents = actual_cents - expected_cents
    reconciles = abs(drift_cents) <= RECONCILIATION_TOLERANCE_CENTS
    return BudgetLineReconciliation(
        budget_line=budget_line,
        contract_types=tuple(t.value for t in contract_types),
        expected_cents=expected_cents,
        actual_cents=actual_cents,
        contract_count=len(contracts),
        drift_cents=drift_cents,
        reconciles=reconciles,
    )
