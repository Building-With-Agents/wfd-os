"""Compliance Requirements Agent — core logic.

Two methods:

  generate_set(scope, force_opus=False)  — Mode A
      Reads the regulatory corpus, the grant context, and the scope. Calls
      the LLM. Parses + validates the structured JSON response against
      ComplianceRequirementsSet. Persists. Marks the prior current set as
      superseded. Returns the persisted set.

  answer_question(question, context_hints=None, asked_by=None)  — Mode B
      Reads the regulatory corpus and the current requirements set (if
      any). Calls the LLM. Parses + validates QAResponse. Logs to
      compliance_qa_log. Returns the response.

Both methods write to audit_log via the engine's existing pattern (the
base Agent class's `self.llm()` helper) AND write the full prompt + full
response to their feature-specific tables for reproducibility.

LLM nondeterminism: handled by validating against the strict Pydantic
schemas. Outputs that don't match the schema raise; agent.py logs the
failure and re-raises so the caller sees the validation error rather
than a silently-malformed set being persisted.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.agents.base import Agent
from grant_compliance.compliance_requirements_agent.corpus import Corpus, load_corpus
from grant_compliance.compliance_requirements_agent.prompts import (
    MODE_A_SYSTEM_PROMPT,
    MODE_B_SYSTEM_PROMPT,
    build_mode_a_user_prompt,
    build_mode_b_user_prompt,
)
from grant_compliance.compliance_requirements_agent.schemas import (
    ComplianceRequirementsSet as ComplianceRequirementsSetSchema,
    GrantContext,
    QARequest,
    QAResponse,
    Requirement,
    Scope,
)
from grant_compliance.config import get_settings
from grant_compliance.db.models import (
    ComplianceQALog,
    ComplianceRequirementRow,
    ComplianceRequirementsSet,
    Grant,
)
from grant_compliance.utils.llm import LLMResponse, get_llm


# Per spec §"LLM model selection":
#   - Mode A default = Sonnet
#   - Mode A initial-foundational run = Opus (when force_opus=True)
#   - Mode A regenerations = Sonnet
#   - Mode B = Sonnet always
# Both modes pass the alias through to LLMClient.complete(model=...),
# which uses the override for that single call without mutating
# engine-wide Settings.anthropic_model.
SONNET_ALIAS = "claude-sonnet-4-5"
OPUS_ALIAS = "claude-opus-4-7"


class AgentValidationError(RuntimeError):
    """Raised when the LLM response fails strict schema validation.

    The error message includes the validation details so the caller can
    surface them. The full LLM response and prompt are written to the
    audit_log even on validation failure, so a follow-up debug pass is
    possible.
    """


class ComplianceRequirementsAgent(Agent):
    """Mode A + Mode B agent. See module docstring."""

    name = "compliance_requirements_agent"

    def __init__(self, db: Session):
        super().__init__(db)
        self.corpus: Corpus = load_corpus()

    # ---------------------------------------------------------------------
    # Mode A
    # ---------------------------------------------------------------------

    def generate_set(
        self,
        *,
        grant: Grant,
        scope: Scope,
        force_opus: bool = False,
        invoked_by: str | None = None,
    ) -> ComplianceRequirementsSet:
        """Run Mode A end-to-end: build prompt, call LLM, validate, persist.

        On success, the new set becomes the `is_current=True` set for the
        grant; any prior current set is marked `superseded_by_id=<new>` and
        `is_current=False` in the same transaction.

        Returns the persisted ORM object.
        """
        grant_context = self._build_grant_context(grant)
        user_prompt = build_mode_a_user_prompt(
            corpus=self.corpus, grant_context=grant_context, scope=scope
        )

        # Per spec §"LLM model selection": Mode A defaults to Sonnet 4.5,
        # with optional Opus override for the foundational initial run.
        # The base Agent.llm() helper passes the override through to the
        # LLMClient, which honors it for this single call without mutating
        # engine-wide settings.
        model_override = OPUS_ALIAS if force_opus else SONNET_ALIAS

        response, used_model = self._call_llm_with_model_override(
            system=MODE_A_SYSTEM_PROMPT,
            user=user_prompt,
            action="compliance_requirements.generate_set",
            target_type="grant",
            target_id=grant.id,
            extra_inputs={"scope": scope.model_dump(mode="json")},
            model_override=model_override,
            max_tokens=32000,  # Mode A output is large; 16K truncated on first attempt
        )

        try:
            parsed = self._parse_mode_a_response(response.text)
        except (json.JSONDecodeError, ValidationError) as exc:
            self.log_action(
                action="compliance_requirements.generate_set.validation_failed",
                target_type="grant",
                target_id=grant.id,
                inputs={"scope": scope.model_dump(mode="json")},
                outputs={
                    "error": str(exc),
                    "raw_response_preview": response.text[:2000],
                },
                note="Mode A response failed schema validation.",
            )
            raise AgentValidationError(
                f"Mode A response failed validation: {exc}"
            ) from exc

        # Validate every requirement cites a section that exists in the
        # corpus. Per honesty discipline, the agent shouldn't be inventing
        # citations.
        self._validate_citations_in_corpus(parsed.requirements)

        # Persist. The prior current set (if any) is superseded in the
        # same transaction so there's never a window with two current sets.
        new_set = self._persist_set(
            grant=grant,
            scope=scope,
            grant_context=grant_context,
            parsed=parsed,
            response=response,
            used_model=used_model,
            user_prompt=user_prompt,
            invoked_by=invoked_by,
        )
        self.db.flush()
        return new_set

    def _build_grant_context(self, grant: Grant) -> GrantContext:
        """Snapshot CFA-specific facts for tailoring. Pulls from the
        engine's existing tables. Personnel-feature data and contracts
        inventory are out of scope for v1 per spec — those land via
        wfdos-common in v1.3+."""
        funder = grant.funder
        return GrantContext(
            grant_id=grant.id,
            grant_name=grant.name,
            funder_name=funder.name if funder else None,
            funder_type=funder.funder_type.value if funder and funder.funder_type else None,
            period_start=datetime.combine(grant.period_start, datetime.min.time()).replace(tzinfo=timezone.utc) if grant.period_start else None,
            period_end=datetime.combine(grant.period_end, datetime.min.time()).replace(tzinfo=timezone.utc) if grant.period_end else None,
            total_award_cents=grant.total_award_cents,
            contract_count=None,  # populate when contracts inventory lands
            classifications={
                "note": "Per-party classifications under §200.331 are populated by the cockpit's personnel feature; not yet wired into the engine for v1 of the requirements agent.",
            },
            thresholds_in_play={
                "micro_purchase_threshold_cents": 1_000_000,  # $10K
                "simplified_acquisition_threshold_cents": 25_000_000,  # $250K
            },
            notes=grant.scope_of_work,
        )

    def _parse_mode_a_response(self, text: str) -> ComplianceRequirementsSetSchema:
        """Parse + validate the JSON. Strips any leading/trailing markdown
        code fence the model accidentally included, then strict-validates."""
        cleaned = self._strip_code_fences(text)
        data = json.loads(cleaned)
        return ComplianceRequirementsSetSchema.model_validate(data)

    def _validate_citations_in_corpus(self, requirements: list[Requirement]) -> None:
        """Each requirement's regulatory_citation must reference a section
        present in the corpus. Reject fabricated citations."""
        # Build a lookup from corpus citations to compliance areas.
        corpus_citations = {d.citation for d in self.corpus.documents if d.is_citable}
        # Citations may include sub-paragraphs (e.g., "2 CFR 200.318(c)(1)").
        # Reduce to the section level for matching.
        section_re = re.compile(r"(2 CFR \d{3}\.\d+|OMB Compliance Supplement[^,]+)")

        unmatched: list[str] = []
        for req in requirements:
            section_match = section_re.search(req.regulatory_citation)
            if not section_match:
                unmatched.append(req.regulatory_citation)
                continue
            section = section_match.group(1).strip()
            if not any(section in c or c in section for c in corpus_citations):
                unmatched.append(req.regulatory_citation)
        if unmatched:
            raise AgentValidationError(
                f"Generated requirements cite {len(unmatched)} sections not present "
                f"in the corpus. First three: {unmatched[:3]}. The agent's prompt "
                f"forbids fabricating citations; this is a strict-validation failure."
            )

    def _persist_set(
        self,
        *,
        grant: Grant,
        scope: Scope,
        grant_context: GrantContext,
        parsed: ComplianceRequirementsSetSchema,
        response: LLMResponse,
        used_model: str,
        user_prompt: str,
        invoked_by: str | None,
    ) -> ComplianceRequirementsSet:
        # Find any existing current set for this grant. Mark it superseded.
        prior_current = self.db.execute(
            select(ComplianceRequirementsSet).where(
                ComplianceRequirementsSet.grant_id == grant.id,
                ComplianceRequirementsSet.is_current.is_(True),
            )
        ).scalar_one_or_none()

        new_set = ComplianceRequirementsSet(
            id=str(uuid4()),
            grant_id=grant.id,
            generated_at=datetime.now(timezone.utc),
            scope=scope.model_dump(mode="json"),
            regulatory_corpus_version=self.corpus.version,
            grant_context=grant_context.model_dump(mode="json"),
            model_name=used_model,
            model_response_text=response.text,
            prompt_text=user_prompt,
            prompt_hash=hashlib.sha256(user_prompt.encode("utf-8")).hexdigest(),
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
            is_current=True,
            reviewed_by=None,
            reviewed_at=None,
            review_notes=None,
        )
        self.db.add(new_set)
        self.db.flush()

        if prior_current is not None:
            prior_current.is_current = False
            prior_current.superseded_by_id = new_set.id

        for req in parsed.requirements:
            self.db.add(
                ComplianceRequirementRow(
                    id=str(uuid4()),
                    set_id=new_set.id,
                    requirement_id=req.requirement_id,
                    compliance_area=req.compliance_area.value,
                    regulatory_citation=req.regulatory_citation,
                    regulatory_text_excerpt=req.regulatory_text_excerpt,
                    applicability=req.applicability.model_dump(mode="json"),
                    requirement_summary=req.requirement_summary,
                    documentation_artifacts_required=req.documentation_artifacts_required,
                    documentation_form_guidance=req.documentation_form_guidance,
                    cfa_specific_application=req.cfa_specific_application,
                    severity_if_missing=req.severity_if_missing.value,
                )
            )

        self.log_action(
            action="compliance_requirements.set_persisted",
            target_type="compliance_requirements_set",
            target_id=new_set.id,
            inputs={
                "grant_id": grant.id,
                "scope": scope.model_dump(mode="json"),
                "invoked_by": invoked_by,
            },
            outputs={
                "set_id": new_set.id,
                "requirement_count": len(parsed.requirements),
                "prior_set_superseded": prior_current.id if prior_current else None,
                "model": used_model,
            },
        )
        return new_set

    # ---------------------------------------------------------------------
    # Mode B
    # ---------------------------------------------------------------------

    def answer_question(
        self,
        *,
        request: QARequest,
        grant: Grant | None = None,
    ) -> tuple[QAResponse, ComplianceQALog]:
        """Run Mode B end-to-end. Returns (parsed_response, persisted_log_row).

        If `grant` is provided, the agent loads that grant's current
        ComplianceRequirementsSet and includes a summary in the prompt so
        Mode B can reference Mode A output coherently via
        relevant_existing_requirements.
        """
        current_set_summary = self._summarize_current_set(grant) if grant else "(no current requirements set)"

        user_prompt = build_mode_b_user_prompt(
            corpus=self.corpus,
            question=request.question,
            context_hints=request.context_hints,
            current_set_summary=current_set_summary,
        )

        response, used_model = self._call_llm_with_model_override(
            system=MODE_B_SYSTEM_PROMPT,
            user=user_prompt,
            action="compliance_requirements.qa",
            target_type="grant",
            target_id=grant.id if grant else None,
            extra_inputs={"question_preview": request.question[:200]},
            model_override=SONNET_ALIAS,
            max_tokens=4000,
        )

        try:
            parsed = self._parse_mode_b_response(response.text)
        except (json.JSONDecodeError, ValidationError) as exc:
            self.log_action(
                action="compliance_requirements.qa.validation_failed",
                target_type="grant",
                target_id=grant.id if grant else None,
                inputs={"question_preview": request.question[:200]},
                outputs={
                    "error": str(exc),
                    "raw_response_preview": response.text[:2000],
                },
                note="Mode B response failed schema validation.",
            )
            raise AgentValidationError(
                f"Mode B response failed validation: {exc}"
            ) from exc

        log_row = ComplianceQALog(
            id=str(uuid4()),
            asked_at=datetime.now(timezone.utc),
            asked_by=request.asked_by,
            question=request.question,
            context_hints=request.context_hints or {},
            response=parsed.model_dump(mode="json"),
            refused=parsed.refused,
            model_name=used_model,
            model_response_text=response.text,
            prompt_text=user_prompt,
            prompt_hash=hashlib.sha256(user_prompt.encode("utf-8")).hexdigest(),
            input_tokens=response.input_tokens,
            output_tokens=response.output_tokens,
        )
        self.db.add(log_row)
        self.db.flush()
        return parsed, log_row

    def _summarize_current_set(self, grant: Grant) -> str:
        """Render the current ComplianceRequirementsSet's requirement_ids
        + summaries as compact text the prompt can include without paying
        for the full requirements_text_excerpt cost."""
        current = self.db.execute(
            select(ComplianceRequirementsSet).where(
                ComplianceRequirementsSet.grant_id == grant.id,
                ComplianceRequirementsSet.is_current.is_(True),
            )
        ).scalar_one_or_none()
        if not current:
            return "(no current requirements set)"
        lines = [
            f"set_id: {current.id}",
            f"generated_at: {current.generated_at.isoformat()}",
            f"corpus_version: {current.regulatory_corpus_version}",
            "requirements:",
        ]
        for r in current.requirements:
            lines.append(
                f"  - {r.requirement_id} [{r.compliance_area} / {r.regulatory_citation}] "
                f"severity={r.severity_if_missing}"
            )
        return "\n".join(lines)

    def _parse_mode_b_response(self, text: str) -> QAResponse:
        cleaned = self._strip_code_fences(text)
        data = json.loads(cleaned)
        return QAResponse.model_validate(data)

    # ---------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------

    def _call_llm_with_model_override(
        self,
        *,
        system: str,
        user: str,
        action: str,
        target_type: str | None,
        target_id: str | None,
        extra_inputs: dict[str, Any] | None,
        model_override: str | None = None,
        max_tokens: int = 4000,
    ) -> tuple[LLMResponse, str]:
        """Run an LLM call with an optional per-call model override and
        return the parsed response + the model alias actually served.

        `model_override` is passed to LLMClient.complete() via the base
        Agent.llm() helper. The LLMClient honors it for this single call
        without mutating engine-wide Settings.anthropic_model. The
        helper writes an audit_log entry recording both the requested
        model (in inputs.model_requested) and the served model (on the
        audit_log row's model column).
        """
        response = self.llm(
            system=system,
            user=user,
            action=action,
            target_type=target_type,
            target_id=target_id,
            extra_inputs={
                **(extra_inputs or {}),
                "engine_default_model": get_settings().anthropic_model,
            },
            max_tokens=max_tokens,
            # Omit temperature — Opus 4.x and later reject the parameter;
            # the default sampling behavior is what we want for this
            # structured-JSON output anyway.
            model=model_override,
        )
        return response, response.model

    @staticmethod
    def _strip_code_fences(text: str) -> str:
        """Permissive parsing — if the model wrapped JSON in a markdown
        code fence despite instructions, strip the fence."""
        t = text.strip()
        if t.startswith("```"):
            # find the first newline to skip the fence + language tag
            first_newline = t.find("\n")
            if first_newline != -1:
                t = t[first_newline + 1:]
            if t.endswith("```"):
                t = t[: -3]
        return t.strip()
