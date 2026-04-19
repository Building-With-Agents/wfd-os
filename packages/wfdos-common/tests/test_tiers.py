"""Tests for wfdos_common.auth.tiers — route tier decorators (#25)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from wfdos_common.auth import (
    Session,
    SessionMiddleware,
    TIER_LLM_GATED,
    TIER_PUBLIC,
    TIER_READ_ONLY,
    audit_tier_tags,
    get_tier,
    issue_session,
    llm_gated,
    public,
    read_only,
)
from wfdos_common.errors import install_error_handlers

_KEY = "tier-test-key"


# ---------------------------------------------------------------------------
# Tag attachment / introspection
# ---------------------------------------------------------------------------


def test_public_tags_function():
    @public
    def handler():
        return {"ok": True}

    tag = get_tier(handler)
    assert tag is not None
    assert tag.tier == TIER_PUBLIC
    assert tag.roles == ()


def test_read_only_defaults():
    @read_only()
    def handler(user):  # user param present to keep wrapper shape realistic
        return {"ok": True}

    tag = get_tier(handler)
    assert tag is not None
    assert tag.tier == TIER_READ_ONLY
    assert set(tag.roles) == {"student", "staff", "admin"}


def test_read_only_custom_roles():
    @read_only(roles=("admin",))
    def handler(user):
        return {"ok": True}

    assert get_tier(handler).roles == ("admin",)


def test_llm_gated_defaults_to_staff_admin():
    @llm_gated()
    def handler(user):
        return {"ok": True}

    tag = get_tier(handler)
    assert tag.tier == TIER_LLM_GATED
    assert set(tag.roles) == {"staff", "admin"}


def test_llm_gated_rate_limit_captured():
    @llm_gated(rate_limit_per_hour=25)
    def handler(user):
        return {"ok": True}

    assert get_tier(handler).rate_limit_per_hour == 25


# ---------------------------------------------------------------------------
# Runtime enforcement (read_only + llm_gated)
# ---------------------------------------------------------------------------


def _build_app(*, has_llm_creds: bool = True) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        SessionMiddleware,
        secret_key=_KEY,
        cookie_name="wfdos_session",
        max_age_seconds=3600,
    )
    install_error_handlers(app)

    @app.get("/api/public")
    @public
    def get_public():
        return {"tier": "public"}

    @app.get("/api/me")
    @read_only(roles=("student", "staff", "admin"))
    def get_me(request: Request):  # noqa: ARG001 — request picked up by wrapper
        return {"tier": "read_only"}

    @app.get("/api/admin-report")
    @llm_gated(roles=("admin",))
    def admin_report(request: Request):  # noqa: ARG001
        return {"tier": "llm_gated"}

    return app


def test_public_tier_allows_unauth():
    app = _build_app()
    client = TestClient(app)
    r = client.get("/api/public")
    assert r.status_code == 200
    assert r.json() == {"tier": "public"}


def test_read_only_rejects_unauth_with_401():
    app = _build_app()
    client = TestClient(app)
    r = client.get("/api/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_read_only_accepts_valid_cookie():
    app = _build_app()
    client = TestClient(app)
    token = issue_session(Session(email="s@example.com", role="student"), secret_key=_KEY)
    client.cookies.set("wfdos_session", token)
    r = client.get("/api/me")
    assert r.status_code == 200
    assert r.json() == {"tier": "read_only"}


def test_llm_gated_rejects_wrong_role():
    app = _build_app()
    client = TestClient(app)
    token = issue_session(Session(email="s@example.com", role="student"), secret_key=_KEY)
    client.cookies.set("wfdos_session", token)
    r = client.get("/api/admin-report")
    assert r.status_code == 403


def test_llm_gated_admin_role_passes(monkeypatch):
    # Make sure LLM creds appear present so the tier-2 gate doesn't 503.
    from wfdos_common.config import settings

    monkeypatch.setattr(settings.azure_openai, "key", "fake-key")
    monkeypatch.setattr(settings.azure_openai, "endpoint", "https://example.openai.azure.com/")
    monkeypatch.setattr(settings.llm, "anthropic_api_key", "")
    monkeypatch.setattr(settings.llm, "gemini_api_key", "")

    app = _build_app()
    client = TestClient(app)
    token = issue_session(Session(email="admin@example.com", role="admin"), secret_key=_KEY)
    client.cookies.set("wfdos_session", token)
    r = client.get("/api/admin-report")
    assert r.status_code == 200


def test_llm_gated_returns_503_when_no_llm_creds(monkeypatch):
    """Stripped-.env deploy: tier-2 must 503, not 500."""
    from wfdos_common.config import settings

    monkeypatch.setattr(settings.azure_openai, "key", "")
    monkeypatch.setattr(settings.azure_openai, "endpoint", "")
    monkeypatch.setattr(settings.llm, "anthropic_api_key", "")
    monkeypatch.setattr(settings.llm, "gemini_api_key", "")

    app = _build_app()
    client = TestClient(app)
    token = issue_session(Session(email="admin@example.com", role="admin"), secret_key=_KEY)
    client.cookies.set("wfdos_session", token)
    r = client.get("/api/admin-report")
    assert r.status_code == 503
    body = r.json()
    assert body["error"]["code"] == "service_unavailable"
    assert body["error"]["details"]["tier"] == "llm_gated"


# ---------------------------------------------------------------------------
# audit_tier_tags
# ---------------------------------------------------------------------------


def test_audit_tier_tags_buckets_routes():
    app = _build_app()
    audit = audit_tier_tags(app.routes)
    assert "/api/public" in audit[TIER_PUBLIC]
    assert "/api/me" in audit[TIER_READ_ONLY]
    assert "/api/admin-report" in audit[TIER_LLM_GATED]


def test_audit_tier_tags_detects_untagged_routes():
    app = FastAPI()

    @app.get("/untagged")
    def untagged():
        return {"tagged": False}

    audit = audit_tier_tags(app.routes)
    assert "/untagged" in audit["untagged"]
