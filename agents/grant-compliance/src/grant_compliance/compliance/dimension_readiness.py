"""Compute per-dimension readiness percentages for the Audit Readiness tab.

Each of the six audit dimensions (see `audit_dimensions.DIMENSIONS`) has a
compute function here. Two are real computations against engine data;
four are placeholders that return `None` because the underlying data
models do not yet exist in the compliance engine. See v1.2 of
`docs/audit_readiness_tab_spec.md` for the deferral rationale.

Functions return integer percentages in [0, 100], or `None` when a
denominator is zero (computed dimensions) or the dimension is a
placeholder awaiting a data model (placeholder dimensions).

A dimension's `status` — "computed" vs "placeholder" — is independent of
whether the current call returns `None`. A computed dimension with no
recent scans will also return `None`, but it remains `computed` in
status. The set of computed dimensions is declared once as
`COMPUTED_DIMENSIONS` below.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from grant_compliance.db.models import ComplianceFlag, FlagStatus, Transaction
from grant_compliance.db.queries import (
    transactions_above_threshold_total,
    transactions_without_documentation,
)


# Default de minimis threshold for transaction documentation (in cents).
DEFAULT_DOCUMENTATION_THRESHOLD_CENTS: int = 250_000

# Default freshness window: transactions scanned within this many days
# count toward the allowable_costs denominator.
DEFAULT_SCAN_FRESHNESS_DAYS: int = 7

# Dimensions that have real compute functions in this module. Everything
# else is a placeholder until its data model lands.
COMPUTED_DIMENSIONS: frozenset[str] = frozenset(
    {"allowable_costs", "transaction_documentation"}
)

# FlagStatus values that mean "this flag is still an open concern" —
# both `open` and `acknowledged` are unresolved for the purposes of
# allowable_costs readiness.
_UNRESOLVED_STATUSES = (FlagStatus.open, FlagStatus.acknowledged)


def _clamp_pct(value: float) -> int:
    """Clamp to [0, 100] and round to int. Guards against edge cases where
    flag counts could momentarily exceed scanned-transaction counts (e.g.
    stale scans + fresh flags) and the computation dips below zero."""
    return max(0, min(100, round(value)))


# ---------------------------------------------------------------------------
# Computed dimensions
# ---------------------------------------------------------------------------


def compute_allowable_costs(
    db: Session,
    scan_freshness_days: int = DEFAULT_SCAN_FRESHNESS_DAYS,
) -> Optional[int]:
    """Readiness = 100 × (1 − unresolved Subpart E flags / recently-scanned txns).

    "Unresolved Subpart E flags" = distinct transactions that have at least
    one ComplianceFlag with rule_id starting `UC.` (the Subpart E prefix
    used by `unallowable_costs.py`) and status in (open, acknowledged).
    Counting distinct transactions rather than raw flag count keeps the
    ratio in [0, 1] — a transaction with two Subpart E flags still
    counts once against the denominator.

    "Recently scanned" = Transaction.last_scanned_at within the last
    `scan_freshness_days` days. Transactions scanned longer ago are
    excluded because their flag state may be stale. Returns `None` if
    no transactions have been scanned within the window.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=scan_freshness_days)

    scanned_count = db.execute(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.last_scanned_at >= cutoff)
    ).scalar_one()

    if scanned_count == 0:
        return None

    flagged_txn_count = db.execute(
        select(func.count(func.distinct(ComplianceFlag.transaction_id)))
        .where(
            ComplianceFlag.transaction_id.is_not(None),
            ComplianceFlag.rule_id.like("UC.%"),
            ComplianceFlag.status.in_(_UNRESOLVED_STATUSES),
        )
    ).scalar_one()

    return _clamp_pct(100.0 * (1 - flagged_txn_count / scanned_count))


def compute_transaction_documentation(
    db: Session,
    threshold_cents: int = DEFAULT_DOCUMENTATION_THRESHOLD_CENTS,
) -> Optional[int]:
    """Readiness = 100 × (1 − missing-doc txns / txns-above-threshold).

    Uses the two helpers in `db.queries`:
      - transactions_without_documentation  (numerator)
      - transactions_above_threshold_total  (denominator)

    Returns `None` when no transactions exist at or above the threshold
    (denominator is zero, so the ratio is undefined).
    """
    total = transactions_above_threshold_total(db, threshold_cents)
    if total == 0:
        return None
    missing = transactions_without_documentation(db, threshold_cents)
    return _clamp_pct(100.0 * (1 - missing / total))


# ---------------------------------------------------------------------------
# Placeholder dimensions
# ---------------------------------------------------------------------------
#
# Each returns None because the required data model is not yet in the
# compliance engine. See v1.2 spec for the deferral table.


def compute_time_effort(db: Session) -> Optional[int]:
    """Placeholder. Requires Employee↔Grant assignment data (which
    employees are federally-funded, as of when) not present in the
    current model. Deferred to v1.3+."""
    return None


def compute_procurement(db: Session) -> Optional[int]:
    """Placeholder. Requires a procurement records data model
    (contracts, competitive-process evidence, sole-source
    justifications) not present in the current engine. Deferred to v1.3+."""
    return None


def compute_subrecipient_monitoring(db: Session) -> Optional[int]:
    """Placeholder. Requires a subrecipient risk assessment data model
    (risk tier, monitoring schedule, follow-up evidence) not present in
    the current engine. Deferred to v1.3+."""
    return None


def compute_performance_reporting(db: Session) -> Optional[int]:
    """Placeholder. Requires WSAC reconciliation data (reported
    placements cross-referenced with underlying source data) not
    present in the current engine. Deferred to v1.3+."""
    return None


# ---------------------------------------------------------------------------
# Dispatch table consumed by the /compliance/dimensions endpoint.
# ---------------------------------------------------------------------------

COMPUTE_FUNCTIONS = {
    "allowable_costs": compute_allowable_costs,
    "transaction_documentation": compute_transaction_documentation,
    "time_effort": compute_time_effort,
    "procurement": compute_procurement,
    "subrecipient_monitoring": compute_subrecipient_monitoring,
    "performance_reporting": compute_performance_reporting,
}
