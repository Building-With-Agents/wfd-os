"""2 CFR 200 Subpart E — encoded unallowable / partially-allowable costs.

These are the rules that determine whether a cost can be charged to a federal
award. They are encoded as Python data, NOT as LLM prompts, because:
  - They must be reviewable and testable.
  - They change rarely; the regulation is the source of truth.
  - LLM judgment on "is this allowable" is the wrong tool for the job.

The Compliance Monitor agent uses these rules deterministically, then can
optionally invoke an LLM to *explain* a flag in plain language for the user.

Source: https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200
References below are to sections within 2 CFR Part 200, Subpart E.

Status legend:
  unallowable          - never chargeable to a federal award
  unallowable_unless   - chargeable only under specific conditions
  conditional          - allowable but with limits or special documentation
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Status = Literal["unallowable", "unallowable_unless", "conditional"]


@dataclass(frozen=True)
class CostRule:
    rule_id: str  # internal, e.g. "UC.200.421"
    citation: str  # human-readable, e.g. "2 CFR 200.421"
    title: str
    status: Status
    summary: str
    # Keywords / vendor patterns / account types that trigger evaluation.
    # Matching is a *trigger* for the rule, not a determination — the human
    # (or a constrained LLM call) makes the final call.
    trigger_keywords: tuple[str, ...] = ()
    trigger_account_types: tuple[str, ...] = ()


# A starter set. This list is NOT exhaustive — Subpart E has dozens of sections.
# Add to this file as the org encounters new cost types.
RULES: tuple[CostRule, ...] = (
    CostRule(
        rule_id="UC.200.421",
        citation="2 CFR 200.421",
        title="Advertising and public relations",
        status="unallowable_unless",
        summary=(
            "Advertising costs are unallowable except for: recruitment of personnel, "
            "procurement of goods and services, disposal of scrap/surplus, and "
            "specific program purposes required by the federal award."
        ),
        trigger_keywords=("advertising", "ad spend", "marketing", "promotion", "billboard"),
    ),
    CostRule(
        rule_id="UC.200.423",
        citation="2 CFR 200.423",
        title="Alcoholic beverages",
        status="unallowable",
        summary="Costs of alcoholic beverages are unallowable.",
        trigger_keywords=("wine", "beer", "liquor", "alcohol", "spirits", "champagne"),
    ),
    CostRule(
        rule_id="UC.200.425",
        citation="2 CFR 200.425",
        title="Audit services",
        status="conditional",
        summary=(
            "Reasonable audit costs are allowable, but costs of audits not performed in "
            "accordance with Subpart F are unallowable."
        ),
        trigger_keywords=("audit", "auditor"),
    ),
    CostRule(
        rule_id="UC.200.434",
        citation="2 CFR 200.434",
        title="Contributions and donations",
        status="unallowable",
        summary="Contributions and donations made by the recipient are unallowable.",
        trigger_keywords=("donation", "contribution to", "gift to"),
    ),
    CostRule(
        rule_id="UC.200.438",
        citation="2 CFR 200.438",
        title="Entertainment costs",
        status="unallowable_unless",
        summary=(
            "Entertainment costs (amusement, diversion, social activities) are unallowable "
            "unless they have a programmatic purpose authorized in the approved budget or "
            "with prior written approval of the federal awarding agency."
        ),
        trigger_keywords=(
            "entertainment", "concert tickets", "sporting event", "theater", "social event"
        ),
    ),
    CostRule(
        rule_id="UC.200.439",
        citation="2 CFR 200.439",
        title="Equipment and other capital expenditures",
        status="conditional",
        summary=(
            "Capital expenditures for general purpose equipment, buildings, and land are "
            "unallowable as direct charges except with prior written approval. Special "
            "purpose equipment requires prior approval if cost exceeds $5,000."
        ),
        trigger_keywords=("equipment purchase", "capital", "building", "vehicle purchase"),
    ),
    CostRule(
        rule_id="UC.200.441",
        citation="2 CFR 200.441",
        title="Fines, penalties, damages and other settlements",
        status="unallowable",
        summary=(
            "Costs from violations of, or failure to comply with, federal/state/local/foreign "
            "laws and regulations are unallowable, except when incurred per federal agency "
            "instructions or with prior written approval."
        ),
        trigger_keywords=("fine", "penalty", "late fee", "settlement payment"),
    ),
    CostRule(
        rule_id="UC.200.442",
        citation="2 CFR 200.442",
        title="Fund raising and investment management costs",
        status="unallowable",
        summary=(
            "Costs of organized fund raising (financial campaigns, solicitation of gifts, "
            "etc.) are unallowable, regardless of purpose."
        ),
        trigger_keywords=("fundraising", "fund raising", "donor cultivation", "gala"),
    ),
    CostRule(
        rule_id="UC.200.445",
        citation="2 CFR 200.445",
        title="Goods or services for personal use",
        status="unallowable",
        summary=(
            "Costs of goods or services for personal use of the recipient's employees are "
            "unallowable regardless of whether the cost is reported as taxable income."
        ),
        trigger_keywords=("personal", "employee gift"),
    ),
    CostRule(
        rule_id="UC.200.450",
        citation="2 CFR 200.450",
        title="Lobbying",
        status="unallowable",
        summary=(
            "Costs of attempting to influence federal/state legislation or executive action "
            "(lobbying) are generally unallowable. Limited exceptions exist; see the section."
        ),
        trigger_keywords=("lobbying", "lobbyist", "advocacy day", "legislative"),
    ),
    CostRule(
        rule_id="UC.200.469",
        citation="2 CFR 200.469",
        title="Student activity costs",
        status="unallowable_unless",
        summary=(
            "Costs incurred for intramural activities, student publications, student clubs, "
            "and other student activities are unallowable unless specifically provided for "
            "in the federal award."
        ),
        trigger_keywords=("student activity", "intramural", "student club"),
    ),
    CostRule(
        rule_id="UC.200.474",
        citation="2 CFR 200.474",
        title="Travel costs",
        status="conditional",
        summary=(
            "Travel costs are allowable when reasonable and necessary, consistent with "
            "written travel policy, and when the purpose is documented. First-class and "
            "premium-class airfare are unallowable absent specific justification."
        ),
        trigger_keywords=("travel", "airfare", "hotel", "lodging", "per diem", "mileage"),
    ),
)


def rules_triggered_by(text: str | None, account_type: str | None = None) -> list[CostRule]:
    """Return rules whose triggers match the given memo/vendor text or account type.

    A match is a *signal to evaluate*, not a determination. The Compliance
    Monitor decides what to do with the match (flag severity, message, etc.).
    """
    matches: list[CostRule] = []
    text_lower = (text or "").lower()
    for rule in RULES:
        if account_type and account_type in rule.trigger_account_types:
            matches.append(rule)
            continue
        if any(kw in text_lower for kw in rule.trigger_keywords):
            matches.append(rule)
    return matches


def get_rule(rule_id: str) -> CostRule | None:
    return next((r for r in RULES if r.rule_id == rule_id), None)
