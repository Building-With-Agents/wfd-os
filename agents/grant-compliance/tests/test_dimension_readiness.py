"""Tests for step 2 engine-side implementation:

- Transaction.last_scanned_at column + migration
- ComplianceMonitor stamps last_scanned_at on every scan
- transactions_above_threshold_total helper
- compute_allowable_costs / compute_transaction_documentation
- Placeholder compute functions return None
- GET /compliance/dimensions endpoint shape
"""

from __future__ import annotations

import importlib.util
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from grant_compliance.agents.compliance import ComplianceMonitor
from grant_compliance.api.routes.compliance import list_dimensions
from grant_compliance.compliance.audit_dimensions import DIMENSIONS, dimension_ids
from grant_compliance.compliance.dimension_readiness import (
    COMPUTE_FUNCTIONS,
    COMPUTED_DIMENSIONS,
    compute_allowable_costs,
    compute_performance_reporting,
    compute_procurement,
    compute_subrecipient_monitoring,
    compute_time_effort,
    compute_transaction_documentation,
)
from grant_compliance.db.models import (
    ComplianceFlag,
    FlagSeverity,
    FlagStatus,
    Transaction,
)
from grant_compliance.db.queries import transactions_above_threshold_total


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_txn(
    db,
    qb_id: str,
    amount_cents: int = 100_000,
    memo: str | None = None,
    last_scanned_at: datetime | None = None,
    attachment_count: int = 0,
):
    qb_type, _ = qb_id.split(":", 1)
    t = Transaction(
        qb_id=qb_id,
        qb_type=qb_type,
        txn_date=date(2025, 6, 1),
        amount_cents=amount_cents,
        memo=memo,
        attachment_count=attachment_count,
        last_scanned_at=last_scanned_at,
    )
    db.add(t)
    db.flush()
    return t


def _mk_flag(db, txn, rule_id: str = "UC.200.423", status: FlagStatus = FlagStatus.open):
    f = ComplianceFlag(
        transaction_id=txn.id,
        rule_id=rule_id,
        rule_citation=f"2 CFR {rule_id.split('.', 1)[1]}",
        message="test",
        severity=FlagSeverity.warning,
        status=status,
    )
    db.add(f)
    db.flush()
    return f


# ---------------------------------------------------------------------------
# Column + migration
# ---------------------------------------------------------------------------


def test_last_scanned_at_defaults_to_none(db):
    t = _mk_txn(db, "Bill:1")
    db.flush()
    db.refresh(t)
    assert t.last_scanned_at is None


