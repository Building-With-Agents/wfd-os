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

from grant_compliance.compliance.audit_dimensions import DIMENSIONS
from grant_compliance.compliance.unallowable_costs import get_rule
from grant_compliance.db.models import (
    ComplianceFlag,
    FlagSeverity,
    FlagStatus,
    Transaction,
)
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


# ---------------------------------------------------------------------------
# Stat-card aggregates for the Audit Readiness tab
# ---------------------------------------------------------------------------
#
# The cockpit consumes these via the `stats` object on the
# GET /compliance/dimensions response. See audit_readiness_tab_spec.md
# §v1.2.5 for the T&E placeholder + dynamic "Across N of 6" subcopy
# contract.

# Sentinel constant for T&E Certifications stat while Employee↔Grant
# assignment data is absent from the engine. Cockpit pattern-matches
# on this exact string to render "Not yet tracked" in the UI.
# Replace with a real numeric/string ratio in v1.3+ once the data
# model lands.
TE_CERTS_PLACEHOLDER_STATUS: str = "placeholder_pending_employee_grant_data"


def compute_stats(db: Session) -> dict:
    """Compute the three Audit Readiness stat-card values.

    Returns a dict with:
      - `overall_readiness_pct`: equal-weighted integer average of the
        readiness percentages of dimensions that are both (a) marked
        `computed` AND (b) returned a non-null pct in this snapshot.
        Placeholder dimensions and computed-but-null dimensions are
        excluded from both the numerator and the denominator. Returns
        `None` if no dimensions qualify — this is distinct from 0% and
        means "no data yet" rather than "everything failing."
      - `overall_readiness_basis`: `{computed_dimension_count,
        total_dimension_count}`. `computed_dimension_count` is the N
        used in the cockpit's "Across N of 6 audit dimensions" subcopy
        — i.e. the count that actually contributed to the average
        (excludes computed-but-null). `total_dimension_count` is
        always 6 in v1.2 (one per entry in audit_dimensions.DIMENSIONS).
      - `doc_gap_count`: transactions at or above the de minimis
        threshold with no linked documentation. Straight pass-through
        from queries.transactions_without_documentation.
      - `doc_gap_threshold_cents`: the threshold used, so the cockpit
        can render the "Transactions over $X" label from the wire
        payload rather than duplicating the threshold literal.
      - `te_certs_status`: the placeholder constant
        `TE_CERTS_PLACEHOLDER_STATUS` in v1.2. Becomes a real ratio in
        v1.3+ once Employee↔Grant assignment data is present.

    Calls the existing per-dimension compute_* functions internally,
    so this function's output always agrees with the dimensions block
    of the /compliance/dimensions endpoint (shared compute path, no
    chance of drift).
    """
    contributing_pcts: list[int] = []
    for dim_id in COMPUTED_DIMENSIONS:
        pct = COMPUTE_FUNCTIONS[dim_id](db)
        if pct is not None:
            contributing_pcts.append(pct)

    if contributing_pcts:
        overall_pct: Optional[int] = _clamp_pct(
            sum(contributing_pcts) / len(contributing_pcts)
        )
    else:
        overall_pct = None

    return {
        "overall_readiness_pct": overall_pct,
        "overall_readiness_basis": {
            "computed_dimension_count": len(contributing_pcts),
            "total_dimension_count": len(DIMENSIONS),
        },
        "doc_gap_count": transactions_without_documentation(
            db, DEFAULT_DOCUMENTATION_THRESHOLD_CENTS
        ),
        "doc_gap_threshold_cents": DEFAULT_DOCUMENTATION_THRESHOLD_CENTS,
        "te_certs_status": TE_CERTS_PLACEHOLDER_STATUS,
    }


# ---------------------------------------------------------------------------
# Per-dimension gap lists for the Audit Readiness drill panels
# ---------------------------------------------------------------------------
#
# Each gap function returns a list of dicts matching the wire shape the
# cockpit renders in the drill panel (type/id/title/detail/metadata).
# Lazy-fetched by `GET /compliance/dimensions/{id}/gaps` per spec §v1.2.7.
#
# TODO(v1.3): add pagination when a tenant first produces hundreds of
# gaps. For now every function returns the full set. Spec §v1.2.7
# explicitly documents the deferral.

# Canonical placeholder copy per spec §v1.2.7. Exact text matters — the
# cockpit renders this verbatim; downstream UX review may lean on it.
# Any drift here should fail test_placeholder_messages_match_spec_text.
_PLACEHOLDER_MESSAGES: dict[str, str] = {
    "time_effort": (
        "Gap detection not yet available. When Employee↔Grant "
        "assignment data is added (v1.3+), this drill will show "
        "employees who lack required quarterly certifications for "
        "the current and prior closed periods."
    ),
    "procurement": (
        "Gap detection not yet available. When procurement record "
        "tracking is added (v1.3+), this drill will show contracts "
        "above threshold lacking documented competitive process or "
        "sole-source justification."
    ),
    "subrecipient_monitoring": (
        "Gap detection not yet available. When subrecipient risk "
        "assessment tracking is added (v1.3+), this drill will show "
        "subrecipients lacking current risk assessment, monitoring "
        "records, or audit follow-up."
    ),
    "performance_reporting": (
        "Gap detection not yet available. When WSAC reconciliation "
        "tracking is added (v1.3+), this drill will show reported "
        "placements not reconcilable to source data."
    ),
}


def placeholder_message_for(dimension_id: str) -> Optional[str]:
    """Return the honest placeholder message for a placeholder dimension,
    or None for a computed dimension."""
    return _PLACEHOLDER_MESSAGES.get(dimension_id)


