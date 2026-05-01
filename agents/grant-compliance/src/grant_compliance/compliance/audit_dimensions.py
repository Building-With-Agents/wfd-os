"""Audit readiness dimensions — canonical dimension-to-regulation mapping.

These are the six compliance areas a Single Audit firm tests against for a
federal award under 2 CFR 200. They are encoded as Python data, NOT as LLM
prompts, because:
  - They must be reviewable and testable.
  - They change rarely; the regulation is the source of truth.
  - LLM judgment on "is this dimension audit-ready" is the wrong tool — the
    readiness percentage is computed deterministically from the underlying
    data (flags resolved, certifications signed, etc.).

The Audit Readiness tab's `_tab_audit` handler and `build_drills()`
`audit:*` panels will read from this module in later implementation steps
(changes 1, 2, and 4 of the v1.2 spec). This module itself does not query
any data or compute readiness — it only declares the static metadata
(id, title, auditor-perspective copy, CFR citations, owning role, default
tone) that both surfaces need.

Source: https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200
References below are to sections within 2 CFR Part 200 (Uniform Guidance).

Tone legend:
  good      - dimension is in good shape
  watch     - known gaps, progress being made
  critical  - material deficiency, must address before audit
  neutral   - no data yet / not computed

`default_tone` is the fallback used when no computed readiness is available.
When real computation lands (spec v1.2 change 1), tone is derived from the
readiness percentage and `default_tone` becomes the initial state only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Tone = Literal["good", "watch", "critical", "neutral"]


@dataclass(frozen=True)
class AuditDimension:
    id: str  # stable slug, e.g. "allowable_costs" — used in drill keys
    title: str  # human-readable label for the dimensions table
    what_auditors_look_for: str  # one-paragraph auditor perspective
    cfr_citations: tuple[str, ...]  # e.g. ("§200.302", "§200.334")
    compliance_supplement_area: str  # OMB Compliance Supplement relevance
    owner_role: str  # role slug; person assignment lives elsewhere
    default_tone: Tone


DIMENSIONS: tuple[AuditDimension, ...] = (
    AuditDimension(
        id="allowable_costs",
        title="Allowable costs",
        what_auditors_look_for=(
            "Every transaction maps to an allowable category under the grant "
            "budget (Exhibit B) and 2 CFR 200 cost principles."
        ),
        cfr_citations=("§§200.403–200.405", "§§200.420–200.476"),
        compliance_supplement_area="Cost principles, unallowable costs",
        owner_role="bookkeeper",
        default_tone="good",
    ),
    AuditDimension(
        id="transaction_documentation",
        title="Transaction documentation",
        what_auditors_look_for=(
            "Vendor invoices, receipts, and written approvals on file for "
            "every transaction — especially those over $2,500."
        ),
        cfr_citations=("§200.302", "§200.334"),
        compliance_supplement_area="Financial management, record retention",
        owner_role="bookkeeper",
        default_tone="watch",
    ),
    AuditDimension(
        id="time_effort",
        title="Time & effort certifications",
        what_auditors_look_for=(
            "Quarterly attestations from every federally-funded staff "
            "member documenting the share of effort charged to the award."
        ),
        cfr_citations=("§200.430(i)",),
        compliance_supplement_area="Personnel compensation support",
        owner_role="executive_director",
        default_tone="critical",
    ),
    AuditDimension(
        id="procurement",
        title="Procurement & competition",
        what_auditors_look_for=(
            "Competitive process or a documented sole-source justification "
            "on file for every contract awarded under the grant."
        ),
        cfr_citations=("§§200.317–200.327",),
        compliance_supplement_area="Procurement standards",
        owner_role="executive_director",
        default_tone="good",
    ),
    AuditDimension(
        id="subrecipient_monitoring",
        title="Subrecipient monitoring",
        what_auditors_look_for=(
            "Risk assessment, periodic monitoring, and follow-up evidence "
            "for each provider receiving grant pass-through funds."
        ),
        cfr_citations=("§§200.331–200.333",),
        compliance_supplement_area="Subrecipient monitoring requirements",
        owner_role="executive_director",
        default_tone="watch",
    ),
    AuditDimension(
        id="performance_reporting",
        title="Performance reporting accuracy",
        what_auditors_look_for=(
            "Reported performance metrics reconcile to the underlying source "
            "data with a clear audit trail."
        ),
        cfr_citations=("§§200.328–200.329",),
        compliance_supplement_area="Performance reporting",
        owner_role="program_operations",
        default_tone="good",
    ),
)


def get_dimension(dimension_id: str) -> AuditDimension | None:
    """Return the AuditDimension with the given id, or None if unknown."""
    return next((d for d in DIMENSIONS if d.id == dimension_id), None)


def dimension_ids() -> tuple[str, ...]:
    """Return the ids of all dimensions in declaration order."""
    return tuple(d.id for d in DIMENSIONS)
