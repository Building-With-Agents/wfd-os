"""Transaction Classifier.

For each unallocated transaction, propose one or more grant allocations with
a confidence score and a rationale. Low-confidence proposals go to a human
review queue — they are NOT auto-approved.

The agent considers:
  - Vendor name and memo (text matching against scope-of-work keywords)
  - QB Class already on the transaction (if the bookkeeper tagged it)
  - Historical allocations for similar vendors/categories
  - Active grants whose period covers the transaction date
  - Active budget lines whose category likely matches
"""

from __future__ import annotations

import json
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.agents.base import Agent
from grant_compliance.config import get_settings
from grant_compliance.db.models import (
    Allocation,
    AllocationStatus,
    Grant,
    QbClass,
    Transaction,
)

CLASSIFIER_SYSTEM = """\
You are a federal grant accounting assistant. You propose how a transaction
should be allocated across active grants. You do NOT make final decisions —
your output is reviewed by a human bookkeeper.

Output format: a single JSON object, no prose, with these fields:
  splits: array of {grant_id, amount_cents, budget_category, rationale}
          summing to the transaction amount (in cents).
  confidence: float between 0 and 1.
  notes: string, optional — anything the reviewer should know.

If you are not confident which grant a charge belongs to, set confidence < 0.5
and explain why in `notes`. The reviewer will decide.

Never make allowability determinations (whether a cost can be charged to a
federal grant). That is handled by a separate deterministic rule engine.
"""


class TransactionClassifier(Agent):
    name = "classifier"

    def classify(self, txn: Transaction) -> list[Allocation]:
        """Generate proposed allocations for a transaction. Returns the
        Allocation rows added to the session (not yet committed).
        """
        active_grants = self._active_grants_for_date(txn.txn_date)
        if not active_grants:
            self.log_action(
                action="classifier.no_active_grants",
                target_type="transaction",
                target_id=txn.id,
                note=f"No grants are active on {txn.txn_date}",
            )
            return []

        # Cheap rule first: if the QB Class on the transaction maps cleanly to
        # exactly one active grant, propose 100% to that grant with high
        # confidence. No LLM needed.
        if txn.qb_class_id:
            qb_class = self.db.get(QbClass, txn.qb_class_id)
            matched = [g for g in active_grants if g.qb_class_name == qb_class.name]
            if len(matched) == 1:
                grant = matched[0]
                allocation = Allocation(
                    transaction_id=txn.id,
                    grant_id=grant.id,
                    amount_cents=txn.amount_cents,
                    rationale=f"QB Class '{qb_class.name}' maps to grant '{grant.name}'",
                    confidence=0.99,
                    proposed_by=self.name,
                    status=AllocationStatus.proposed,
                )
                self.db.add(allocation)
                self.log_action(
                    action="classifier.propose.deterministic",
                    target_type="transaction",
                    target_id=txn.id,
                    outputs={"grant_id": grant.id, "confidence": 0.99},
                )
                return [allocation]

        # Otherwise, fall through to the LLM
        return self._llm_classify(txn, active_grants)

    def _active_grants_for_date(self, on_date: date) -> list[Grant]:
        stmt = (
            select(Grant)
            .where(Grant.period_start <= on_date)
            .where(Grant.period_end >= on_date)
            .where(Grant.closed.is_(False))
        )
        return list(self.db.execute(stmt).scalars())

    def _llm_classify(self, txn: Transaction, grants: list[Grant]) -> list[Allocation]:
        settings = get_settings()
        grant_summaries = [
            {
                "id": g.id,
                "name": g.name,
                "period": f"{g.period_start} to {g.period_end}",
                "scope": (g.scope_of_work or "")[:300],
            }
            for g in grants
        ]
        user_prompt = (
            "Classify this transaction.\n\n"
            f"Transaction:\n"
            f"  date: {txn.txn_date}\n"
            f"  vendor: {txn.vendor_name or '(none)'}\n"
            f"  memo: {txn.memo or '(none)'}\n"
            f"  amount_cents: {txn.amount_cents}\n\n"
            f"Active grants:\n{json.dumps(grant_summaries, indent=2)}\n"
        )

        response = self.llm(
            system=CLASSIFIER_SYSTEM,
            user=user_prompt,
            action="classifier.propose.llm",
            target_type="transaction",
            target_id=txn.id,
        )

        try:
            parsed = json.loads(response.text)
        except json.JSONDecodeError:
            self.log_action(
                action="classifier.parse_failed",
                target_type="transaction",
                target_id=txn.id,
                outputs={"raw": response.text[:500]},
            )
            return []

        confidence = float(parsed.get("confidence", 0.0))
        allocations: list[Allocation] = []
        for split in parsed.get("splits", []):
            allocation = Allocation(
                transaction_id=txn.id,
                grant_id=split["grant_id"],
                amount_cents=int(split["amount_cents"]),
                budget_category=split.get("budget_category"),
                rationale=split.get("rationale"),
                confidence=confidence,
                proposed_by=self.name,
                status=AllocationStatus.proposed,
            )
            self.db.add(allocation)
            allocations.append(allocation)

        # Confidence below threshold => stays "proposed", reviewer sees it in queue
        # Confidence above threshold => still "proposed" (we never auto-approve)
        # The threshold just affects UI sorting / urgency, not status.
        if confidence < settings.llm_confidence_threshold:
            self.log_action(
                action="classifier.low_confidence",
                target_type="transaction",
                target_id=txn.id,
                outputs={"confidence": confidence, "threshold": settings.llm_confidence_threshold},
            )

        return allocations
