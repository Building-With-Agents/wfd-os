"""Tests for wfdos_common.models (#21)."""

import json
import sys

import pytest
from pydantic import ValidationError


# ---------------------------------------------------------------------------
# Core models
# ---------------------------------------------------------------------------

def test_error_detail_roundtrip():
    from wfdos_common.models import ErrorDetail
    err = ErrorDetail(code="not_found", message="Student not found", details={"id": 42})
    payload = err.model_dump()
    assert payload == {"code": "not_found", "message": "Student not found", "details": {"id": 42}}
    rebuilt = ErrorDetail.model_validate(payload)
    assert rebuilt == err


def test_error_detail_rejects_extra_fields():
    from wfdos_common.models import ErrorDetail
    with pytest.raises(ValidationError):
        ErrorDetail(code="x", message="y", bogus="nope")


def test_api_envelope_generic_success_and_error():
    from wfdos_common.models import APIEnvelope, ErrorDetail, StudentProfile

    success = APIEnvelope[StudentProfile](data=StudentProfile(id=1, full_name="Jane"))
    assert success.data.id == 1
    assert success.error is None

    failure = APIEnvelope[StudentProfile](error=ErrorDetail(code="bad", message="bad"))
    assert failure.data is None
    assert failure.error.code == "bad"


def test_audit_event_defaults():
    from wfdos_common.models import AuditEvent
    ev = AuditEvent(event_type="ingest.run.start")
    assert ev.event_type == "ingest.run.start"
    assert ev.attributes == {}
    # occurred_at is a datetime; just assert it's populated
    assert ev.occurred_at is not None


def test_tool_serialization_excludes_handler():
    from wfdos_common.models import Tool

    def search_jobs(q: str) -> list[str]:
        return [q]

    tool = Tool(
        name="search_jobs",
        description="Search job listings by keyword",
        parameters={"type": "object", "properties": {"q": {"type": "string"}}, "required": ["q"]},
        handler=search_jobs,
    )
    payload = tool.model_dump()
    # Handler must not leak into serialization
    assert "handler" not in payload
    assert payload["name"] == "search_jobs"
    assert payload["parameters"]["required"] == ["q"]


def test_tool_default_parameters_is_empty_object():
    from wfdos_common.models import Tool
    tool = Tool(name="no_args", description="takes nothing")
    assert tool.parameters == {"type": "object", "properties": {}, "required": []}


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------

def test_student_profile_accepts_observed_columns():
    from wfdos_common.models import StudentProfile

    # Simulate a psycopg2-style row from showcase_api's SELECT
    row = {
        "id": 1,
        "full_name": "Jane Doe",
        "city": "Seattle",
        "state": "WA",
        "institution": "UW",
        "degree": "BS",
        "field_of_study": "CS",
        "graduation_year": 2024,
        "profile_completeness_score": 0.85,
        "parse_confidence_score": 0.92,
        "pipeline_status": "intake",
        "track": "ojt",
        "availability_status": "seeking",
        "showcase_eligible": True,
        "showcase_active": False,
    }
    student = StudentProfile.model_validate(row)
    assert student.full_name == "Jane Doe"
    assert student.showcase_eligible is True


def test_student_profile_ignores_unknown_columns():
    from wfdos_common.models import StudentProfile
    # Extra columns in the cursor row must not blow up validation (we
    # set extra='ignore' deliberately — schema still drifts #22 finalizes).
    student = StudentProfile.model_validate({"id": 1, "unknown_column": 42})
    assert student.id == 1


def test_candidate_showcase_composes_gap_and_skills():
    from wfdos_common.models import CandidateShowcase, GapAnalysis

    c = CandidateShowcase(
        id=1,
        full_name="Jane",
        top_skills=["python", "sql", "react"],
        total_skill_count=12,
        latest_gap=GapAnalysis(student_id=1, target_role="data-engineer", gap_score=0.72),
    )
    payload = c.model_dump()
    assert payload["top_skills"] == ["python", "sql", "react"]
    assert payload["latest_gap"]["gap_score"] == 0.72


