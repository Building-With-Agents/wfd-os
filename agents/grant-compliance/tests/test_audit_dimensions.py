"""Tests for the canonical audit-dimension metadata module.

These tests pin the dimension set that the Audit Readiness tab relies on.
If a dimension is added, removed, or renamed, a test here will fail — that
is intentional, because changing the dimension set is a coordinated change
across `_tab_audit`, `build_drills()`, and any future ownership/assignment
wiring.
"""

from __future__ import annotations

from grant_compliance.compliance.audit_dimensions import (
    DIMENSIONS,
    AuditDimension,
    Tone,
    dimension_ids,
    get_dimension,
)


EXPECTED_IDS = (
    "allowable_costs",
    "transaction_documentation",
    "time_effort",
    "procurement",
    "subrecipient_monitoring",
    "performance_reporting",
)


def test_dimension_set_is_exactly_the_six_expected():
    assert dimension_ids() == EXPECTED_IDS


def test_dimension_count_is_six():
    assert len(DIMENSIONS) == 6


def test_ids_are_unique():
    ids = [d.id for d in DIMENSIONS]
    assert len(set(ids)) == len(ids)


def test_every_dimension_has_at_least_one_cfr_citation():
    for d in DIMENSIONS:
        assert len(d.cfr_citations) >= 1, f"{d.id} has no CFR citations"
        for c in d.cfr_citations:
            assert c.startswith("§"), f"{d.id}: citation {c!r} should start with §"


def test_every_dimension_has_nonempty_required_fields():
    for d in DIMENSIONS:
        assert d.title, f"{d.id} missing title"
        assert d.what_auditors_look_for, f"{d.id} missing what_auditors_look_for"
        assert d.compliance_supplement_area, f"{d.id} missing compliance_supplement_area"
        assert d.owner_role, f"{d.id} missing owner_role"


def test_default_tone_is_valid_literal():
    valid_tones = {"good", "watch", "critical", "neutral"}
    for d in DIMENSIONS:
        assert d.default_tone in valid_tones, (
            f"{d.id} default_tone {d.default_tone!r} not in {valid_tones}"
        )


def test_get_dimension_returns_known_dimension():
    d = get_dimension("allowable_costs")
    assert d is not None
    assert d.title == "Allowable costs"
    assert "§§200.420–200.476" in d.cfr_citations


def test_get_dimension_returns_none_for_unknown_id():
    assert get_dimension("not_a_real_dimension") is None


def test_time_effort_cites_200_430_i():
    d = get_dimension("time_effort")
    assert d is not None
    assert d.cfr_citations == ("§200.430(i)",)


def test_subrecipient_monitoring_cites_200_331_333():
    d = get_dimension("subrecipient_monitoring")
    assert d is not None
    assert "§§200.331–200.333" in d.cfr_citations


def test_dimensions_are_immutable():
    # Frozen dataclass should reject attribute assignment.
    d = DIMENSIONS[0]
    try:
        d.title = "changed"  # type: ignore[misc]
    except Exception:
        return
    raise AssertionError("AuditDimension should be frozen")


def test_owner_role_uses_role_not_person_name():
    # The role abstraction is the contract; person names live elsewhere
    # and will be injected by a future ownership-assignment mechanism.
    person_names = {"Krista", "Ritu", "Bethany", "Gage"}
    for d in DIMENSIONS:
        assert d.owner_role not in person_names, (
            f"{d.id}: owner_role {d.owner_role!r} looks like a person name"
        )


def test_tone_type_alias_exported():
    # Exercises the Tone export so downstream code can use the same type.
    tone: Tone = "neutral"
    assert tone == "neutral"


def test_dimension_class_is_a_frozen_dataclass():
    # Defensive: confirm the class keeps the same shape as unallowable_costs.
    assert AuditDimension.__dataclass_params__.frozen is True  # type: ignore[attr-defined]
