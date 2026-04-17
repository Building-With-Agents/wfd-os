"""Compliance Monitor.

Runs the deterministic rule engine over transactions and writes ComplianceFlag
rows. Optionally uses the LLM to draft user-friendly explanations of why a
flag was raised — but the raise/no-raise decision is always deterministic.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.agents.base import Agent
from grant_compliance.compliance.rules import run_all_for_transaction, to_orm
from grant_compliance.db.models import ComplianceFlag, Transaction


class ComplianceMonitor(Agent):
    name = "compliance_monitor"

    def scan_transaction(self, txn: Transaction) -> list[ComplianceFlag]:
        """Run all rules against one transaction. Returns the flags written
        to the session (not yet committed).
        """
        drafts = run_all_for_transaction(self.db, txn)
        flags: list[ComplianceFlag] = []
        for draft in drafts:
            # Idempotency: don't raise the same rule on the same transaction
            # twice if it's still open.
            existing = (
                self.db.query(ComplianceFlag)
                .filter(
                    ComplianceFlag.transaction_id == draft.transaction_id,
                    ComplianceFlag.rule_id == draft.rule_id,
                    ComplianceFlag.status.in_(("open", "acknowledged")),
                )
                .first()
            )
            if existing:
                continue
            flag = to_orm(draft)
            self.db.add(flag)
            flags.append(flag)
            self.log_action(
                action="compliance.flag_raised",
                target_type="transaction",
                target_id=txn.id,
                outputs={
                    "rule_id": draft.rule_id,
                    "severity": draft.severity.value,
                    "message": draft.message,
                },
            )
        return flags

    def scan_all_unscanned(self) -> int:
        """Scan every transaction. Returns the number of new flags raised."""
        stmt = select(Transaction)
        total = 0
        for txn in self.db.execute(stmt).scalars():
            total += len(self.scan_transaction(txn))
        return total

    def explain_flag(self, flag: ComplianceFlag) -> str:
        """Use the LLM to turn a terse flag into a plain-language paragraph
        the bookkeeper can show to a program manager. The raise/no-raise
        decision is NOT made by the LLM — only the explanation phrasing.
        """
        system = (
            "You are a federal grants compliance assistant. Explain the given "
            "flag to a non-technical program manager in 2-3 sentences. Do not "
            "make new claims about allowability — restate only what the flag says."
        )
        user = (
            "Explain this compliance flag in plain language.\n\n"
            f"Rule: {flag.rule_id} ({flag.rule_citation})\n"
            f"Severity: {flag.severity.value}\n"
            f"Message: {flag.message}"
        )
        response = self.llm(
            system=system,
            user=user,
            action="compliance.explain_flag",
            target_type="compliance_flag",
            target_id=flag.id,
        )
        return response.text
