"""Recent compliance activity — query + per-entry target summaries.

Reads from the immutable `audit_log` table and assembles a rich feed
entry per row. Where the action has a useful target, joins to the
relevant table (transactions, flags, allocations) to build a one-line
`target_summary` string. Presentation translation of action strings
(e.g. "compliance.flag.resolve" → "Resolved compliance flag on …")
does NOT happen here — that lives cockpit-side per spec §v1.2.9.

Consumed by GET /compliance/activity, which powers the cockpit's
"Recent Compliance Activity" panel.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.db.models import (
    Allocation,
    AuditLog,
    ComplianceFlag,
    Transaction,
)


# Known action vocabulary emitted by audit-log writers in the codebase.
# Listed here for reference / test anchoring only — the summary
# dispatch below is keyed directly on the action string, and unknown
# actions gracefully return target_summary=None (cockpit renders the
# raw action string).
KNOWN_ACTIONS: tuple[str, ...] = (
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
)


# Matches the trailing section of a CFR citation — "200.423", "200.430(i)",
# etc. Used to normalize both "2 CFR 200.423" (stored on ComplianceFlag)
# and "UC.200.423" (stored in flag-raised outputs) into "§200.423" form.
_SECTION_RE = re.compile(r"(\d+\.\d+(?:\([a-z0-9]+\))?)$")


def _short_citation(raw: Optional[str]) -> str:
    if not raw:
        return ""
    match = _SECTION_RE.search(raw)
    if match:
        return f"§{match.group(1)}"
    return raw


def _fmt_dollars_cents(amount_cents: Optional[int]) -> str:
    """Mirror of the engine's other dollar formatters (see
    dimension_readiness._format_dollars). Whole dollars render as
    '$X,XXX', fractional amounts as '$X,XXX.YY'. Empty string on None."""
    if amount_cents is None:
        return ""
    dollars = amount_cents / 100
    if dollars == int(dollars):
        return f"${int(dollars):,}"
    return f"${dollars:,.2f}"


def _txn_summary(txn: Optional[Transaction], citation: str = "") -> Optional[str]:
    if txn is None:
        return None
    parts: list[str] = []
    if txn.vendor_name:
        parts.append(txn.vendor_name)
    amt = _fmt_dollars_cents(txn.amount_cents)
    if amt:
        parts.append(amt)
    if citation:
        parts.append(f"— {citation}")
    text = " ".join(parts).strip()
    return text or None


def _build_target_summary(db: Session, entry: AuditLog) -> Optional[str]:
    """Dispatch on action string to produce a one-line summary, or None
    for actions without a dedicated builder (cockpit falls back to
    rendering the bare action name).
    """
    action = entry.action
    outputs = entry.outputs or {}

    # compliance.flag_raised — target_type="transaction", target_id=txn.id.
    # outputs carries rule_id + severity + message.
    if action == "compliance.flag_raised":
        citation = _short_citation(outputs.get("rule_id"))
        if entry.target_id:
            txn = db.get(Transaction, entry.target_id)
            summary = _txn_summary(txn, citation)
            if summary is not None:
                return summary
        return f"flag raised {citation}".strip() or None

    # compliance.flag.resolve / .waive / .acknowledge — target is the flag.
    if action.startswith("compliance.flag."):
        if entry.target_id:
            flag = db.get(ComplianceFlag, entry.target_id)
            if flag is not None:
                citation = _short_citation(flag.rule_citation)
                summary = _txn_summary(flag.transaction, citation)
                if summary is not None:
                    return summary
                return citation or None
        return None

    # compliance.explain_flag — target is the flag.
    if action == "compliance.explain_flag":
        if entry.target_id:
            flag = db.get(ComplianceFlag, entry.target_id)
            if flag is not None:
                citation = _short_citation(flag.rule_citation)
                return (f"explained {citation}".strip()) or None
        return None

    # Allocation actions — target is the allocation row.
    if action.startswith("allocation."):
        if entry.target_id:
            alloc = db.get(Allocation, entry.target_id)
            if alloc is not None:
                amt_str = _fmt_dollars_cents(alloc.amount_cents)
                grant_name = alloc.grant.name if alloc.grant else "—"
                return f"{amt_str} for {grant_name}".strip()
        return None

    # QB syncs — no target row; outputs carry counts.
    if action == "qb.sync.accounts":
        n = outputs.get("new_accounts")
        total = outputs.get("total_seen")
        if n is not None and total is not None:
            return f"{n} new accounts ({total} seen)"
        return "Accounts synced from QB"
    if action == "qb.sync.classes":
        n = outputs.get("new_classes")
        total = outputs.get("total_seen")
        if n is not None and total is not None:
            return f"{n} new classes ({total} seen)"
        return "Classes synced from QB"
    if action == "qb.sync.transactions":
        n = outputs.get("new_transactions", 0)
        return f"{n} new transactions synced from QB"
    if action == "qb.sync.attachables":
        processed = outputs.get("attachables_processed", 0)
        with_attachments = outputs.get("transactions_with_attachments", 0)
        return (
            f"{processed} attachments processed "
            f"({with_attachments} transactions)"
        )

    # OAuth authorization — target_id is the realm_id.
    if action == "qb.oauth.authorized":
        if entry.target_id:
            return f"Authorized QB realm {entry.target_id}"
        return None

    # Report lifecycle — target is report_draft; outputs has report_type.
    if action == "report.finalize":
        rtype = outputs.get("report_type", "report")
        return f"Finalized {rtype} report draft"

    # Time & effort — keep summaries simple.
    if action == "time_effort.certified":
        return "Time & effort certification signed"
    if action.startswith("time_effort.draft"):
        return "Time & effort certification drafted"

    # Classifier actions are intentionally per-transaction noisy and
    # don't carry a useful target row; let the cockpit render them as
    # raw action strings rather than manufacture a summary.
    return None


def list_recent_activity(
    db: Session, days: int = 7, limit: int = 50
) -> list[dict]:
    """Return up to `limit` audit_log rows from the last `days` days,
    newest first. Each entry is a dict matching the spec §v1.2.9 shape
    (actor, actor_kind, action, target_type, target_id, target_summary,
    occurred_at, metadata).

    Parameter bounds are enforced at the FastAPI layer via
    Query(ge=..., le=...). This helper assumes the caller supplied
    already-validated values; a programmatic caller passing out-of-bound
    values still gets a well-formed response (truncation is silent).

    Pagination beyond the limit is not supported in v1.2 — callers can
    narrow `days` to cover earlier windows if needed. Known limit;
    revisit in v1.3.
    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(AuditLog)
        .where(AuditLog.occurred_at >= cutoff)
        .order_by(AuditLog.occurred_at.desc())
        .limit(limit)
    )
    rows = list(db.execute(stmt).scalars())

    entries: list[dict] = []
    for e in rows:
        entries.append({
            "actor": e.actor,
            "actor_kind": e.actor_kind,
            "action": e.action,
            "target_type": e.target_type,
            "target_id": e.target_id,
            "target_summary": _build_target_summary(db, e),
            "occurred_at": e.occurred_at.isoformat(),
            "metadata": {
                "inputs": e.inputs or {},
                "outputs": e.outputs or {},
                "model": e.model,
                "note": e.note,
            },
        })
    return entries