def test_migration_file_is_well_formed():
    versions_dir = (
        Path(__file__).resolve().parent.parent / "alembic" / "versions"
    )
    matches = list(versions_dir.glob("*_add_last_scanned_at_to_transactions.py"))
    assert len(matches) == 1
    path = matches[0]

    spec = importlib.util.spec_from_file_location("migration_under_test_2", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "8d2b4a91c0f7"
    assert module.down_revision == "7c1fa8b3d2e4"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    src = path.read_text(encoding="utf-8")
    assert "op.add_column" in src
    assert "op.drop_column" in src
    assert "last_scanned_at" in src
    assert "'transactions'" in src
    assert "schema='grant_compliance'" in src
    assert "nullable=True" in src


# ---------------------------------------------------------------------------
# ComplianceMonitor stamps last_scanned_at
# ---------------------------------------------------------------------------


def test_scan_transaction_stamps_last_scanned_at_even_without_flags(db):
    """An innocuous memo should not raise a flag, but last_scanned_at
    must still be stamped."""
    before = datetime.now(timezone.utc)
    t = _mk_txn(db, "Bill:1", memo="Office supplies — routine")
    monitor = ComplianceMonitor(db)
    flags = monitor.scan_transaction(t)
    assert flags == []
    assert t.last_scanned_at is not None
    assert t.last_scanned_at >= before


def test_scan_transaction_stamps_last_scanned_at_when_flag_raised(db):
    """A memo that triggers a Subpart E rule should both raise a flag
    and stamp last_scanned_at."""
    t = _mk_txn(db, "Bill:1", memo="Wine for donor gala")
    monitor = ComplianceMonitor(db)
    flags = monitor.scan_transaction(t)
    assert len(flags) >= 1
    assert t.last_scanned_at is not None


def test_scan_all_unscanned_stamps_every_transaction(db):
    t1 = _mk_txn(db, "Bill:1", memo="Office supplies")
    t2 = _mk_txn(db, "Bill:2", memo="Printer paper")
    t3 = _mk_txn(db, "Bill:3", memo="Alcohol for board dinner")  # triggers rule
    monitor = ComplianceMonitor(db)
    monitor.scan_all_unscanned()
    db.flush()
    for t in (t1, t2, t3):
        db.refresh(t)
        assert t.last_scanned_at is not None


# ---------------------------------------------------------------------------
# transactions_above_threshold_total
# ---------------------------------------------------------------------------


def test_transactions_above_threshold_total_counts_correctly(db):
    _mk_txn(db, "Bill:1", amount_cents=500_000)
    _mk_txn(db, "Bill:2", amount_cents=250_000)  # exactly at
    _mk_txn(db, "Bill:3", amount_cents=249_999)  # just below
    _mk_txn(db, "Bill:4", amount_cents=1_000_000)
    assert transactions_above_threshold_total(db, threshold_cents=250_000) == 3


def test_transactions_above_threshold_total_empty_table(db):
    assert transactions_above_threshold_total(db, threshold_cents=250_000) == 0


# ---------------------------------------------------------------------------
# compute_allowable_costs
# ---------------------------------------------------------------------------


def test_compute_allowable_costs_returns_none_when_no_recent_scans(db):
    # Transaction exists but has never been scanned.
    _mk_txn(db, "Bill:1")
    assert compute_allowable_costs(db) is None


def test_compute_allowable_costs_all_clean_returns_100(db):
    now = datetime.now(timezone.utc)
    _mk_txn(db, "Bill:1", last_scanned_at=now)
    _mk_txn(db, "Bill:2", last_scanned_at=now)
    _mk_txn(db, "Bill:3", last_scanned_at=now)
    assert compute_allowable_costs(db) == 100


def test_compute_allowable_costs_one_flagged_of_four(db):
    now = datetime.now(timezone.utc)
    t1 = _mk_txn(db, "Bill:1", last_scanned_at=now)
    _mk_txn(db, "Bill:2", last_scanned_at=now)
    _mk_txn(db, "Bill:3", last_scanned_at=now)
    _mk_txn(db, "Bill:4", last_scanned_at=now)
    _mk_flag(db, t1, rule_id="UC.200.423", status=FlagStatus.open)
    # 1 flagged of 4 scanned → 75%
    assert compute_allowable_costs(db) == 75


def test_compute_allowable_costs_resolved_flags_do_not_count(db):
    now = datetime.now(timezone.utc)
    t1 = _mk_txn(db, "Bill:1", last_scanned_at=now)
    _mk_txn(db, "Bill:2", last_scanned_at=now)
    _mk_flag(db, t1, rule_id="UC.200.423", status=FlagStatus.resolved)
    _mk_flag(db, t1, rule_id="UC.200.421", status=FlagStatus.waived)
    assert compute_allowable_costs(db) == 100


def test_compute_allowable_costs_multiple_flags_on_one_txn_count_once(db):
    """Two Subpart E flags on the same txn should count as one flagged
    transaction, not two. Otherwise the ratio could exceed 1."""
    now = datetime.now(timezone.utc)
    t1 = _mk_txn(db, "Bill:1", last_scanned_at=now)
    _mk_txn(db, "Bill:2", last_scanned_at=now)
    _mk_flag(db, t1, rule_id="UC.200.423", status=FlagStatus.open)
    _mk_flag(db, t1, rule_id="UC.200.421", status=FlagStatus.open)
    # 1 flagged txn of 2 scanned → 50%
    assert compute_allowable_costs(db) == 50


def test_compute_allowable_costs_excludes_stale_scans(db):
    recent = datetime.now(timezone.utc)
    stale = datetime.now(timezone.utc) - timedelta(days=30)
    _mk_txn(db, "Bill:1", last_scanned_at=recent)
    _mk_txn(db, "Bill:2", last_scanned_at=stale)
    _mk_txn(db, "Bill:3", last_scanned_at=stale)
    # Only 1 recent scan, no flags → 100%
    assert compute_allowable_costs(db, scan_freshness_days=7) == 100


def test_compute_allowable_costs_ignores_non_subpart_e_flags(db):
    now = datetime.now(timezone.utc)
    t1 = _mk_txn(db, "Bill:1", last_scanned_at=now)
    _mk_txn(db, "Bill:2", last_scanned_at=now)
    # A non-Subpart-E rule (period of performance, say) should not affect
    # allowable_costs.
    _mk_flag(db, t1, rule_id="POP.200.309", status=FlagStatus.open)
    assert compute_allowable_costs(db) == 100


# ---------------------------------------------------------------------------
# compute_transaction_documentation
# ---------------------------------------------------------------------------


def test_compute_transaction_documentation_returns_none_when_empty(db):
    assert compute_transaction_documentation(db, threshold_cents=250_000) is None


def test_compute_transaction_documentation_returns_none_when_none_above_threshold(db):
    _mk_txn(db, "Bill:1", amount_cents=100_000)
    assert compute_transaction_documentation(db, threshold_cents=250_000) is None


def test_compute_transaction_documentation_all_documented(db):
    _mk_txn(db, "Bill:1", amount_cents=500_000, attachment_count=1)
    _mk_txn(db, "Bill:2", amount_cents=500_000, attachment_count=2)
    assert compute_transaction_documentation(db, threshold_cents=250_000) == 100


def test_compute_transaction_documentation_mixed(db):
    # 4 above threshold, 1 missing → 75%
    _mk_txn(db, "Bill:1", amount_cents=500_000, attachment_count=0)  # missing
    _mk_txn(db, "Bill:2", amount_cents=500_000, attachment_count=1)
    _mk_txn(db, "Bill:3", amount_cents=500_000, attachment_count=1)
    _mk_txn(db, "Bill:4", amount_cents=500_000, attachment_count=1)
    # below threshold — excluded from denominator and numerator
    _mk_txn(db, "Bill:5", amount_cents=100_000, attachment_count=0)
    assert compute_transaction_documentation(db, threshold_cents=250_000) == 75


# ---------------------------------------------------------------------------
# Placeholder compute functions
# ---------------------------------------------------------------------------


def test_placeholder_compute_functions_return_none(db):
    assert compute_time_effort(db) is None
    assert compute_procurement(db) is None
    assert compute_subrecipient_monitoring(db) is None
    assert compute_performance_reporting(db) is None


def test_compute_functions_dispatch_table_covers_every_dimension():
    """Every dimension in the canonical set has a dispatch entry."""
    assert set(COMPUTE_FUNCTIONS.keys()) == set(dimension_ids())


def test_computed_dimensions_is_exactly_the_two(db):
    assert COMPUTED_DIMENSIONS == frozenset(
        {"allowable_costs", "transaction_documentation"}
    )


# ---------------------------------------------------------------------------
# GET /compliance/dimensions endpoint
# ---------------------------------------------------------------------------


def test_dimensions_endpoint_returns_all_six_dimensions(db):
    result = list_dimensions(db=db)
    ids = [d["id"] for d in result["dimensions"]]
    assert ids == list(dimension_ids())


def test_dimensions_endpoint_marks_computed_vs_placeholder(db):
    result = list_dimensions(db=db)
    status_by_id = {d["id"]: d["status"] for d in result["dimensions"]}
    assert status_by_id["allowable_costs"] == "computed"
    assert status_by_id["transaction_documentation"] == "computed"
    assert status_by_id["time_effort"] == "placeholder"
    assert status_by_id["procurement"] == "placeholder"
    assert status_by_id["subrecipient_monitoring"] == "placeholder"
    assert status_by_id["performance_reporting"] == "placeholder"


def test_dimensions_endpoint_shape_and_metadata(db):
    result = list_dimensions(db=db)
    assert "dimensions" in result
    assert "computed_at" in result
    for d in result["dimensions"]:
        assert set(d.keys()) >= {
            "id", "title", "what_auditors_look_for", "cfr_citations",
            "compliance_supplement_area", "owner_role", "default_tone",
            "readiness_pct", "status",
        }
        assert isinstance(d["cfr_citations"], list)
        assert all(c.startswith("§") for c in d["cfr_citations"])


def test_dimensions_endpoint_readiness_pct_reflects_real_state(db):
    # Seed: 2 recently-scanned txns, one with a Subpart E flag.
    now = datetime.now(timezone.utc)
    t1 = _mk_txn(db, "Bill:1", amount_cents=500_000, last_scanned_at=now)
    _mk_txn(db, "Bill:2", amount_cents=500_000, last_scanned_at=now, attachment_count=1)
    _mk_flag(db, t1, rule_id="UC.200.423", status=FlagStatus.open)
    db.flush()

    result = list_dimensions(db=db)
    pcts = {d["id"]: d["readiness_pct"] for d in result["dimensions"]}
    # allowable_costs: 1 flagged of 2 scanned → 50
    assert pcts["allowable_costs"] == 50
    # transaction_documentation: 1 missing of 2 above threshold → 50
    assert pcts["transaction_documentation"] == 50
    # placeholders remain None
    assert pcts["time_effort"] is None
    assert pcts["procurement"] is None
    assert pcts["subrecipient_monitoring"] is None
    assert pcts["performance_reporting"] is None


def test_dimensions_endpoint_reads_from_canonical_source(db, monkeypatch):
    """Endpoint metadata must come from audit_dimensions.DIMENSIONS, not
    a duplicate. Patch the canonical source and verify the endpoint reflects
    the patched values."""
    from grant_compliance.api.routes import compliance as compliance_route
    from grant_compliance.compliance.audit_dimensions import (
        AuditDimension,
    )

    patched = tuple(
        AuditDimension(
            id=d.id,
            title=f"[PATCHED] {d.title}",
            what_auditors_look_for=d.what_auditors_look_for,
            cfr_citations=d.cfr_citations,
            compliance_supplement_area=d.compliance_supplement_area,
            owner_role=d.owner_role,
            default_tone=d.default_tone,
        )
        for d in DIMENSIONS
    )
    monkeypatch.setattr(compliance_route, "DIMENSIONS", patched)

    result = list_dimensions(db=db)
    titles = [d["title"] for d in result["dimensions"]]
    assert all(t.startswith("[PATCHED] ") for t in titles)
