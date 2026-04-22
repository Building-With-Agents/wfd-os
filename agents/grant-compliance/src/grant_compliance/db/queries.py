"""Read-side DB query helpers.

Functions in this module return scalar values or result lists for the
agents, route handlers, and cockpit-facing APIs to consume. Keeping them
here (rather than inline in routes) makes them easy to test in isolation
and reusable across callers — e.g. the Audit Readiness tab and the
Documentation Gap stat both want the same "transactions missing docs"
count.

Everything here is read-only. Writes live in the service/agent modules.
"""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from grant_compliance.db.models import Transaction


def transactions_without_documentation(db: Session, threshold_cents: int) -> int:
    """Count transactions at or above `threshold_cents` with no linked documentation.

    "Documentation" here means a QB Attachable (invoice PDF, receipt scan,
    written approval) that references the transaction. Populated by
    quickbooks.sync.sync_attachables.

    Used by the Audit Readiness tab's Documentation Gap stat
    (`stats.doc_gap`). Typical invocation: `threshold_cents=250_000` for a
    $2,500 de minimis threshold.
    """
    stmt = (
        select(func.count())
        .select_from(Transaction)
        .where(
            Transaction.amount_cents >= threshold_cents,
            Transaction.attachment_count == 0,
        )
    )
    return db.execute(stmt).scalar_one()
