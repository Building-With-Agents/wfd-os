"""Reporting Agent.

Generates draft funder reports from the local DB. Drafts are NEVER auto-sent.
A human reviews, finalizes, and exports.

Initial supported report types:
  - SF-425 (Federal Financial Report) — the standard federal cash & expenditure
    report submitted to most federal awarding agencies.
  - foundation_narrative — a generic structured payload suitable for most
    private-foundation interim/final reports.

Each report references a `snapshot_id` so it can be reproduced later.
"""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.agents.base import Agent
from grant_compliance.db.models import (
    Allocation,
    AllocationStatus,
    BudgetLine,
    ComplianceFlag,
    FlagSeverity,
    FlagStatus,
    Grant,
    ReportDraft,
)


class ReportingAgent(Agent):
    name = "reporting_agent"

    # ------------------------------------------------------------------
    # SF-425
    # ------------------------------------------------------------------

    def draft_sf425(
        self,
        grant: Grant,
        period_start: date,
        period_end: date,
    ) -> ReportDraft:
        """Build a draft SF-425 payload. Does not include the federal awarding
        agency boilerplate (DUNS/UEI, EIN, address, etc.) — those are pulled
        in at finalization time from org settings.
        """
        self._block_on_blockers(grant)

        approved = self._approved_allocations_in_period(grant, period_start, period_end)
        cumulative = self._approved_allocations_in_period(grant, grant.period_start, period_end)

        period_total = sum(a.amount_cents for a in approved)
        cumulative_total = sum(a.amount_cents for a in cumulative)

        # SF-425 fields (subset; full form has ~17 numbered lines)
        payload = {
            "report_type": "SF-425",
            "grant": {
                "name": grant.name,
                "award_number": grant.award_number,
                "period_of_performance": [
                    grant.period_start.isoformat(),
                    grant.period_end.isoformat(),
                ],
                "total_award_cents": grant.total_award_cents,
            },
            "reporting_period": [period_start.isoformat(), period_end.isoformat()],
            "transactions": {
                "federal_cash_outlays_this_period_cents": period_total,
                "federal_cash_outlays_cumulative_cents": cumulative_total,
                "federal_share_of_unliquidated_obligations_cents": 0,  # TODO
                "unobligated_balance_cents": grant.total_award_cents - cumulative_total,
            },
            "indirect_expense": self._indirect_block(grant, cumulative_total),
            "allocation_count_this_period": len(approved),
        }

        snapshot_id = str(uuid.uuid4())
        draft = ReportDraft(
            grant_id=grant.id,
            report_type="SF-425",
            period_start=period_start,
            period_end=period_end,
            payload=payload,
            snapshot_id=snapshot_id,
        )
        self.db.add(draft)
        self.log_action(
            action="report.draft.sf425",
            target_type="grant",
            target_id=grant.id,
            outputs={
                "draft_id_pending_flush": True,
                "period_total_cents": period_total,
                "cumulative_total_cents": cumulative_total,
            },
        )
        return draft

    # ------------------------------------------------------------------
    # Foundation narrative
    # ------------------------------------------------------------------

    def draft_foundation_narrative(
        self,
        grant: Grant,
        period_start: date,
        period_end: date,
    ) -> ReportDraft:
        """Generic foundation report. Most foundations want: budget vs actual
        by category, narrative of activities, and any deviations from plan.
        We produce the structured part; the LLM can be invoked separately to
        draft the narrative prose for human editing.
        """
        approved = self._approved_allocations_in_period(grant, period_start, period_end)
        budget_lines = list(self.db.execute(select(BudgetLine).where(BudgetLine.grant_id == grant.id)).scalars())

        by_category: dict[str, int] = {}
        for a in approved:
            by_category[a.budget_category or "Uncategorized"] = (
                by_category.get(a.budget_category or "Uncategorized", 0) + a.amount_cents
            )

        budget_vs_actual = []
        for line in budget_lines:
            actual = by_category.pop(line.category, 0)
            budget_vs_actual.append(
                {
                    "category": line.category,
                    "budgeted_cents": line.budgeted_cents,
                    "actual_cents": actual,
                    "variance_cents": line.budgeted_cents - actual,
                }
            )
        # Anything spent in a category with no budget line
        for cat, actual in by_category.items():
            budget_vs_actual.append(
                {
                    "category": cat,
                    "budgeted_cents": 0,
                    "actual_cents": actual,
                    "variance_cents": -actual,
                    "warning": "No budget line for this category",
                }
            )

        payload = {
            "report_type": "foundation_narrative",
            "grant": {"name": grant.name, "award_number": grant.award_number},
            "reporting_period": [period_start.isoformat(), period_end.isoformat()],
            "budget_vs_actual": budget_vs_actual,
            "narrative": "[Draft narrative to be added — call /reports/{id}/narrative to generate]",
        }

        draft = ReportDraft(
            grant_id=grant.id,
            report_type="foundation_narrative",
            period_start=period_start,
            period_end=period_end,
            payload=payload,
            snapshot_id=str(uuid.uuid4()),
        )
        self.db.add(draft)
        return draft

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _approved_allocations_in_period(
        self, grant: Grant, start: date, end: date
    ) -> list[Allocation]:
        # Allocations in period = transactions whose date falls in the period
        from grant_compliance.db.models import Transaction

        stmt = (
            select(Allocation)
            .join(Transaction, Allocation.transaction_id == Transaction.id)
            .where(Allocation.grant_id == grant.id)
            .where(Allocation.status == AllocationStatus.approved)
            .where(Transaction.txn_date >= start)
            .where(Transaction.txn_date <= end)
        )
        return list(self.db.execute(stmt).scalars())

    def _indirect_block(self, grant: Grant, mtdc_cents: int) -> dict:
        if grant.indirect_rate_pct is None:
            return {"applied": False, "reason": "No indirect rate on file."}
        # NOTE: MTDC vs. TDC vs. salary-base depends on the grant's basis.
        # This is a simplification; check `grant.indirect_rate_basis` in real use.
        amount = int(round(mtdc_cents * (grant.indirect_rate_pct / 100.0)))
        return {
            "applied": True,
            "rate_pct": grant.indirect_rate_pct,
            "basis": grant.indirect_rate_basis or "MTDC",
            "amount_cents": amount,
        }

    def _block_on_blockers(self, grant: Grant) -> None:
        """Refuse to draft a report if there are open blocker-severity flags
        on transactions allocated to this grant.
        """
        from grant_compliance.db.models import Transaction

        open_blockers = (
            self.db.query(ComplianceFlag)
            .join(Transaction, ComplianceFlag.transaction_id == Transaction.id)
            .join(Allocation, Allocation.transaction_id == Transaction.id)
            .filter(Allocation.grant_id == grant.id)
            .filter(ComplianceFlag.severity == FlagSeverity.blocker)
            .filter(ComplianceFlag.status == FlagStatus.open)
            .count()
        )
        if open_blockers:
            raise RuntimeError(
                f"Cannot draft report: {open_blockers} open blocker flag(s) on this grant. "
                "Resolve or waive them first."
            )
