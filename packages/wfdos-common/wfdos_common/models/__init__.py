"""wfdos_common.models — shared Pydantic models.

STATUS: STUB — implementation lands in Building-With-Agents/wfd-os#21.

Target scope (from #21):
- wfdos_common.models.core — APIEnvelope, ErrorDetail, AuditEvent, Tool
- wfdos_common.models.domain — StudentProfile, EmployerProfile,
  CandidateShowcase, Skill, Education
- wfdos_common.models.scoping — Contact, Organization, ScopingRequest,
  ResearchResult, ScopingAnalysis, ScopingAnswer (moved from
  agents/scoping/models.py; breaks circular import with graph module)
"""
