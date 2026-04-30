"""Pydantic schemas for the Compliance Requirements Agent.

These describe the agent's I/O contract — what Mode A produces and Mode B
returns. Distinct from `api/schemas.py` (which carries route-level request /
response shapes) so the agent's domain model can evolve independently of
HTTP wire shapes.

Validation responsibilities:
  - Requirement.regulatory_citation must be non-empty (no claim without
    citation, per spec §"Honesty discipline")
  - severity_if_missing must be one of the four allowed values
  - applicability.applies_to must be one of the seven allowed values
  - QAResponse must include either an answer + citations OR an
    out_of_scope_warning
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class ComplianceArea(str, Enum):
    procurement_standards = "procurement_standards"
    full_and_open_competition = "full_and_open_competition"
    cost_reasonableness = "cost_reasonableness"
    classification_200_331 = "classification_200_331"
    subrecipient_monitoring = "subrecipient_monitoring"
    conflict_of_interest = "conflict_of_interest"
    standards_of_conduct = "standards_of_conduct"


class ApplicabilityScope(str, Enum):
    all_contracts = "all_contracts"
    contracts_above_threshold = "contracts_above_threshold"
    sole_source_only = "sole_source_only"
    contractors_only = "contractors_only"
    subrecipients_only = "subrecipients_only"
    specific_circumstance = "specific_circumstance"


class Severity(str, Enum):
    """Per spec: severity reflects how a federal auditor or pass-through
    monitor would likely characterize a finding if the documentation is
    absent. The agent provides a reasoned default; counsel can revise.
    Severity is informational, not authoritative.
    """

    material = "material"
    significant = "significant"
    minor = "minor"
    procedural = "procedural"


# ---------------------------------------------------------------------------
# Mode A — Requirement and ComplianceRequirementsSet
# ---------------------------------------------------------------------------


class Applicability(BaseModel):
    """When this requirement applies."""

    applies_to: ApplicabilityScope
    threshold_value: Decimal | None = Field(
        default=None,
        description="Dollar threshold above which this requirement applies; "
        "set when applies_to == 'contracts_above_threshold'.",
    )
    circumstance_description: str | None = Field(
        default=None,
        description="Narrative for specific circumstances; required when "
        "applies_to == 'specific_circumstance'.",
    )

    @model_validator(mode="after")
    def _check_threshold_when_required(self) -> Applicability:
        if self.applies_to == ApplicabilityScope.contracts_above_threshold and self.threshold_value is None:
            raise ValueError(
                "applicability.threshold_value is required when applies_to == 'contracts_above_threshold'"
            )
        if self.applies_to == ApplicabilityScope.specific_circumstance and not self.circumstance_description:
            raise ValueError(
                "applicability.circumstance_description is required when applies_to == 'specific_circumstance'"
            )
        return self


class Requirement(BaseModel):
    """One documentation requirement implied by the regulation.

    Honesty discipline (per spec §"Honesty discipline"):
    - regulatory_citation must be non-empty (no claims without citation)
    - regulatory_text_excerpt must be non-empty (auditable against source)
    """

    requirement_id: str = Field(min_length=1)
    compliance_area: ComplianceArea
    regulatory_citation: str = Field(
        min_length=1,
        description="Specific CFR section, e.g. '2 CFR 200.318(c)(1)'. "
        "Required — outputs without citation are rejected at validation.",
    )
    regulatory_text_excerpt: str = Field(
        min_length=1,
        description="The relevant excerpt from the regulation, so the requirement "
        "is auditable against source.",
    )
    applicability: Applicability
    requirement_summary: str = Field(min_length=1)
    documentation_artifacts_required: list[str] = Field(default_factory=list)
    documentation_form_guidance: str | None = None
    cfa_specific_application: str | None = None
    severity_if_missing: Severity

    @field_validator("regulatory_citation")
    @classmethod
    def _citation_must_look_like_one(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("regulatory_citation cannot be empty")
        # Soft heuristic — accept "2 CFR 200.xxx" or "OMB Compliance Supplement"
        # patterns. Actual presence-in-corpus check happens at agent.py level.
        return v


class Scope(BaseModel):
    """What a generation run covers."""

    compliance_areas: list[ComplianceArea] = Field(default_factory=list)
    contract_ids: list[str] = Field(default_factory=list)
    engagement_id: str | None = None
    description: str | None = None


class GrantContext(BaseModel):
    """Snapshot of CFA-specific facts the agent used to tailor output."""

    grant_id: str
    grant_name: str
    funder_name: str | None = None
    funder_type: str | None = None
    period_start: datetime | None = None
    period_end: datetime | None = None
    total_award_cents: int | None = None
    contract_count: int | None = None
    classifications: dict = Field(default_factory=dict)
    thresholds_in_play: dict = Field(default_factory=dict)
    notes: str | None = None


class ComplianceRequirementsSet(BaseModel):
    """The Mode A output — a comprehensive structured documentation
    requirements specification."""

    set_id: str
    generated_at: datetime
    scope: Scope
    regulatory_corpus_version: str
    grant_context: GrantContext
    requirements: list[Requirement]

    model_config = ConfigDict(arbitrary_types_allowed=True)


# ---------------------------------------------------------------------------
# Mode B — Q&A
# ---------------------------------------------------------------------------


class QARequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)
    context_hints: dict | None = Field(
        default=None,
        description="Optional caller-supplied context (e.g. {'contract_id': '...'}) "
        "the agent may use to scope the response.",
    )
    asked_by: str | None = None


class QAResponse(BaseModel):
    """Mode B response. Honesty constraints:

    - `answer` must be non-empty IF this is not a refusal.
    - `regulatory_citations` must be non-empty for any answer that purports
      to derive from the regulation. Empty citations are allowed only when
      `out_of_scope_warning` or `refused` indicates the agent declined to
      answer on substance.
    - `caveats` is REQUIRED — the agent always carries the "informational,
      not legal advice" caveat.
    """

    answer: str = ""
    regulatory_citations: list[str] = Field(default_factory=list)
    relevant_existing_requirements: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    out_of_scope_warning: str | None = None
    refused: bool = Field(
        default=False,
        description="True when the agent refused to answer because the "
        "question seeks a legal opinion or falls outside its corpus scope. "
        "When refused == True, `answer` carries the structured refusal text.",
    )

    @model_validator(mode="after")
    def _check_substantive_answer_has_citations(self) -> QAResponse:
        # If this is not a refusal and not flagged out-of-scope, the agent
        # must have cited at least one regulatory section.
        if not self.refused and not self.out_of_scope_warning:
            if not self.regulatory_citations:
                raise ValueError(
                    "QAResponse must include at least one regulatory_citation "
                    "for a substantive (non-refused, in-scope) answer."
                )
            if not self.answer.strip():
                raise ValueError(
                    "QAResponse.answer cannot be empty for a substantive answer."
                )
        if not self.caveats:
            raise ValueError(
                "QAResponse.caveats must include at least one caveat — typically "
                "the informational-not-legal-advice disclaimer."
            )
        return self
