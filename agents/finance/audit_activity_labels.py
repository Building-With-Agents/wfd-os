"""Label translation for the Recent Compliance Activity feed.

The engine's `/compliance/activity` endpoint returns raw audit_log
entries with a pre-built `target_summary` per entry (see engine
commit e87f3b7). This module translates each entry into the display
shape the cockpit's React `ActivityFeed` component renders:

    {
        "timestamp_label":  "10:42 AM",
        "actor_label":      "Krista",
        "action_text":      "Resolved flag: Vendor X $1,500 — §200.438",
        "metadata_text":    None,
        "occurred_at":      "2026-04-23T...",
    }

Keeps all label construction in Python (testable in isolation) rather
than splitting it between Python and React.

Action vocabulary (22 types) mirrors engine commit e87f3b7's
KNOWN_ACTIONS tuple. See spec §v1.2.9 for the consumer contract.

TODO(v1.2 cockpit-side step 6 follow-up): add pytest on this branch
and cover each action template, unknown-action fallback, actor
display, timestamp formatting bands, and the classifier-silence
filter. Tests deferred per scope; see integration_notes.md on
feature/compliance-engine-extract.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Optional


# ---------------------------------------------------------------------------
# Actor display names
# ---------------------------------------------------------------------------
#
# v1.2 snapshot — the known actors emitted by audit_log writers in the
# engine. Extend as new actors appear. Unknown actors fall back to the
# email local-part (before '@') or the raw string when not email-shaped.

_ACTOR_DISPLAY_NAMES: dict[str, str] = {
    "krista@cfa.org": "Krista",
    "ritu@computingforall.org": "Ritu",
    "qb_sync": "QB Sync",
    "compliance_monitor": "Compliance Monitor",
}


def display_actor(actor: Optional[str]) -> str:
    """Translate an actor string (email or agent name) to a display
    name. Known actors → mapped; email → local-part; other → as-is."""
    if not actor:
        return "Unknown"
    if actor in _ACTOR_DISPLAY_NAMES:
        return _ACTOR_DISPLAY_NAMES[actor]
    if "@" in actor:
        local, _, _ = actor.partition("@")
        return local
    return actor


# ---------------------------------------------------------------------------
# Silenced action prefixes
# ---------------------------------------------------------------------------
#
# classifier.* signals are internal per-transaction bookkeeping, not
# actionable events for the finance operator. They stay in the
# engine's audit_log (accessible via direct SQL / /compliance/activity
# query) but don't clutter the cockpit feed. Spec §v1.2.9 decision.

_SILENCED_PREFIXES: tuple[str, ...] = ("classifier.",)


def _is_silenced(action: str) -> bool:
    return any(action.startswith(p) for p in _SILENCED_PREFIXES)


# ---------------------------------------------------------------------------
# Action → display template
# ---------------------------------------------------------------------------
#
# When target_summary is present, it's interpolated into the template.
# When None, the ": {target_summary}" suffix is stripped cleanly.

_ACTION_TEMPLATES: dict[str, str] = {
    "compliance.flag_raised":          "Flag raised: {target_summary}",
    "compliance.flag.resolve":         "Resolved flag: {target_summary}",
    "compliance.flag.waive":           "Waived flag: {target_summary}",
    "compliance.flag.acknowledge":     "Acknowledged flag: {target_summary}",
    "compliance.explain_flag":         "Generated explanation for flag: {target_summary}",
    "allocation.approve":              "Approved allocation: {target_summary}",
    "allocation.reject":               "Rejected allocation: {target_summary}",
    "allocation.propose.manual":       "Proposed allocation: {target_summary}",
    "qb.sync.accounts":                "QB sync — accounts: {target_summary}",
    "qb.sync.classes":                 "QB sync — classes: {target_summary}",
    "qb.sync.transactions":            "QB sync — transactions: {target_summary}",
    "qb.sync.attachables":             "QB sync — attachables: {target_summary}",
    "qb.oauth.authorized":             "QB authorized: {target_summary}",
    "report.finalize":                 "Report finalized: {target_summary}",
    "time_effort.certified":           "Certification signed",
    "time_effort.draft.deterministic": "Time & effort certification drafted",
    "time_effort.draft.llm":           "Time & effort certification drafted (LLM-assisted)",
}


def _format_action_text(entry: dict) -> str:
    """Produce the action-line body. Unknown actions fall back to
    '{actor} performed {action}'."""
    action = entry.get("action", "")
    summary = entry.get("target_summary")
    template = _ACTION_TEMPLATES.get(action)

    if template is None:
        actor = display_actor(entry.get("actor"))
        return f"{actor} performed {action}" if action else actor

    if "{target_summary}" not in template:
        # Static template (e.g. time_effort.certified) — no interpolation.
        return template
    if summary is None or summary == "":
        # Template expects a summary but engine returned none —
        # strip the "': {target_summary}" tail cleanly rather than
        # rendering ": None".
        return template.replace(": {target_summary}", "").strip()
    return template.format(target_summary=summary)


# ---------------------------------------------------------------------------
# Timestamp formatting — matches the prior hardcoded FEED's shape.
# ---------------------------------------------------------------------------


def _format_timestamp(
    occurred_at: str, now: Optional[datetime] = None
) -> str:
    """Human-friendly relative time label. Input is an ISO-8601 string
    (UTC) from the engine; output bands match the prior hardcoded
    FEED's style:
      - < 1 min          → "just now"
      - < 1 hr           → "N min ago"
      - same day         → "H:MM AM/PM"
      - previous day     → "Yesterday at H:MM AM/PM"
      - within year      → "Mon D at H:MM AM/PM"
      - older            → "Mon D, YYYY"
    """
    if not occurred_at:
        return ""
    try:
        ts = datetime.fromisoformat(occurred_at.replace("Z", "+00:00"))
    except ValueError:
        return occurred_at

    current = now or datetime.now(timezone.utc)
    delta = current - ts

    if delta.total_seconds() < 60:
        return "just now"
    if delta < timedelta(hours=1):
        minutes = int(delta.total_seconds() / 60)
        return f"{minutes} min ago"

    # strftime %I on Windows gives "08" with a leading zero; strip.
    time_str = ts.strftime("%I:%M %p").lstrip("0")

    if ts.date() == current.date():
        return time_str
    if ts.date() == (current - timedelta(days=1)).date():
        return f"Yesterday at {time_str}"
    if ts.year == current.year:
        date_str = ts.strftime("%b %d").replace(" 0", " ")
        return f"{date_str} at {time_str}"
    return ts.strftime("%b %d, %Y").replace(" 0", " ")


# ---------------------------------------------------------------------------
# Public entrypoints
# ---------------------------------------------------------------------------


def render_entry(entry: dict, now: Optional[datetime] = None) -> dict:
    """Translate one raw audit_log entry into the feed display shape."""
    return {
        "timestamp_label": _format_timestamp(entry.get("occurred_at", ""), now),
        "actor_label": display_actor(entry.get("actor")),
        "action_text": _format_action_text(entry),
        "metadata_text": None,
        "occurred_at": entry.get("occurred_at", ""),
    }


def render_entries(
    raw_response: dict, now: Optional[datetime] = None
) -> list[dict]:
    """Filter silenced actions and render the rest. Preserves the
    engine's newest-first order."""
    entries = raw_response.get("entries") or []
    rendered: list[dict] = []
    for entry in entries:
        if _is_silenced(entry.get("action", "")):
            continue
        rendered.append(render_entry(entry, now))
    return rendered
