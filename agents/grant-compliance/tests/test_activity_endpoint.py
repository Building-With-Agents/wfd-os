"""Tests for the /compliance/activity endpoint and the underlying
list_recent_activity + target-summary logic.

Covers step 6 engine-side scope from audit_readiness_tab_spec.md §v1.2.9.
Parameter-bounds validation (HTTP 422 from FastAPI's Query(ge=..., le=...))
is framework behavior and is exercised via a TestClient check.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from grant_compliance.api.routes.compliance import list_activity, router
from grant_compliance.compliance.activity import (
    KNOWN_ACTIONS,
    _short_citation,
    list_recent_activity,
)
from grant_compliance.db.models import (
    Allocation,
    AllocationStatus,
    AuditLog,
    ComplianceFlag,
    FlagSeverity,
    FlagStatus,
    Funder,
    FunderType,
    Grant,
    Transaction,
)
from grant_compliance.db.session import get_db


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entries_payload(db, days: int = 7, limit: int = 50) -> dict:
    """Emulate what the HTTP endpoint returns — same shape, but
    constructed without FastAPI Query() resolution (which needs a real
    request to unwrap defaults). Used by direct-call tests throughout
    this file; HTTP-layer validation is exercised separately via
    TestClient below."""
    from datetime import datetime, timezone as _tz
    return {
        "entries": list_recent_activity(db, days=days, limit=limit),
        "computed_at": datetime.now(_tz.utc).isoformat(),
    }


def _audit(
    db,
    action: str,
    actor: str = "test@example.com",
    actor_kind: str = "human",
    occurred_at: datetime | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    outputs: dict | None = None,
    note: str | None = None,
):
    entry = AuditLog(
        actor=actor,
        actor_kind=actor_kind,
        action=action,
        target_type=target_type,
        target_id=target_id,
        outputs=outputs or {},
        note=note,
    )
    if occurred_at is not None:
        entry.occurred_at = occurred_at
    db.add(entry)
    db.flush()
    return entry


def _txn(db, qb_id="Bill:1", vendor="Vendor X", amount_cents=150_000):
    qb_type = qb_id.split(":", 1)[0]
    t = Transaction(
        qb_id=qb_id,
        qb_type=qb_type,
        txn_date=date(2025, 6, 1),
        vendor_name=vendor,
        amount_cents=amount_cents,
    )
    db.add(t)
    db.flush()
    return t


def _flag(db, txn, rule_id="UC.200.438", rule_citation="2 CFR 200.438"):
    f = ComplianceFlag(
        transaction_id=txn.id,
        rule_id=rule_id,
        rule_citation=rule_citation,
        message="Entertainment expense",
        severity=FlagSeverity.warning,
        status=FlagStatus.open,
    )
    db.add(f)
    db.flush()
    return f


def _grant_with_funder(db, name="Good Jobs Challenge"):
    funder = Funder(name="Federal Funder", funder_type=FunderType.federal)
    db.add(funder)
    db.flush()
    g = Grant(
        funder_id=funder.id,
        name=name,
        period_start=date(2025, 1, 1),
        period_end=date(2026, 12, 31),
        total_award_cents=10_000_000,
    )
    db.add(g)
    db.flush()
    return g


def _allocation(db, txn, grant, amount_cents=150_000):
    a = Allocation(
        transaction_id=txn.id,
        grant_id=grant.id,
        amount_cents=amount_cents,
        status=AllocationStatus.approved,
    )
    db.add(a)
    db.flush()
    return a


# ---------------------------------------------------------------------------
# Empty / minimal response shape
# ---------------------------------------------------------------------------


def test_empty_audit_log_returns_valid_response(db):
    result = _entries_payload(db)
    assert result["entries"] == []
    assert "computed_at" in result
    datetime.fromisoformat(result["computed_at"])


def test_response_includes_expected_fields(db):
    _audit(db, action="classifier.propose.llm", actor="qb_sync", actor_kind="agent")
    result = _entries_payload(db)
    assert len(result["entries"]) == 1
    entry = result["entries"][0]
    expected_keys = {
        "actor",
        "actor_kind",
        "action",
        "target_type",
        "target_id",
        "target_summary",
        "occurred_at",
        "metadata",
    }
    assert set(entry.keys()) == expected_keys
    assert set(entry["metadata"].keys()) == {"inputs", "outputs", "model", "note"}


# ---------------------------------------------------------------------------
# Time window + limit
# ---------------------------------------------------------------------------


def test_entries_outside_window_are_excluded(db):
    now = datetime.now(timezone.utc)
    _audit(db, action="qb.sync.accounts", occurred_at=now - timedelta(days=1))
    _audit(db, action="qb.sync.classes", occurred_at=now - timedelta(days=10))
    result = _entries_payload(db, days=7)
    actions = [e["action"] for e in result["entries"]]
    assert "qb.sync.accounts" in actions
    assert "qb.sync.classes" not in actions


def test_days_parameter_widens_window(db):
    now = datetime.now(timezone.utc)
    _audit(db, action="qb.sync.classes", occurred_at=now - timedelta(days=10))
    result = _entries_payload(db, days=14)
    actions = [e["action"] for e in result["entries"]]
    assert "qb.sync.classes" in actions


def test_limit_caps_result_count(db):
    for i in range(10):
        _audit(db, action=f"classifier.propose.llm", actor=f"a{i}")
    result = _entries_payload(db, limit=3)
    assert len(result["entries"]) == 3


def test_sort_order_is_newest_first(db):
    now = datetime.now(timezone.utc)
    _audit(db, action="a.old", occurred_at=now - timedelta(hours=3))
    _audit(db, action="a.newest", occurred_at=now)
    _audit(db, action="a.middle", occurred_at=now - timedelta(hours=1))
    actions = [e["action"] for e in _entries_payload(db)["entries"]]
    assert actions == ["a.newest", "a.middle", "a.old"]


# ---------------------------------------------------------------------------
# target_summary — per-action dispatch
# ---------------------------------------------------------------------------


def test_target_summary_for_flag_raised_uses_transaction_and_outputs(db):
    txn = _txn(db, vendor="Liquor Co", amount_cents=8_500)
    _audit(
        db,
        action="compliance.flag_raised",
        target_type="transaction",
        target_id=txn.id,
        outputs={"rule_id": "UC.200.423", "severity": "warning"},
    )
    result = _entries_payload(db)
    summary = result["entries"][0]["target_summary"]
    assert summary is not None
    assert "Liquor Co" in summary
    assert "$85" in summary
    assert "§200.423" in summary


def test_target_summary_for_flag_resolve_uses_flag_row(db):
    txn = _txn(db, vendor="Big Vendor", amount_cents=250_000)
    flag = _flag(db, txn, rule_id="UC.200.438", rule_citation="2 CFR 200.438")
    _audit(
        db,
        action="compliance.flag.resolve",
        target_type="compliance_flag",
        target_id=flag.id,
    )
    result = _entries_payload(db)
    summary = result["entries"][0]["target_summary"]
    assert summary is not None
    assert "Big Vendor" in summary
    assert "$2,500" in summary
    assert "§200.438" in summary


def test_target_summary_for_qb_sync_transactions_reads_outputs(db):
    _audit(
        db,
        action="qb.sync.transactions",
        actor="qb_sync",
        actor_kind="agent",
        outputs={"new_transactions": 42},
    )
    result = _entries_payload(db)
    assert result["entries"][0]["target_summary"] == "42 new transactions synced from QB"


def test_target_summary_for_qb_sync_accounts_mentions_new_and_total(db):
    _audit(
        db,
        action="qb.sync.accounts",
        actor="qb_sync",
        actor_kind="agent",
        outputs={"new_accounts": 3, "total_seen": 27},
    )
    result = _entries_payload(db)
    assert "3 new accounts" in result["entries"][0]["target_summary"]
    assert "27 seen" in result["entries"][0]["target_summary"]


def test_target_summary_for_qb_sync_attachables(db):
    _audit(
        db,
        action="qb.sync.attachables",
        actor="qb_sync",
        actor_kind="agent",
        outputs={"attachables_processed": 12, "transactions_with_attachments": 8},
    )
    result = _entries_payload(db)
    summary = result["entries"][0]["target_summary"]
    assert "12 attachments processed" in summary
    assert "8 transactions" in summary


def test_target_summary_for_allocation_uses_grant_name(db):
    grant = _grant_with_funder(db, name="K8341 GJC")
    txn = _txn(db, vendor="Contractor", amount_cents=500_000)
    alloc = _allocation(db, txn, grant, amount_cents=500_000)
    _audit(
        db,
        action="allocation.approve",
        target_type="allocation",
        target_id=alloc.id,
    )
    result = _entries_payload(db)
    summary = result["entries"][0]["target_summary"]
    assert "$5,000" in summary
    assert "K8341 GJC" in summary


def test_target_summary_for_report_finalize_uses_report_type(db):
    _audit(
        db,
        action="report.finalize",
        outputs={"report_type": "SF-425"},
    )
    result = _entries_payload(db)
    assert result["entries"][0]["target_summary"] == "Finalized SF-425 report draft"


def test_target_summary_for_oauth_mentions_realm(db):
    _audit(
        db,
        action="qb.oauth.authorized",
        target_type="qb_realm",
        target_id="realm-1234",
    )
    result = _entries_payload(db)
    assert "realm-1234" in result["entries"][0]["target_summary"]


def test_unknown_action_returns_null_target_summary(db):
    _audit(db, action="future.unknown_action_type_v99")
    result = _entries_payload(db)
    assert result["entries"][0]["target_summary"] is None


def test_classifier_actions_return_null_target_summary(db):
    """Classifier signals are per-transaction noisy; cockpit renders
    them as the bare action string."""
    _audit(db, action="classifier.propose.llm")
    _audit(db, action="classifier.low_confidence")
    _audit(db, action="classifier.no_active_grants")
    result = _entries_payload(db)
    for entry in result["entries"]:
        assert entry["target_summary"] is None


# ---------------------------------------------------------------------------
# Helpers — _short_citation + KNOWN_ACTIONS vocabulary
# ---------------------------------------------------------------------------


def test_short_citation_normalizes_both_formats():
    assert _short_citation("UC.200.423") == "§200.423"
    assert _short_citation("2 CFR 200.438") == "§200.438"
    assert _short_citation("§200.430(i)") == "§200.430(i)"
    assert _short_citation(None) == ""
    assert _short_citation("") == ""


def test_known_actions_vocabulary_covers_all_codebase_emitters():
    """Anchor the list of actions currently emitted by the codebase.
    If someone adds a new action string without updating KNOWN_ACTIONS,
    this test should be refreshed and target_summary dispatch reviewed."""
    # All 17 literal strings + 5 f-string expansions from the grep at
    # commit time.
    expected = {
        "allocation.approve",
        "allocation.propose.manual",
        "allocation.reject",
        "classifier.low_confidence",
        "classifier.no_active_grants",
        "classifier.parse_failed",
        "classifier.propose.deterministic",
        "classifier.propose.llm",
        "compliance.explain_flag",
        "compliance.flag.acknowledge",
        "compliance.flag.resolve",
        "compliance.flag.waive",
        "compliance.flag_raised",
        "qb.oauth.authorized",
        "qb.sync.accounts",
        "qb.sync.attachables",
        "qb.sync.classes",
        "qb.sync.transactions",
        "report.finalize",
        "time_effort.certified",
        "time_effort.draft.deterministic",
        "time_effort.draft.llm",
    }
    assert set(KNOWN_ACTIONS) == expected


# ---------------------------------------------------------------------------
# FastAPI Query() bounds — exercised via TestClient
# ---------------------------------------------------------------------------


def _make_test_client(db):
    """Build a minimal FastAPI app mounting just the compliance router
    with the test session overriding the real get_db dependency."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def test_query_validation_rejects_negative_days(db):
    client = _make_test_client(db)
    response = client.get("/compliance/activity", params={"days": -1})
    assert response.status_code == 422


def test_query_validation_rejects_zero_days(db):
    client = _make_test_client(db)
    response = client.get("/compliance/activity", params={"days": 0})
    assert response.status_code == 422


def test_query_validation_rejects_over_cap_days(db):
    client = _make_test_client(db)
    response = client.get("/compliance/activity", params={"days": 365})
    assert response.status_code == 422


def test_query_validation_rejects_over_cap_limit(db):
    client = _make_test_client(db)
    response = client.get("/compliance/activity", params={"limit": 9999})
    assert response.status_code == 422


# Note: a positive-path HTTP test (200 on valid defaults) isn't run
# here because the TestClient opens a fresh DB connection per request,
# and the conftest's `ATTACH DATABASE ':memory:' AS grant_compliance`
# trigger produces an empty schema on each new connection — the
# fixture's tables only exist on the session's original connection.
# The happy-path shape is already pinned by the direct-call tests
# above; what's specific to the HTTP layer here is the 422 rejection
# behavior, which doesn't touch the DB at all.
