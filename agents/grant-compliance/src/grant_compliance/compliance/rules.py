"""Deterministic compliance rule engine.

Runs rules against transactions and allocations. All checks here are pure
functions over data — no LLM calls. The Compliance Monitor agent wraps these
and may optionally use an LLM to draft user-friendly explanations of flags.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from sqlalchemy.orm import Session

from grant_compliance.compliance.unallowable_costs import rules_triggered_by
from grant_compliance.db.models import (
    Allocation,
    AllocationStatus,
    BudgetLine,
    ComplianceFlag,
    FlagSeverity,
    Grant,
    Transaction,
)


@dataclass
class FlagDraft:
    """A flag the rule engine wants to raise. The Compliance Monitor turns
    these into ComplianceFlag rows and writes them to the audit log.
    """

    rule_id: str
    rule_citation: str
    severity: FlagSeverity
    message: str
    transaction_id: str | None = None
    allocation_id: str | None = None


# ---------------------------------------------------------------------------
# Individual rules
# ---------------------------------------------------------------------------


def check_period_of_performance(txn: Transaction, allocation: Allocation, grant: Grant) -> list[FlagDraft]:
    """2 CFR 200.309 — costs must be incurred within the period of performance."""
    flags: list[FlagDraft] = []
    if txn.txn_date < grant.period_start:
        flags.append(
            FlagDraft(
                rule_id="POP.200.309.before",
                rule_citation="2 CFR 200.309",
                severity=FlagSeverity.blocker,
                message=(
                    f"Transaction dated {txn.txn_date} is before grant period start "
                    f"{grant.period_start} for grant '{grant.name}'."
                ),
                transaction_id=txn.id,
                allocation_id=allocation.id,
            )
        )
    if txn.txn_date > grant.period_end:
        flags.append(
            FlagDraft(
                rule_id="POP.200.309.after",
                rule_citation="2 CFR 200.309",
                severity=FlagSeverity.blocker,
                message=(
                    f"Transaction dated {txn.txn_date} is after grant period end "
                    f"{grant.period_end} for grant '{grant.name}'."
                ),
                transaction_id=txn.id,
                allocation_id=allocation.id,
            )
        )
    return flags


def check_unallowable_cost_triggers(txn: Transaction) -> list[FlagDraft]:
    """Trigger 2 CFR 200 Subpart E rules based on memo/vendor text.

    Triggering a rule does NOT determine unallowability — it raises a flag
    for human review. A vendor named "Tickets, Inc." might be unrelated to
    entertainment; the human decides.
    """
    text = " ".join(filter(None, [txn.memo, txn.vendor_name]))
    triggered = rules_triggered_by(text)
    flags: list[FlagDraft] = []
    for rule in triggered:
        severity = (
            FlagSeverity.blocker if rule.status == "unallowable" else FlagSeverity.warning
        )
        flags.append(
            FlagDraft(
                rule_id=rule.rule_id,
                rule_citation=rule.citation,
                severity=severity,
                message=(
                    f"Possible match for {rule.title} ({rule.citation}). "
                    f"{rule.summary} — review whether this charge is allowable on the grant."
                ),
                transaction_id=txn.id,
            )
        )
    return flags


def check_allocation_sums(txn: Transaction) -> list[FlagDraft]:
    """Sum of approved allocations on a transaction must equal its amount."""
    approved = [
        a for a in txn.allocations if a.status == AllocationStatus.approved
    ]
    if not approved:
        return []  # nothing to check yet
    total = sum(a.amount_cents for a in approved)
    if total != txn.amount_cents:
        return [
            FlagDraft(
                rule_id="ALLOC.sum_mismatch",
                rule_citation="Internal control",
                severity=FlagSeverity.blocker,
                message=(
                    f"Approved allocations sum to {total / 100:.2f} but transaction "
                    f"amount is {txn.amount_cents / 100:.2f}."
                ),
                transaction_id=txn.id,
            )
        ]
    return []


def check_budget_overrun(
    db: Session, grant: Grant, category: str, as_of: date
) -> list[FlagDraft]:
    """Has the approved spending in `category` exceeded the budget line?"""
    # Find the active budget line version for `as_of`
    line = (
        db.query(BudgetLine)
        .filter(
            BudgetLine.grant_id == grant.id,
            BudgetLine.category == category,
            BudgetLine.effective_from <= as_of,
        )
        .order_by(BudgetLine.effective_from.desc())
        .first()
    )
    if not line:
        return []  # no budget line for this category — separate flag could be raised

    spent = (
        db.query(Allocation)
        .filter(
            Allocation.grant_id == grant.id,
            Allocation.status == AllocationStatus.approved,
            Allocation.budget_category == category,
        )
        .with_entities(Allocation.amount_cents)
        .all()
    )
    total_spent = sum(s.amount_cents for s in spent)
    if total_spent > line.budgeted_cents:
        return [
            FlagDraft(
                rule_id="BUDGET.overrun",
                rule_citation="2 CFR 200.308",
                severity=FlagSeverity.warning,
                message=(
                    f"Category '{category}' on grant '{grant.name}' is over budget: "
                    f"{total_spent / 100:.2f} approved vs. {line.budgeted_cents / 100:.2f} "
                    "budgeted. Budget revision or prior approval may be required."
                ),
            )
        ]
    return []


# ---------------------------------------------------------------------------
# Top-level runner
# ---------------------------------------------------------------------------


def run_all_for_transaction(db: Session, txn: Transaction) -> list[FlagDraft]:
    """Run all per-transaction rules. Caller writes the flags + audit log."""
    drafts: list[FlagDraft] = []
    drafts.extend(check_unallowable_cost_triggers(txn))
    drafts.extend(check_allocation_sums(txn))
    for alloc in txn.allocations:
        if alloc.status not in (AllocationStatus.approved, AllocationStatus.proposed):
            continue
        drafts.extend(check_period_of_performance(txn, alloc, alloc.grant))
    return drafts


def to_orm(draft: FlagDraft) -> ComplianceFlag:
    return ComplianceFlag(
        transaction_id=draft.transaction_id,
        allocation_id=draft.allocation_id,
        rule_id=draft.rule_id,
        rule_citation=draft.rule_citation,
        message=draft.message,
        severity=draft.severity,
    )
