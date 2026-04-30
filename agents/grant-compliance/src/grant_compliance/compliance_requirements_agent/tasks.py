"""Scheduled-task entry points for Mode A.

For v1, Mode A is invocation-based per spec §"Open questions" #4 — Ritu
recommended invocation rather than automatic scheduling for v1, with the
option to add scheduling later. This module exists as a stub so the
scheduling hook is in place for v1.1 when scheduled regeneration becomes
desired.

To run a scheduled regeneration manually today, call
`run_scheduled_regeneration(grant_id, scope)` from a Python REPL or a
standalone script — but the canonical invocation path is the HTTP
endpoint POST /compliance/requirements/generate.
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from grant_compliance.compliance_requirements_agent.agent import (
    ComplianceRequirementsAgent,
)
from grant_compliance.compliance_requirements_agent.schemas import (
    ComplianceArea,
    Scope,
)
from grant_compliance.db.models import Grant


def run_scheduled_regeneration(
    db: Session,
    *,
    grant_id: str,
    compliance_areas: list[ComplianceArea] | None = None,
    invoked_by: str = "scheduled_task",
) -> str:
    """Run a Mode A regeneration for the given grant. Returns the new set_id.

    Default scope covers all in-scope compliance areas if `compliance_areas`
    is None — this is the canonical "regenerate everything" pass.
    """
    grant = db.get(Grant, grant_id)
    if grant is None:
        raise ValueError(f"Grant {grant_id!r} not found")

    if compliance_areas is None:
        compliance_areas = list(ComplianceArea)

    scope = Scope(
        compliance_areas=compliance_areas,
        description="Scheduled regeneration covering all in-scope compliance areas.",
    )
    agent = ComplianceRequirementsAgent(db)
    new_set = agent.generate_set(grant=grant, scope=scope, invoked_by=invoked_by)
    db.commit()
    return new_set.id