def test_skill_embedding_vector_is_string_or_none():
    from wfdos_common.models import Skill
    s1 = Skill(skill_name="Python")
    assert s1.embedding_vector is None
    s2 = Skill(skill_name="Python", embedding_vector="[0.1, 0.2]")
    assert s2.embedding_vector == "[0.1, 0.2]"


# ---------------------------------------------------------------------------
# Scoping dataclasses (moved from agents/scoping/models.py)
# ---------------------------------------------------------------------------

def test_scoping_request_from_webhook_preserves_pre_migration_shape():
    from wfdos_common.models.scoping import ScopingRequest

    req = ScopingRequest.from_webhook({
        "contact": {
            "first_name": "Jane",
            "last_name": "Doe",
            "title": "CTO",
            "email": "jane@acme.com",
        },
        "organization": {
            "name": "Acme Corp",
            "industry": "tech",
        },
        "notes": "urgent",
    })
    assert req.contact.full_name == "Jane Doe"
    assert req.contact.title == "CTO"
    assert req.organization.safe_name == "AcmeCorp"
    assert req.notes == "urgent"


def test_scoping_request_handles_missing_fields_same_as_master():
    """The Apollo webhook sometimes sends empty payloads. The from_webhook
    classmethod is tolerant (empty strings for missing fields). A Pydantic
    conversion would break this; keeping dataclasses preserves the contract.
    """
    from wfdos_common.models.scoping import ScopingRequest

    req = ScopingRequest.from_webhook({})
    assert req.contact.first_name == ""
    assert req.organization.name == ""
    assert req.notes == ""


def test_organization_safe_name_stripping():
    from wfdos_common.models.scoping import Organization
    assert Organization(name="Acme Corp").safe_name == "AcmeCorp"
    assert Organization(name="data-bridge systems").safe_name == "DataBridgeSystems"
    assert Organization(name="  ").safe_name == ""


# ---------------------------------------------------------------------------
# Shim + circular-import guards
# ---------------------------------------------------------------------------

def test_scoping_shim_identity():
    """agents.scoping.models re-exports must resolve to the same classes as
    the canonical location so existing callers continue to work unchanged.
    """
    from agents.scoping.models import (
        Contact as ShimContact,
        Organization as ShimOrg,
        ScopingRequest as ShimSR,
        ResearchResult as ShimRR,
        ScopingAnswer as ShimSA,
        ScopingAnalysis as ShimAnalysis,
    )
    from wfdos_common.models.scoping import (
        Contact, Organization, ScopingRequest,
        ResearchResult, ScopingAnswer, ScopingAnalysis,
    )
    assert ShimContact is Contact
    assert ShimOrg is Organization
    assert ShimSR is ScopingRequest
    assert ShimRR is ResearchResult
    assert ShimSA is ScopingAnswer
    assert ShimAnalysis is ScopingAnalysis


def test_graph_sharepoint_no_longer_pulls_in_agents_scoping():
    """The #17 blocker: agents/graph/sharepoint.py imported ScopingRequest
    from agents.scoping.models, creating a graph -> scoping circular
    coupling that blocked clean packaging. After #21 the canonical model
    lives in wfdos_common.models.scoping; importing sharepoint must not
    drag agents.scoping into the process.
    """
    # Clear caches to force fresh resolution
    for m in list(sys.modules.keys()):
        if m.startswith(("agents.scoping", "wfdos_common.graph", "wfdos_common.models")):
            del sys.modules[m]

    import wfdos_common.graph.sharepoint  # noqa: F401

    loaded_scoping = [m for m in sys.modules if m.startswith("agents.scoping")]
    assert loaded_scoping == [], (
        f"agents.scoping still transitively loaded: {loaded_scoping}"
    )
