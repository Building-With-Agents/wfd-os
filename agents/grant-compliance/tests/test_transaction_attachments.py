"""Tests for the Transaction.attachment_count column + sync_attachables +
transactions_without_documentation.

Implements the acceptance tests called out in step 1.5 of
agents/grant-compliance/docs/audit_readiness_tab_spec.md.
"""

from __future__ import annotations

import importlib.util
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock

from grant_compliance.db.models import Transaction
from grant_compliance.db.queries import transactions_without_documentation
from grant_compliance.quickbooks.client import QbClient, WRITE_METHOD_NAME_PREFIXES
from grant_compliance.quickbooks.sync import sync_attachables


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mk_txn(db, qb_id: str, amount_cents: int, attachment_count: int | None = None):
    qb_type, _ = qb_id.split(":", 1)
    t = Transaction(
        qb_id=qb_id,
        qb_type=qb_type,
        txn_date=date(2025, 6, 1),
        amount_cents=amount_cents,
    )
    if attachment_count is not None:
        t.attachment_count = attachment_count
    db.add(t)
    db.flush()
    return t


def _fake_client(attachables: list[dict]) -> MagicMock:
    client = MagicMock(spec=QbClient)
    client.list_attachables.return_value = attachables
    return client


# ---------------------------------------------------------------------------
# Column default
# ---------------------------------------------------------------------------


def test_attachment_count_defaults_to_zero(db):
    """New Transaction rows default to attachment_count = 0, not NULL."""
    t = _mk_txn(db, "Bill:1", 500_000)
    db.flush()
    db.refresh(t)
    assert t.attachment_count == 0


def test_attachment_count_is_not_nullable(db):
    """The column is NOT NULL; SQLAlchemy's default fills it even without an explicit value."""
    t = Transaction(
        qb_id="Bill:99",
        qb_type="Bill",
        txn_date=date(2025, 6, 1),
        amount_cents=100,
    )
    db.add(t)
    db.flush()
    db.refresh(t)
    assert t.attachment_count == 0


# ---------------------------------------------------------------------------
# sync_attachables
# ---------------------------------------------------------------------------


def test_sync_attachables_sets_counts_per_transaction(db):
    """Parse AttachableRef and update attachment_count on matching transactions."""
    _mk_txn(db, "Bill:100", 300_000)
    _mk_txn(db, "Purchase:200", 100_000)
    _mk_txn(db, "JournalEntry:300", 500_000)

    attachables = [
        {
            "Id": "1",
            "FileName": "invoice-a.pdf",
            "AttachableRef": [{"EntityRef": {"type": "Bill", "value": "100"}}],
        },
        {
            "Id": "2",
            "FileName": "invoice-b.pdf",
            "AttachableRef": [
                {"EntityRef": {"type": "Bill", "value": "100"}},
                {"EntityRef": {"type": "Purchase", "value": "200"}},
            ],
        },
    ]
    client = _fake_client(attachables)
    processed = sync_attachables(db, client)
    db.expire_all()

    assert processed == 2
    bill = db.query(Transaction).filter(Transaction.qb_id == "Bill:100").one()
    purchase = db.query(Transaction).filter(Transaction.qb_id == "Purchase:200").one()
    je = db.query(Transaction).filter(Transaction.qb_id == "JournalEntry:300").one()
    assert bill.attachment_count == 2
    assert purchase.attachment_count == 1
    assert je.attachment_count == 0


def test_sync_attachables_ignores_non_transaction_entity_types(db):
    """Attachables referencing Customer/Vendor/Invoice are skipped — only
    Bill / Purchase / JournalEntry count as transaction documentation."""
    _mk_txn(db, "Bill:1", 500_000)

    attachables = [
        {
            "Id": "x",
            "AttachableRef": [
                {"EntityRef": {"type": "Customer", "value": "500"}},
                {"EntityRef": {"type": "Vendor", "value": "600"}},
                {"EntityRef": {"type": "Invoice", "value": "700"}},
            ],
        },
    ]
    client = _fake_client(attachables)
    sync_attachables(db, client)
    db.expire_all()

    bill = db.query(Transaction).filter(Transaction.qb_id == "Bill:1").one()
    assert bill.attachment_count == 0


def test_sync_attachables_is_idempotent(db):
    """Running sync twice with the same attachables produces the same count."""
    _mk_txn(db, "Bill:1", 500_000)
    attachables = [
        {"Id": "1", "AttachableRef": [{"EntityRef": {"type": "Bill", "value": "1"}}]},
    ]
    client = _fake_client(attachables)

    sync_attachables(db, client)
    sync_attachables(db, client)
    db.expire_all()

    bill = db.query(Transaction).filter(Transaction.qb_id == "Bill:1").one()
    assert bill.attachment_count == 1


