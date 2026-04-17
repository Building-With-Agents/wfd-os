"""Tests for the Transaction Classifier (deterministic path only — the LLM
path is exercised manually with LLM_PROVIDER=anthropic).
"""

from __future__ import annotations

from datetime import date

from grant_compliance.agents.classifier import TransactionClassifier
from grant_compliance.db.models import (
    AllocationStatus,
    Funder,
    FunderType,
    Grant,
    QbClass,
    Transaction,
)


def test_classifier_uses_qb_class_when_unique(db):
    funder = Funder(name="F", funder_type=FunderType.federal)
    db.add(funder)
    db.flush()

    grant = Grant(
        funder_id=funder.id,
        name="G",
        qb_class_name="Federal:CHI",
        period_start=date(2025, 1, 1),
        period_end=date(2026, 12, 31),
        total_award_cents=1_000_000,
    )
    db.add(grant)

    qb_class = QbClass(qb_id="C1", name="Federal:CHI")
    db.add(qb_class)
    db.flush()

    txn = Transaction(
        qb_id="t1",
        qb_type="Bill",
        txn_date=date(2025, 6, 1),
        amount_cents=10000,
        qb_class_id=qb_class.id,
    )
    db.add(txn)
    db.flush()

    classifier = TransactionClassifier(db)
    allocations = classifier.classify(txn)

    assert len(allocations) == 1
    assert allocations[0].grant_id == grant.id
    assert allocations[0].amount_cents == 10000
    assert allocations[0].confidence == 0.99
    assert allocations[0].status == AllocationStatus.proposed  # never auto-approved


def test_classifier_returns_empty_when_no_active_grants(db):
    txn = Transaction(
        qb_id="t1", qb_type="Bill", txn_date=date(2025, 6, 1), amount_cents=10000
    )
    db.add(txn)
    db.flush()
    classifier = TransactionClassifier(db)
    assert classifier.classify(txn) == []
