"""Time & Effort Agent.

Drafts monthly time & effort certifications for employees whose salary is
charged to one or more federal grants. Required by 2 CFR 200.430.

The agent drafts; the employee (or a supervisor with first-hand knowledge)
must explicitly certify. Drafts are NEVER auto-certified.

Sources of signal (when available):
  - Calendar events tagged with project codes
  - Slack/email threads mentioning grants
  - Self-reported splits from prior months as a starting estimate

Until those integrations are wired up, this agent produces an evenly-split
draft based on which grants the employee is currently assigned to, with a
clear note that the human must adjust before signing.
"""

from __future__ import annotations

import json

from sqlalchemy.orm import Session

from grant_compliance.agents.base import Agent
from grant_compliance.db.models import Employee, Grant, TimeCertification

TIME_EFFORT_SYSTEM = """\
You are drafting a federal time & effort certification for one employee for
one calendar month. Output a single JSON object:
  splits: { "<grant_id>": <percent>, ... } summing to 100
  rationale: short string explaining the basis of the draft

This is a DRAFT only. The employee must review and certify. Do not invent
specific activities — describe the basis (e.g., "carried forward from prior
month", "based on assigned grants only — needs employee adjustment").
"""


class TimeEffortAgent(Agent):
    name = "time_effort_agent"

    def draft_certification(
        self,
        employee: Employee,
        period_year: int,
        period_month: int,
        assigned_grants: list[Grant],
        prior_splits: dict[str, float] | None = None,
    ) -> TimeCertification:
        """Create a draft TimeCertification for review. Not certified."""
        if not assigned_grants:
            raise ValueError(
                f"Employee {employee.name} has no assigned grants — "
                "no certification needed."
            )

        # Cheap path: one assigned grant => 100% to it, no LLM needed
        if len(assigned_grants) == 1:
            cert = TimeCertification(
                employee_id=employee.id,
                period_year=period_year,
                period_month=period_month,
                splits={assigned_grants[0].id: 100.0},
                drafted_by=self.name,
                rationale=f"Sole assigned grant: {assigned_grants[0].name}",
            )
            self.db.add(cert)
            self.log_action(
                action="time_effort.draft.deterministic",
                target_type="time_certification",
                target_id=cert.id,
                outputs={"splits": cert.splits},
            )
            return cert

        # LLM path: draft a starting estimate
        grant_summaries = [
            {"id": g.id, "name": g.name, "scope": (g.scope_of_work or "")[:200]}
            for g in assigned_grants
        ]
        user = (
            "Draft a time and effort certification.\n\n"
            f"Employee: {employee.name}\n"
            f"Period: {period_year}-{period_month:02d}\n"
            f"Assigned grants:\n{json.dumps(grant_summaries, indent=2)}\n"
            f"Prior month splits (if any): {json.dumps(prior_splits or {}, indent=2)}\n"
        )
        response = self.llm(
            system=TIME_EFFORT_SYSTEM,
            user=user,
            action="time_effort.draft.llm",
            target_type="employee",
            target_id=employee.id,
        )

        try:
            parsed = json.loads(response.text)
            splits = {k: float(v) for k, v in parsed.get("splits", {}).items()}
            rationale = parsed.get("rationale", "LLM draft — needs employee review.")
        except (json.JSONDecodeError, ValueError, TypeError):
            # Fall back to even split
            even = round(100.0 / len(assigned_grants), 2)
            splits = {g.id: even for g in assigned_grants}
            rationale = "LLM parse failed — fell back to even split. Employee must adjust."

        cert = TimeCertification(
            employee_id=employee.id,
            period_year=period_year,
            period_month=period_month,
            splits=splits,
            drafted_by=self.name,
            rationale=rationale,
        )
        self.db.add(cert)
        return cert

    def certify(
        self,
        cert: TimeCertification,
        certifier_email: str,
        method: str = "click",
        adjustments: dict[str, float] | None = None,
    ) -> TimeCertification:
        """Apply final splits and mark certified. This is a HUMAN action;
        the agent only records it.
        """
        if adjustments is not None:
            total = sum(adjustments.values())
            if abs(total - 100.0) > 0.01:
                raise ValueError(f"Splits must sum to 100, got {total}")
            cert.splits = adjustments
        from datetime import datetime, timezone

        cert.certified_by = certifier_email
        cert.certified_at = datetime.now(timezone.utc)
        cert.signature_method = method
        self.log_action(
            action="time_effort.certified",
            target_type="time_certification",
            target_id=cert.id,
            inputs={"certifier": certifier_email, "method": method},
            outputs={"final_splits": cert.splits},
        )
        return cert
