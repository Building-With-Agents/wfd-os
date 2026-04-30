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


# QB transaction types we mirror in the Transaction table. Attachables
# referencing other entity types (Customer, Vendor, Invoice, etc.) are
# ignored for the purposes of documentation linkage since those aren't
# transactions in our domain sense.
_MIRRORED_QB_TYPES: frozenset[str] = frozenset({"Bill", "Purchase", "JournalEntry"})


def sync_attachables(db: Session, client: QbClient) -> int:
    """Pull all QB Attachables and set Transaction.attachment_count from them.

    Each Attachable is a file uploaded to QB (invoice PDF, receipt scan, etc.)
    with an AttachableRef[] pointing at the entities it's attached to. We
    count references per transaction qb_id and update attachment_count.

    Idempotency: every run resets attachment_count to 0 for the whole
    transactions mirror before applying the freshly-counted values. This
    means (a) running the sync twice produces the same result, and (b) an
    attachment deleted in QB correctly decrements the count in our mirror
    on the next sync.

    Read-only: only issues a QB SELECT query. No writes to QB.

    Returns the number of Attachable entities processed (not the number of
    transactions updated, since one attachable can reference zero or many).
    """
    attachables = client.list_attachables()

    counts: dict[str, int] = {}
    for att in attachables:
        for ref in att.get("AttachableRef") or []:
            entity = ref.get("EntityRef") or {}
            etype = entity.get("type")
            evalue = entity.get("value")
            if not etype or not evalue:
                continue
            if etype not in _MIRRORED_QB_TYPES:
                continue
            qb_id = f"{etype}:{evalue}"
            counts[qb_id] = counts.get(qb_id, 0) + 1

    # Reset all mirrored transactions to 0, then apply fresh counts. The
    # reset is what makes a deletion in QB observable in our mirror.
    db.query(Transaction).update(
        {Transaction.attachment_count: 0}, synchronize_session=False
    )
    for qb_id, count in counts.items():
        db.query(Transaction).filter(Transaction.qb_id == qb_id).update(
            {Transaction.attachment_count: count}, synchronize_session=False
        )

    write_entry(
        db,
        actor="qb_sync",
        actor_kind="agent",
        action="qb.sync.attachables",
        outputs={
            "attachables_processed": len(attachables),
            "transactions_with_attachments": len(counts),
        },
    )
    return len(attachables)


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
