"""Tests for Microsoft Graph integration scaffolding.

These verify imports, OAuth URL construction, and EvidenceItem shape — they
do NOT call out to real Microsoft endpoints. Integration tests against the
real Graph API need fixture credentials and live in a separate suite.
"""

from __future__ import annotations

from datetime import date

from grant_compliance.integrations.msgraph import build_authorize_url
from grant_compliance.integrations.msgraph.evidence import (
    EvidenceBundle,
    EvidenceItem,
    _parse_dt,
)


def test_authorize_url_includes_required_params(monkeypatch):
    monkeypatch.setenv("MSGRAPH_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("MSGRAPH_TENANT_ID", "test-tenant")
    monkeypatch.setenv("MSGRAPH_REDIRECT_URI", "http://localhost:8000/msgraph/callback")
    # Reset the lru_cache on get_settings
    from grant_compliance.config import get_settings
    get_settings.cache_clear()

    url, state = build_authorize_url()
    assert "client_id=test-client-id" in url
    assert "test-tenant" in url
    assert "redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fmsgraph%2Fcallback" in url
    assert "offline_access" in url
    assert "Mail.Read" in url
    assert state and len(state) > 16


def test_authorize_url_state_is_unique():
    _, s1 = build_authorize_url()
    _, s2 = build_authorize_url()
    assert s1 != s2


def test_evidence_item_round_trip():
    item = EvidenceItem(
        source="teams",
        item_type="message",
        identifier="abc123",
        title="Re: HRSA grant Q3 reporting",
        snippet="We need to align on the indirect rate before submission.",
        url="https://teams.example.com/abc",
        metadata={"from": "alex@example.org"},
    )
    assert item.source == "teams"
    assert item.metadata["from"] == "alex@example.org"


def test_evidence_bundle_starts_empty():
    bundle = EvidenceBundle(
        grant_id="grant-1", period_start=date(2025, 1, 1), period_end=date(2025, 12, 31)
    )
    assert bundle.items == []
    assert bundle.collected_at is not None


def test_parse_dt_handles_z_suffix():
    dt = _parse_dt("2025-06-15T14:30:00Z")
    assert dt is not None
    assert dt.year == 2025
    assert dt.month == 6


def test_parse_dt_handles_none_and_garbage():
    assert _parse_dt(None) is None
    assert _parse_dt("not-a-date") is None
