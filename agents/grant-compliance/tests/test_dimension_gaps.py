"""Tests for the per-dimension gap endpoint and the underlying
gaps_for_* functions.

Covers the step 4 engine-side scope from
agents/grant-compliance/docs/audit_readiness_tab_spec.md §v1.2.7.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import HTTPException

from grant_compliance.api.routes.compliance import list_dimension_gaps
from grant_compliance.compliance.audit_dimensions import dimension_ids
from grant_compliance.compliance.dimension_readiness import (
    DEFAULT_DOCUMENTATION_THRESHOLD_CENTS,
    GAP_FUNCTIONS,
    gaps_for_allowable_costs,
    gaps_for_performance_reporting,
    gaps_for_procurement,
    gaps_for_subrecipient_monitoring,
    gaps_for_time_effort,
    gaps_for_transaction_documentation,
    placeholder_message_for,
)
from grant_compliance.db.models import (
    ComplianceFlag,
    FlagSeverity,
    FlagStatus,
    Transaction,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_txn(
    db,
    qb_id: str,
    amount_cents: int = 100_000,
    vendor_name: str | None = None,
    memo: str | None = None,
    attachment_count: int = 0,
):
    qb_type, _ = qb_id.split(":", 1)
    t = Transaction(
        qb_id=qb_id,
        qb_type=qb_type,
        txn_date=date(2025, 6, 1),
        amount_cents=amount_cents,
        vendor_name=vendor_name,
        memo=memo,
        attachment_count=attachment_count,
    )
    db.add(t)
    db.flush()
    return t


def _mk_flag(
    db,
    txn,
    rule_id: str = "UC.200.423",
    rule_citation: str = "2 CFR 200.423",
    message: str = "test flag message",
    severity: FlagSeverity = FlagSeverity.warning,
    status: FlagStatus = FlagStatus.open,
    raised_at: datetime | None = None,
):
    f = ComplianceFlag(
        transaction_id=txn.id,
        rule_id=rule_id,
        rule_citation=rule_citation,
        message=message,
        severity=severity,
        status=status,
    )
    if raised_at is not None:
        f.raised_at = raised_at
    db.add(f)
    db.flush()
    return f


# ---------------------------------------------------------------------------
# Endpoint — 404 on unknown dimension
# ---------------------------------------------------------------------------


def test_endpoint_returns_404_for_unknown_dimension(db):
    with pytest.raises(HTTPException) as excinfo:
        list_dimension_gaps(dimension_id="not_a_real_dimension", db=db)
    assert excinfo.value.status_code == 404


def test_endpoint_dispatch_table_covers_every_canonical_dimension(db):
    """Every canonical dimension must have a gap function."""
    assert set(GAP_FUNCTIONS.keys()) == set(dimension_ids())


# ---------------------------------------------------------------------------
# Endpoint response shape
# ---------------------------------------------------------------------------


def test_endpoint_shape_for_computed_dimension(db):
    result = list_dimension_gaps(dimension_id="allowable_costs", db=db)
    assert result["dimension_id"] == "allowable_costs"
    assert result["status"] == "computed"
    assert result["gap_count"] == 0
    assert result["gaps"] == []
    assert "placeholder_message" not in result
    assert "computed_at" in result
    # ISO 8601 with timezone — round-trippable via fromisoformat
    datetime.fromisoformat(result["computed_at"])


def test_endpoint_shape_for_placeholder_dimension(db):
    result = list_dimension_gaps(dimension_id="time_effort", db=db)
    assert result["dimension_id"] == "time_effort"
    assert result["status"] == "placeholder"
    assert result["gap_count"] == 0
    assert result["gaps"] == []
    assert "placeholder_message" in result
    assert result["placeholder_message"].startswith("Gap detection not yet available.")


# ---------------------------------------------------------------------------
# Allowable costs — real gap data
# ---------------------------------------------------------------------------


def test_allowable_costs_one_gap_per_unresolved_subpart_e_flag(db):
    t = _mk_txn(db, "Bill:1", vendor_name="Wine Shop", amount_cents=8_500)
    _mk_flag(db, t, rule_id="UC.200.423", message="Alcohol — §200.423")
    gaps = gaps_for_allowable_costs(db)
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap["type"] == "compliance_flag"
    assert "200.423" in gap["title"]
    assert gap["detail"] == "Alcohol — §200.423"
    assert gap["metadata"]["vendor_name"] == "Wine Shop"
    assert gap["metadata"]["amount_dollars"] == 85.0
    assert gap["metadata"]["qb_id"] == "Bill:1"
    assert gap["metadata"]["severity"] == "warning"


def test_allowable_costs_ignores_resolved_and_waived_flags(db):
    t = _mk_txn(db, "Bill:1")
    _mk_flag(db, t, rule_id="UC.200.421", status=FlagStatus.resolved)
    _mk_flag(db, t, rule_id="UC.200.423", status=FlagStatus.waived)
    _mk_flag(db, t, rule_id="UC.200.438", status=FlagStatus.open)
    gaps = gaps_for_allowable_costs(db)
    assert len(gaps) == 1
    # Only the open one should appear
    assert "200.438" in gaps[0]["title"]


def test_allowable_costs_multiple_flags_on_one_txn_each_become_own_gap(db):
    """Distinct from the dimension pct (which counts distinct txns).
    A transaction with two Subpart E flags yields two gap entries."""
    t = _mk_txn(db, "Bill:1", vendor_name="Vendor A", amount_cents=12_000)
    _mk_flag(db, t, rule_id="UC.200.421")
    _mk_flag(db, t, rule_id="UC.200.438")
    gaps = gaps_for_allowable_costs(db)
    assert len(gaps) == 2
    # Both should reference the same transaction in metadata
    qb_ids = {g["metadata"]["qb_id"] for g in gaps}
    assert qb_ids == {"Bill:1"}


def test_allowable_costs_ignores_non_subpart_e_flags(db):
    t = _mk_txn(db, "Bill:1")
    _mk_flag(db, t, rule_id="POP.200.309", rule_citation="2 CFR 200.309")
    gaps = gaps_for_allowable_costs(db)
    assert gaps == []


def test_allowable_costs_sort_severity_desc_then_raised_at_desc(db):
    now = datetime.now(timezone.utc)
    t = _mk_txn(db, "Bill:1")
    # Create in scrambled order so we know the sort is doing work
    _mk_flag(db, t, rule_id="UC.200.421", severity=FlagSeverity.info,
             raised_at=now - timedelta(days=3))
    _mk_flag(db, t, rule_id="UC.200.423", severity=FlagSeverity.blocker,
             raised_at=now - timedelta(days=2))
    _mk_flag(db, t, rule_id="UC.200.438", severity=FlagSeverity.warning,
             raised_at=now - timedelta(days=1))
    _mk_flag(db, t, rule_id="UC.200.442", severity=FlagSeverity.blocker,
             raised_at=now)  # newer blocker — should be first

    gaps = gaps_for_allowable_costs(db)
    severities = [g["metadata"]["severity"] for g in gaps]
    # blocker, blocker, warning, info
    assert severities == ["blocker", "blocker", "warning", "info"]
    # within the two blockers, newer comes first
    assert "200.442" in gaps[0]["title"]
    assert "200.423" in gaps[1]["title"]


def test_allowable_costs_title_format_uses_section_and_rule_title(db):
    """Title should be "§{section} — {rule_title}" when the rule is known."""
    t = _mk_txn(db, "Bill:1")
    # UC.200.423 is "Alcoholic beverages" per unallowable_costs.RULES
    _mk_flag(db, t, rule_id="UC.200.423")
    gaps = gaps_for_allowable_costs(db)
    assert gaps[0]["title"] == "§200.423 — Alcoholic beverages"


# ---------------------------------------------------------------------------
# Transaction documentation — real gap data
# ---------------------------------------------------------------------------


def test_transaction_documentation_lists_missing_doc_txns_above_threshold(db):
    _mk_txn(db, "Bill:1", vendor_name="Vendor A", amount_cents=500_000, attachment_count=0)  # missing
    _mk_txn(db, "Bill:2", vendor_name="Vendor B", amount_cents=500_000, attachment_count=1)  # documented
    _mk_txn(db, "Bill:3", vendor_name="Vendor C", amount_cents=100_000, attachment_count=0)  # below threshold
    gaps = gaps_for_transaction_documentation(db)
    assert len(gaps) == 1
    gap = gaps[0]
    assert gap["type"] == "missing_documentation"
    assert gap["metadata"]["vendor_name"] == "Vendor A"
    assert gap["metadata"]["qb_id"] == "Bill:1"
    assert gap["metadata"]["amount_dollars"] == 5000.0
    assert "Vendor A" in gap["title"]
    assert "$5,000" in gap["title"]
    assert "Threshold: $2,500" in gap["detail"]


def test_transaction_documentation_sorted_by_amount_desc(db):
    _mk_txn(db, "Bill:1", vendor_name="Small", amount_cents=300_000)
    _mk_txn(db, "Bill:2", vendor_name="Big", amount_cents=1_000_000)
    _mk_txn(db, "Bill:3", vendor_name="Middle", amount_cents=500_000)
    gaps = gaps_for_transaction_documentation(db)
    amounts = [g["metadata"]["amount_dollars"] for g in gaps]
    assert amounts == sorted(amounts, reverse=True)
    assert amounts == [10000.0, 5000.0, 3000.0]


def test_transaction_documentation_respects_threshold_parameter(db):
    _mk_txn(db, "Bill:1", amount_cents=500_000, attachment_count=0)
    _mk_txn(db, "Bill:2", amount_cents=200_000, attachment_count=0)
    # Default threshold $2,500 → both included (both >= 2000)? No, 200_000 = $2000 < $2500.
    # Let's use a different threshold to verify the parameter.
    high_threshold = gaps_for_transaction_documentation(db, threshold_cents=400_000)
    assert len(high_threshold) == 1
    low_threshold = gaps_for_transaction_documentation(db, threshold_cents=100_000)
    assert len(low_threshold) == 2


def test_transaction_documentation_vendor_name_fallback_for_none(db):
    _mk_txn(db, "Bill:1", vendor_name=None, amount_cents=500_000)
    gaps = gaps_for_transaction_documentation(db)
    assert gaps[0]["title"].startswith("Unknown vendor — $")


def test_transaction_documentation_default_threshold_matches_constant(db):
    # Default used when threshold_cents not passed
    _mk_txn(db, "Bill:1", amount_cents=250_000, attachment_count=0)
    gaps = gaps_for_transaction_documentation(db)
    assert len(gaps) == 1
    assert gaps[0]["metadata"]["threshold_dollars"] == DEFAULT_DOCUMENTATION_THRESHOLD_CENTS / 100


# ---------------------------------------------------------------------------
# Placeholder dimensions
# ---------------------------------------------------------------------------


def test_each_placeholder_dimension_returns_empty_gaps(db):
    assert gaps_for_time_effort(db) == []
    assert gaps_for_procurement(db) == []
    assert gaps_for_subrecipient_monitoring(db) == []
    assert gaps_for_performance_reporting(db) == []


def test_placeholder_messages_match_spec_text():
    """Exact text from audit_readiness_tab_spec.md §v1.2.7. Drift here
    should fail this test so the spec and code stay aligned."""
    assert placeholder_message_for("time_effort") == (
        "Gap detection not yet available. When Employee↔Grant "
        "assignment data is added (v1.3+), this drill will show "
        "employees who lack required quarterly certifications for "
        "the current and prior closed periods."
    )
    assert placeholder_message_for("procurement") == (
        "Gap detection not yet available. When procurement record "
        "tracking is added (v1.3+), this drill will show contracts "
        "above threshold lacking documented competitive process or "
        "sole-source justification."
    )
    assert placeholder_message_for("subrecipient_monitoring") == (
        "Gap detection not yet available. When subrecipient risk "
        "assessment tracking is added (v1.3+), this drill will show "
        "subrecipients lacking current risk assessment, monitoring "
        "records, or audit follow-up."
    )
    assert placeholder_message_for("performance_reporting") == (
        "Gap detection not yet available. When WSAC reconciliation "
        "tracking is added (v1.3+), this drill will show reported "
        "placements not reconcilable to source data."
    )


def test_placeholder_message_is_none_for_computed_dimensions():
    assert placeholder_message_for("allowable_costs") is None
    assert placeholder_message_for("transaction_documentation") is None


def test_placeholder_message_is_none_for_unknown_dimension():
    assert placeholder_message_for("banana") is None


# ---------------------------------------------------------------------------
# Endpoint wires to the canonical constants (no duplication)
# ---------------------------------------------------------------------------


def test_endpoint_placeholder_message_reads_from_canonical_constants(db, monkeypatch):
    """Monkeypatch the canonical placeholder map and verify the endpoint
    reflects the patch — proves there's no second copy of the text in
    the route handler."""
    from grant_compliance.compliance import dimension_readiness

    patched = dict(dimension_readiness._PLACEHOLDER_MESSAGES)
    patched["time_effort"] = "[PATCHED] test message"
    monkeypatch.setattr(
        dimension_readiness, "_PLACEHOLDER_MESSAGES", patched
    )

    result = list_dimension_gaps(dimension_id="time_effort", db=db)
    assert result["placeholder_message"] == "[PATCHED] test message"


# ---------------------------------------------------------------------------
# Endpoint integration — computed_at + full response shape for both modes
# ---------------------------------------------------------------------------


def test_endpoint_returns_real_gaps_for_allowable_costs(db):
    t = _mk_txn(db, "Bill:1", vendor_name="Liquor Co", amount_cents=3_500)
    _mk_flag(db, t, rule_id="UC.200.423", message="Wine for donor gala")
    result = list_dimension_gaps(dimension_id="allowable_costs", db=db)
    assert result["status"] == "computed"
    assert result["gap_count"] == 1
    assert result["gaps"][0]["type"] == "compliance_flag"
    assert "200.423" in result["gaps"][0]["title"]


def test_endpoint_returns_real_gaps_for_transaction_documentation(db):
    _mk_txn(db, "Bill:1", vendor_name="Big Vendor", amount_cents=1_200_000)
    result = list_dimension_gaps(dimension_id="transaction_documentation", db=db)
    assert result["status"] == "computed"
    assert result["gap_count"] == 1
    assert result["gaps"][0]["type"] == "missing_documentation"
    assert "$12,000" in result["gaps"][0]["title"]