# Severity ordering for gap sorting. Higher value = more urgent; used
# with reverse=True to surface blockers first.
_SEVERITY_ORDER: dict[FlagSeverity, int] = {
    FlagSeverity.blocker: 2,
    FlagSeverity.warning: 1,
    FlagSeverity.info: 0,
}


def _format_dollars(amount_dollars: float) -> str:
    """Format a dollar amount as '$X,XXX' for whole numbers or '$X,XXX.YY'
    otherwise. Used in gap titles/details so the wire payload carries
    pre-formatted human-readable strings (cockpit can still re-format
    from the metadata if it wants)."""
    if amount_dollars == int(amount_dollars):
        return f"${int(amount_dollars):,}"
    return f"${amount_dollars:,.2f}"


def _citation_section(rule_id: str) -> str:
    """Extract the §-prefixed section form from a rule_id like
    'UC.200.438' → '§200.438'. Falls back to the full rule_id if the
    expected shape isn't present (belt-and-braces for non-Subpart-E
    rules that might leak in)."""
    if "." in rule_id:
        # "UC.200.438" → "200.438"
        _, section = rule_id.split(".", 1)
        return f"§{section}"
    return rule_id


def gaps_for_allowable_costs(db: Session) -> list[dict]:
    """One gap entry per unresolved Subpart E ComplianceFlag.

    A transaction with two Subpart E flags produces two gap entries —
    each flag is an independent auditor-facing finding. (This differs
    from the allowable_costs readiness pct, which counts distinct
    flagged transactions to keep the ratio in [0, 1].)

    Sort: severity desc (blocker → warning → info), then raised_at desc.
    """
    stmt = select(ComplianceFlag).where(
        ComplianceFlag.rule_id.like("UC.%"),
        ComplianceFlag.status.in_(_UNRESOLVED_STATUSES),
    )
    flags = list(db.execute(stmt).scalars())

    flags.sort(
        key=lambda f: (_SEVERITY_ORDER.get(f.severity, -1), f.raised_at),
        reverse=True,
    )

    gaps: list[dict] = []
    for f in flags:
        rule = get_rule(f.rule_id)
        rule_short_title = rule.title if rule else ""
        citation = _citation_section(f.rule_id)
        title = (
            f"{citation} — {rule_short_title}"
            if rule_short_title
            else citation
        )

        metadata: dict = {
            "severity": f.severity.value,
            "raised_at": f.raised_at.isoformat(),
        }
        txn = f.transaction
        if txn is not None:
            metadata.update({
                "vendor_name": txn.vendor_name,
                "amount_dollars": round(txn.amount_cents / 100, 2),
                "txn_date": txn.txn_date.isoformat(),
                "qb_id": txn.qb_id,
            })

        gaps.append({
            "type": "compliance_flag",
            "id": f.id,
            "title": title,
            "detail": f.message,
            "metadata": metadata,
        })
    return gaps


def gaps_for_transaction_documentation(
    db: Session,
    threshold_cents: int = DEFAULT_DOCUMENTATION_THRESHOLD_CENTS,
) -> list[dict]:
    """One gap entry per transaction at or above `threshold_cents` with
    no linked documentation (attachment_count == 0). Sorted by amount desc.
    """
    stmt = (
        select(Transaction)
        .where(
            Transaction.amount_cents >= threshold_cents,
            Transaction.attachment_count == 0,
        )
        .order_by(Transaction.amount_cents.desc())
    )
    txns = list(db.execute(stmt).scalars())

    threshold_dollars = round(threshold_cents / 100, 2)
    threshold_str = _format_dollars(threshold_dollars)

    gaps: list[dict] = []
    for t in txns:
        amount_dollars = round(t.amount_cents / 100, 2)
        amount_str = _format_dollars(amount_dollars)
        vendor = t.vendor_name or "Unknown vendor"
        gaps.append({
            "type": "missing_documentation",
            "id": t.id,
            "title": f"{vendor} — {amount_str}",
            "detail": (
                f"No invoice or receipt attached. Threshold: {threshold_str}"
            ),
            "metadata": {
                "vendor_name": t.vendor_name,
                "amount_dollars": amount_dollars,
                "txn_date": t.txn_date.isoformat(),
                "qb_id": t.qb_id,
                "qb_type": t.qb_type,
                "threshold_dollars": threshold_dollars,
            },
        })
    return gaps


def gaps_for_time_effort(db: Session) -> list[dict]:
    """Placeholder. Empty list; the endpoint surfaces
    `_PLACEHOLDER_MESSAGES['time_effort']` separately so the UI can
    distinguish "no gaps" from "no formula."
    """
    return []


def gaps_for_procurement(db: Session) -> list[dict]:
    """Placeholder — see gaps_for_time_effort."""
    return []


def gaps_for_subrecipient_monitoring(db: Session) -> list[dict]:
    """Placeholder — see gaps_for_time_effort."""
    return []


def gaps_for_performance_reporting(db: Session) -> list[dict]:
    """Placeholder — see gaps_for_time_effort."""
    return []


GAP_FUNCTIONS = {
    "allowable_costs": gaps_for_allowable_costs,
    "transaction_documentation": gaps_for_transaction_documentation,
    "time_effort": gaps_for_time_effort,
    "procurement": gaps_for_procurement,
    "subrecipient_monitoring": gaps_for_subrecipient_monitoring,
    "performance_reporting": gaps_for_performance_reporting,
}
