"""wfdos_common.models — shared Pydantic models + scoping dataclasses.

Submodules:
  core     — APIEnvelope, ErrorDetail, AuditEvent, Tool (cross-cutting)
  domain   — StudentProfile, EmployerProfile, CandidateShowcase, Skill,
             Education, GapAnalysis (workforce domain)
  scoping  — Contact, Organization, ScopingRequest, ResearchResult,
             ScopingAnswer, ScopingAnalysis (consulting-intake pipeline;
             migrated from agents/scoping/models.py in #21)

Implemented in Building-With-Agents/wfd-os#21. Breaks the circular import
between wfdos_common.graph.sharepoint and agents.scoping.models by pulling
the scoping dataclasses into the shared package.
"""

from wfdos_common.models.core import (
    APIEnvelope,
    AuditEvent,
    ErrorDetail,
    Tool,
)
from wfdos_common.models.domain import (
    CandidateShowcase,
    Education,
    EmployerProfile,
    GapAnalysis,
    Skill,
    StudentProfile,
)
from wfdos_common.models.scoping import (
    Contact,
    Organization,
    ResearchResult,
    ScopingAnalysis,
    ScopingAnswer,
    ScopingRequest,
)

__all__ = [
    # core
    "APIEnvelope",
    "AuditEvent",
    "ErrorDetail",
    "Tool",
    # domain
    "CandidateShowcase",
    "Education",
    "EmployerProfile",
    "GapAnalysis",
    "Skill",
    "StudentProfile",
    # scoping
    "Contact",
    "Organization",
    "ResearchResult",
    "ScopingAnalysis",
    "ScopingAnswer",
    "ScopingRequest",
]
