"""Display helpers for the Audit Readiness tab.

Translates the canonical role slugs returned by the compliance engine's
`GET /compliance/dimensions` endpoint (e.g. "bookkeeper") into the
person names the cockpit UI shows today (e.g. "Krista"). This is the
temporary v1.2 mechanism for owner display — a real ownership-assignment
system (mapping grants + dimensions to specific people by ID, not by
role) is future work. See agents/grant-compliance/docs/audit_readiness_tab_spec.md.

Imported by:
  - agents/finance/cockpit_api.py::_tab_audit  (dimension-table owner column)
  - agents/finance/design/cockpit_data.py::build_drills  (drill-panel summary)

TODO(v1.2 cockpit-side step 2 follow-up): add pytest infrastructure on
feature/finance-cockpit and cover the mapping + fallback cases. Tests
are deferred per the scope decision in step 2 cockpit-side — see
integration_notes.md on feature/compliance-engine-extract for the
deferral record.
"""

from __future__ import annotations


# Mapping of role slug → display name. v1.2 snapshot of the three roles
# currently returned by the engine for the audit dimensions. Extend here
# when new roles are added on the engine side (and coordinate the
# display text with Ritu before shipping).
_ROLE_DISPLAY_NAMES: dict[str, str] = {
    "bookkeeper": "Krista",
    "executive_director": "Ritu",
    "program_operations": "Bethany · Gage",
}


def display_name_for_role(role: str | None) -> str:
    """Return a human-readable display name for an owner role slug.

    - Known role → mapped name.
    - Empty / None → "—" so the UI column isn't awkwardly blank.
    - Unknown role → the role string with a trailing " (?)" so the
      gap is visible in the UI rather than silently hidden. Surfacing
      the missing mapping is preferable to a generic fallback that
      would mask the issue.
    """
    if not role:
        return "—"
    return _ROLE_DISPLAY_NAMES.get(role, f"{role} (?)")
