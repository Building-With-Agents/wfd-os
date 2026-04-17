"""QuickBooks → local DB sync.

Read-only sync. Idempotent: re-running with the same QB data produces no
changes. Uses qb_id as the upsert key.

In dev mode (LLM_PROVIDER=mock or no QB credentials), call `seed_from_fixture`
instead — it loads from a JSON file in `scripts/fixtures/`.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Any

from sqlalchemy.orm import Session

from grant_compliance.audit.log import write_entry
from grant_compliance.db.models import QbAccount, QbClass, Transaction
from grant_compliance.quickbooks.client import QbClient


def sync_accounts(db: Session, client: QbClient) -> int:
    """Pull active accounts from QB and upsert into qb_accounts. Returns count."""
    accounts = client.list_accounts()
    count = 0
    for raw in accounts:
        existing = db.query(QbAccount).filter(QbAccount.qb_id == raw["Id"]).first()
        if existing:
            existing.name = raw["Name"]
            existing.account_type = raw["AccountType"]
            existing.account_subtype = raw.get("AccountSubType")
            existing.active = raw.get("Active", True)
        else:
            db.add(
                QbAccount(
                    qb_id=raw["Id"],
                    name=raw["Name"],
                    account_type=raw["AccountType"],
                    account_subtype=raw.get("AccountSubType"),
                    active=raw.get("Active", True),
                )
            )
            count += 1
    write_entry(
        db,
        actor="qb_sync",
        actor_kind="agent",
        action="qb.sync.accounts",
        outputs={"new_accounts": count, "total_seen": len(accounts)},
    )
    return count


def sync_classes(db: Session, client: QbClient) -> int:
    classes = client.list_classes()
    count = 0
    for raw in classes:
        existing = db.query(QbClass).filter(QbClass.qb_id == raw["Id"]).first()
        if existing:
            existing.name = raw["FullyQualifiedName"]
            existing.active = raw.get("Active", True)
        else:
            db.add(
                QbClass(
                    qb_id=raw["Id"],
                    name=raw["FullyQualifiedName"],
                    active=raw.get("Active", True),
                )
            )
            count += 1
    write_entry(
        db,
        actor="qb_sync",
        actor_kind="agent",
        action="qb.sync.classes",
        outputs={"new_classes": count, "total_seen": len(classes)},
    )
    return count


def sync_transactions(db: Session, client: QbClient, since: date) -> int:
    """Pull bills, purchases, and journal entries since `since`. Returns
    the count of newly-inserted transactions.
    """
    iso = since.isoformat()
    new = 0
    for qb_type, fetcher in (
        ("Bill", client.list_bills_since),
        ("Purchase", client.list_purchases_since),
        ("JournalEntry", client.list_journal_entries_since),
    ):
        for raw in fetcher(iso):
            new += _upsert_transaction(db, qb_type, raw)
    write_entry(
        db,
        actor="qb_sync",
        actor_kind="agent",
        action="qb.sync.transactions",
        inputs={"since": iso},
        outputs={"new_transactions": new},
    )
    return new


def _upsert_transaction(db: Session, qb_type: str, raw: dict[str, Any]) -> int:
    qb_id = f"{qb_type}:{raw['Id']}"
    existing = db.query(Transaction).filter(Transaction.qb_id == qb_id).first()
    if existing:
        return 0  # treat as immutable in our mirror

    txn_date = datetime.strptime(raw["TxnDate"], "%Y-%m-%d").date()
    amount_dollars = float(raw.get("TotalAmt", 0))
    amount_cents = int(round(amount_dollars * 100))

    vendor = (raw.get("VendorRef") or {}).get("name") or (raw.get("EntityRef") or {}).get("name")
    memo = raw.get("PrivateNote") or raw.get("Memo")

    qb_class_name = None
    # Bills/Purchases tag class on each line; pick the first if uniform
    lines = raw.get("Line", [])
    classes_on_lines = {
        (line.get("AccountBasedExpenseLineDetail", {}) or {})
        .get("ClassRef", {})
        .get("name")
        for line in lines
    }
    classes_on_lines.discard(None)
    if len(classes_on_lines) == 1:
        qb_class_name = next(iter(classes_on_lines))

    qb_class_id = None
    if qb_class_name:
        cls = db.query(QbClass).filter(QbClass.name == qb_class_name).first()
        if cls:
            qb_class_id = cls.id

    db.add(
        Transaction(
            qb_id=qb_id,
            qb_type=qb_type,
            txn_date=txn_date,
            vendor_name=vendor,
            memo=memo,
            amount_cents=amount_cents,
            qb_class_id=qb_class_id,
            raw=raw,
        )
    )
    return 1


# ---------------------------------------------------------------------------
# Dev mode — load from fixture
# ---------------------------------------------------------------------------


def seed_from_fixture(db: Session, fixture_path: Path) -> dict[str, int]:
    """Load accounts, classes, and transactions from a JSON fixture for dev/test."""
    import json

    data = json.loads(fixture_path.read_text())
    counts = {"accounts": 0, "classes": 0, "transactions": 0}

    for raw in data.get("accounts", []):
        if not db.query(QbAccount).filter(QbAccount.qb_id == raw["Id"]).first():
            db.add(
                QbAccount(
                    qb_id=raw["Id"],
                    name=raw["Name"],
                    account_type=raw["AccountType"],
                    account_subtype=raw.get("AccountSubType"),
                )
            )
            counts["accounts"] += 1

    for raw in data.get("classes", []):
        if not db.query(QbClass).filter(QbClass.qb_id == raw["Id"]).first():
            db.add(
                QbClass(qb_id=raw["Id"], name=raw["FullyQualifiedName"])
            )
            counts["classes"] += 1
    db.flush()  # so qb_class_name lookup works below

    for raw in data.get("transactions", []):
        counts["transactions"] += _upsert_transaction(db, raw["_qb_type"], raw)

    return counts
