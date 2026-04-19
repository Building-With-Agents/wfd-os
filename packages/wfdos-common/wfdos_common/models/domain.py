"""Cross-service domain models.

Initial set derived from observed SELECT patterns in
`agents/portal/{student,showcase,college,wji}_api.py`,
`agents/career-services/gap_analysis.py`, and the schema inventory at
`docs/database/wfdos-schema-inventory.md`.

These models are intentionally permissive (most fields Optional,
`extra='ignore'`) because the canonical schema isn't defined yet — that's
#22's scope. The goal of #21 is to give every service a single shared
shape to talk in; #22 locks the columns.

Any column observed in a SELECT somewhere should eventually land here.
Gaps are fine for now; add them as services migrate from dict-based
cursors to these models.
"""

from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class Skill(BaseModel):
    """A normalized skill from the skills taxonomy.

    embedding_vector is serialized to/from Postgres as a string literal
    (e.g. "[0.12, 0.34, ...]"); consumers parse into floats themselves.
    The vector dim (1536 today for OpenAI-compatible embeddings) is not
    asserted here — let the service validate it.
    """

    skill_id: Optional[int] = None
    skill_name: str
    embedding_vector: Optional[str] = Field(
        default=None,
        description="Postgres-side vector literal or None if not embedded yet.",
    )

    model_config = ConfigDict(extra="ignore")


class Education(BaseModel):
    """One row from student_education.

    Free-form today. Once the canonical schema lands the optional fields
    narrow (graduation_year to int, etc.).
    """

    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None

    model_config = ConfigDict(extra="ignore")


class StudentProfile(BaseModel):
    """Student master-record shape. Columns observed in
    `agents/portal/showcase_api.py`, `student_api.py`, `college_api.py`
    SELECTs as of #21.

    showcase_eligible / showcase_active are the talent-showcase gate
    (see CLAUDE.md — ALL required fields + gap_score >= 50 + resume
    finalized + staff-set showcase_active).
    """

    id: int
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

    # Location
    city: Optional[str] = None
    state: Optional[str] = None
    zipcode: Optional[str] = None

    # Education (latest)
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None

    # Intake / parse metadata
    resume_uploaded: Optional[bool] = None
    resume_parsed: Optional[bool] = None
    resume_blob_path: Optional[str] = None
    parse_confidence_score: Optional[float] = None
    profile_completeness_score: Optional[float] = None
    missing_required: Optional[list[str]] = None
    missing_preferred: Optional[list[str]] = None

    # Journey
    pipeline_status: Optional[str] = None
    track: Optional[str] = None  # ojt | direct-placement | unknown
    availability_status: Optional[str] = None

    # Showcase
    showcase_eligible: Optional[bool] = None
    showcase_active: Optional[bool] = None

    # Migration tags (Dynamics → Postgres)
    source_system: Optional[str] = None
    original_record_id: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class EmployerProfile(BaseModel):
    """Employer master-record shape. Columns observed in student_api.py,
    reporting/api.py, scripts/002-migrate-dataverse.py.

    Tight column set here pending the real schema in #22.
    """

    id: int
    name: Optional[str] = None
    website_url: Optional[str] = None
    industry: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None

    # Migration tags
    source_system: Optional[str] = None
    original_record_id: Optional[str] = None

    model_config = ConfigDict(extra="ignore")


class GapAnalysis(BaseModel):
    """One row of skill-gap analysis output. Columns from gap_analyses."""

    student_id: int
    target_role: Optional[str] = None
    gap_score: Optional[float] = None
    matched_skills: Optional[list[str]] = None
    missing_skills: Optional[list[str]] = None
    analyzed_at: Optional[datetime] = None

    model_config = ConfigDict(extra="ignore")


class CandidateShowcase(BaseModel):
    """Showcase-facing view of a student. Composition of StudentProfile +
    top-5 skills + latest gap match. Shape returned by
    showcase_api.py `/api/showcase/candidates` list endpoint.

    The top_skills list is already truncated (5 per student) upstream.
    """

    id: int
    full_name: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    institution: Optional[str] = None
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None
    profile_completeness_score: Optional[float] = None
    track: Optional[str] = None
    availability_status: Optional[str] = None
    showcase_eligible: Optional[bool] = None
    showcase_active: Optional[bool] = None

    top_skills: list[str] = Field(default_factory=list)
    total_skill_count: int = 0
    latest_gap: Optional[GapAnalysis] = None

    model_config = ConfigDict(extra="ignore")
