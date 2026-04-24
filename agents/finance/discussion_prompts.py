"""Seeded prompts for the Finance Cockpit drill-chat surface.

Returns three hand-authored prompts per drill, keyed by the drill_key
prefix. Provider drills tone-branch on the entry's status_chip — red-band
providers get a different set than green/neutral ones. Other drill types
share a single prompt set per type.

Hand-authored rather than LLM-generated per the implementation decision
logged in agents/finance/design/chat_spec.md — deterministic, copy-
reviewable, and the drill-key taxonomy is small (seven prefixes).

See chat_spec.md §"Seeded prompts" (Surface 2: Drill chat) for the
authoritative prompt list.
"""
from __future__ import annotations

from typing import Any


_PROVIDER_RED_PROMPTS: tuple[str, ...] = (
    "Why is this in the red band?",
    "What's driving the CPP?",
    "Which transactions contributed most?",
)

_PROVIDER_GREEN_PROMPTS: tuple[str, ...] = (
    "What's keeping this on track?",
    "Show me the spend pattern",
    "Any concentration risk?",
)

_BACKBONE_PROMPTS: tuple[str, ...] = (
    "What happens if we don't move the $700k?",
    "Where's the burn concentrated?",
    "When do we run out?",
)

_PLACEMENTS_PROMPTS: tuple[str, ...] = (
    "What drove the Q1 numbers?",
    "How far are we from the grant goal?",
    "Where is recovery coming from?",
)

_REIMBURSEMENT_PROMPTS: tuple[str, ...] = (
    "When should the funds land?",
    "What's the cash-flow exposure?",
    "Which invoices are still pending?",
)

_FLAGS_PROMPTS: tuple[str, ...] = (
    "Which one needs attention first?",
    "Who owns the most HIGH items?",
    "What's changed since last week?",
)

_AUDIT_PROMPTS: tuple[str, ...] = (
    "What's the biggest open gap?",
    "What closes this fastest?",
    "Which providers contribute?",
)

_DECISION_PROMPTS: tuple[str, ...] = (
    "What's the shortest path to close this?",
    "Who else needs to weigh in?",
    "What changes if we don't act this week?",
)


def _provider_prompts(entry: dict) -> tuple[str, ...]:
    tone = (entry.get("status_chip") or {}).get("tone")
    if tone == "critical":
        return _PROVIDER_RED_PROMPTS
    return _PROVIDER_GREEN_PROMPTS


def _category_prompts(entry: dict) -> tuple[str, ...]:
    title = entry.get("title") or "this category"
    return (
        f"What's driving spend in {title}?",
        "How much runway does this leave at current pace?",
        "Where's the biggest risk if spending keeps up?",
    )


def _default_prompts(entry: dict) -> tuple[str, ...]:
    title = entry.get("title") or "this drill"
    return (
        f"Summarize {title}",
        "What's the biggest concern here?",
        "What should I look at next?",
    )


def generate_discussion_prompts(drill_key: str, entry: dict[str, Any]) -> list[str]:
    """Return three seeded prompts for a drill's chat panel.

    Uses a prefix-routed table. Callers pass the raw drill_key (e.g.
    ``"provider:Ada"``) and the drill entry dict. The entry is only read
    for tone-branching (provider red band) and for default-prompt
    interpolation; no mutation.
    """
    if drill_key.startswith("provider:"):
        return list(_provider_prompts(entry))
    if drill_key.startswith("category:"):
        return list(_category_prompts(entry))
    if drill_key.startswith("decision:"):
        return list(_DECISION_PROMPTS)
    if drill_key.startswith("audit:"):
        return list(_AUDIT_PROMPTS)
    if drill_key == "backbone":
        return list(_BACKBONE_PROMPTS)
    if drill_key == "placements":
        return list(_PLACEMENTS_PROMPTS)
    if drill_key == "reimbursement":
        return list(_REIMBURSEMENT_PROMPTS)
    if drill_key == "flags":
        return list(_FLAGS_PROMPTS)
    return list(_default_prompts(entry))