def test_sync_attachables_zeroes_when_attachment_removed(db):
    """If an attachment is deleted in QB, the next sync decrements the count."""
    _mk_txn(db, "Bill:1", 500_000)
    client = _fake_client(
        [{"Id": "1", "AttachableRef": [{"EntityRef": {"type": "Bill", "value": "1"}}]}]
    )

    sync_attachables(db, client)
    db.expire_all()
    bill = db.query(Transaction).filter(Transaction.qb_id == "Bill:1").one()
    assert bill.attachment_count == 1

    # Attachment removed in QB between sync runs.
    client.list_attachables.return_value = []
    sync_attachables(db, client)
    db.expire_all()
    bill = db.query(Transaction).filter(Transaction.qb_id == "Bill:1").one()
    assert bill.attachment_count == 0


def test_sync_attachables_tolerates_missing_attachableref(db):
    """Attachables with no AttachableRef (or empty array) are processed without error."""
    _mk_txn(db, "Bill:1", 500_000)
    client = _fake_client(
        [
            {"Id": "x", "AttachableRef": None},
            {"Id": "y"},
            {"Id": "z", "AttachableRef": []},
        ]
    )
    processed = sync_attachables(db, client)
    assert processed == 3


def test_sync_attachables_returns_count_not_transactions_updated(db):
    """Return value is the count of Attachables, not the count of transactions touched."""
    _mk_txn(db, "Bill:1", 500_000)
    client = _fake_client(
        [
            {"Id": "1", "AttachableRef": [{"EntityRef": {"type": "Bill", "value": "1"}}]},
            {"Id": "2", "AttachableRef": [{"EntityRef": {"type": "Bill", "value": "999"}}]},
        ]
    )
    # One transaction in our mirror + two attachables. Return value is 2.
    assert sync_attachables(db, client) == 2


# ---------------------------------------------------------------------------
# transactions_without_documentation
# ---------------------------------------------------------------------------


def test_transactions_without_documentation_counts_correctly(db):
    """Mixed-data case: count only rows at-or-above threshold with zero attachments."""
    # above threshold, no attachments → counted
    _mk_txn(db, "Bill:1", 500_000, attachment_count=0)
    # above threshold, with attachments → not counted
    _mk_txn(db, "Bill:2", 500_000, attachment_count=2)
    # below threshold, no attachments → not counted
    _mk_txn(db, "Bill:3", 100_000, attachment_count=0)
    # exactly at threshold, no attachments → counted (>=)
    _mk_txn(db, "Bill:4", 250_000, attachment_count=0)
    # just under threshold, no attachments → not counted
    _mk_txn(db, "Bill:5", 249_999, attachment_count=0)

    assert transactions_without_documentation(db, threshold_cents=250_000) == 2


def test_transactions_without_documentation_empty_table(db):
    assert transactions_without_documentation(db, threshold_cents=250_000) == 0


def test_transactions_without_documentation_all_documented(db):
    _mk_txn(db, "Bill:1", 500_000, attachment_count=1)
    _mk_txn(db, "Bill:2", 600_000, attachment_count=3)
    assert transactions_without_documentation(db, threshold_cents=250_000) == 0


# ---------------------------------------------------------------------------
# Read-only enforcement regression
# ---------------------------------------------------------------------------


def test_list_attachables_name_does_not_trigger_write_prefix_guard():
    """The new QbClient method name must not trip the write-prefix guard."""
    for prefix in WRITE_METHOD_NAME_PREFIXES:
        assert not "list_attachables".startswith(prefix), (
            f"'list_attachables' starts with forbidden prefix {prefix!r}"
        )
    # Also verify the method is actually exposed on QbClient.
    assert hasattr(QbClient, "list_attachables")


# ---------------------------------------------------------------------------
# Alembic migration file structure
# ---------------------------------------------------------------------------
#
# We don't spin up a real Postgres to exercise `alembic upgrade/downgrade`
# here — the SQLite conftest creates the schema from metadata, not from
# migrations. This test verifies the migration file is well-formed: right
# revision chain, both upgrade() and downgrade() defined, correct schema
# and table, correct column name. Running the migration against a live
# Postgres is an operational step.


def test_migration_file_is_well_formed():
    versions_dir = Path(__file__).resolve().parent.parent / "alembic" / "versions"
    matches = list(versions_dir.glob("*_add_attachment_count_to_transactions.py"))
    assert len(matches) == 1, f"expected exactly one matching migration, found: {matches}"
    path = matches[0]

    spec = importlib.util.spec_from_file_location("migration_under_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "7c1fa8b3d2e4"
    assert module.down_revision == "52e509f9e39a"
    assert callable(module.upgrade)
    assert callable(module.downgrade)

    src = path.read_text(encoding="utf-8")
    assert "op.add_column" in src
    assert "op.drop_column" in src
    assert "attachment_count" in src
    assert "'transactions'" in src
    assert "schema='grant_compliance'" in src
    assert "server_default='0'" in src
    assert "nullable=False" in src
