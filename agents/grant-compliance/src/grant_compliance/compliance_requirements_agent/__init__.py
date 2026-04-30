"""Compliance Requirements Agent.

Two-mode agent that produces grant-tailored documentation requirements
specifications (Mode A) and answers narrowly-scoped Q&A (Mode B), both
grounded in the regulatory corpus at
agents/grant-compliance/data/regulatory_corpus/.

Spec: agents/grant-compliance/docs/compliance_requirements_agent_spec.md
"""

from grant_compliance.compliance_requirements_agent.agent import (
    ComplianceRequirementsAgent,
)
from grant_compliance.compliance_requirements_agent.schemas import (
    ApplicabilityScope,
    ComplianceArea,
    ComplianceRequirementsSet,
    GrantContext,
    QARequest,
    QAResponse,
    Requirement,
    Scope,
    Severity,
)

__all__ = [
    "ApplicabilityScope",
    "ComplianceArea",
    "ComplianceRequirementsAgent",
    "ComplianceRequirementsSet",
    "GrantContext",
    "QARequest",
    "QAResponse",
    "Requirement",
    "Scope",
    "Severity",
]
