"""Tests for the deterministic compliance rule engine."""

from __future__ import annotations

from datetime import date

from grant_compliance.compliance.rules import (
    check_period_of_performance,
    check_unallowable_cost_triggers,
)
from grant_compliance.compliance.unallowable_costs import get_rule, rules_triggered_by
from grant_compliance.db.models import (
    Allocation,
    AllocationStatus,
    Funder,
    FunderType,
    Grant,
    Transaction,
)


def _grant(db, **kwargs):
    funder = Funder(name="Test Funder", funder_type=FunderType.federal)
    db.add(funder)
    db.flush()
    defaults = dict(
        funder_id=funder.id,
        name="Test Grant",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 12, 31),
        total_award_cents=10_000_000,
    )
    defaults.update(kwargs)
    g = Grant(**defaults)
    db.add(g)
    db.flush()
    return g


def test_alcohol_rule_triggers_on_wine_in_memo():
    triggered = rules_triggered_by("Wine and cheese for donor event")
    rule_ids = [r.rule_id for r in triggered]
    assert "UC.200.423" in rule_ids


def test_lobbying_rule_triggers():
    triggered = rules_triggered_by("Lobbying services Q4")
    assert any(r.rule_id == "UC.200.450" for r in triggered)


def test_no_trigger_on_innocuous_text():
    triggered = rules_triggered_by("Office supplies for clinical staff")
    assert triggered == []


def test_period_of_performance_after_end(db):
    grant = _grant(db)
    txn = Transaction(
        qb_id="t1",
        qb_type="Bill",
        txn_date=date(2026, 1, 5),  # after grant end
        amount_cents=10000,
    )
    db.add(txn)
    db.flush()
    alloc = Allocation(
        transaction_id=txn.id,
        grant_id=grant.id,
        amount_cents=10000,
        status=AllocationStatus.proposed,
    )
    db.add(alloc)
    db.flush()
    flags = check_period_of_performance(txn, alloc, grant)
    assert any("after grant period end" in f.message for f in flags)


def test_period_of_performance_within_range_is_clean(db):
    grant = _grant(db)
    txn = Transaction(
        qb_id="t2",
        qb_type="Bill",
        txn_date=date(2025, 6, 15),
        amount_cents=5000,
    )
    db.add(txn)
    db.flush()
    alloc = Allocation(
        transaction_id=txn.id,
        grant_id=grant.id,
        amount_cents=5000,
        status=AllocationStatus.proposed,
    )
    db.add(alloc)
    flags = check_period_of_performance(txn, alloc, grant)
    assert flags == []


def test_unallowable_cost_check_finds_alcohol():
    txn = Transaction(
        qb_id="t3",
        qb_type="Bill",
        txn_date=date(2025, 6, 1),
        memo="Champagne for board dinner",
        amount_cents=20000,
    )
    flags = check_unallowable_cost_triggers(txn)
    assert any(f.rule_id == "UC.200.423" for f in flags)


def test_get_rule_returns_known_rule():
    rule = get_rule("UC.200.450")
    assert rule is not None
    assert "Lobbying" in rule.title
