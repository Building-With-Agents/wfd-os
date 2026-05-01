"""Coverage for the FastAPI cockpit service.

The plan called for auth-wiring smoke and core endpoint shapes. This
file uses TestClient against the real `app` (which loads the K8341
fixtures via `default_source()` at import time, so each call is fast
after the first).

The auth surface follows the wfdos_common pattern: SessionMiddleware
parses the cookie into request.state.user; the @read_only / @llm_gated
decorators check that. Tests inject a session by setting
`request.state.user` via a dependency override — that mirrors how the
laborpulse smoke harness does it without requiring a real magic-link
round-trip.
"""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from wfdos_common.auth.tokens import Session, issue_session
from wfdos_common.config import settings


@pytest.fixture
def app():
    # Imported inside the fixture so the module-load side effects
    # (Excel parse + dotenv read) only happen when the test runs.
    from agents.finance.cockpit_api import app as cockpit_app
    return cockpit_app


@pytest.fixture
def client(app):
    return TestClient(app)


def _staff_session() -> Session:
    # Session has three fields; the tier decorators only check `role`,
    # TenantResolutionMiddleware sets tenant_id from the host map.
    return Session(
        email="ritu@computingforall.org",
        role="staff",
        tenant_id="waifinder-flagship",
    )


@pytest.fixture
def auth_client(app):
    """TestClient that carries a real wfdos_session cookie issued by
    issue_session(). This exercises the actual SessionMiddleware path
    rather than monkeypatching the auth wrapper, so a regression in
    cookie parsing would still be caught."""
    cookie = issue_session(_staff_session(), secret_key=settings.auth.secret_key)
    c = TestClient(app)
    c.cookies.set(settings.auth.cookie_name, cookie)
    return c


# ---------------------------------------------------------------------------
# Public + auth wiring
# ---------------------------------------------------------------------------


class TestAuthWiring:
    def test_health_is_public(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["service"] == "cockpit_api"

    def test_status_requires_auth(self, client):
        r = client.get("/cockpit/status")
        assert r.status_code == 401
        envelope = r.json()
        # #29 envelope shape: {"data": null, "error": {"code", "message", ...}, "meta": null}
        assert envelope["error"]["code"] == "unauthorized"
        assert envelope["data"] is None

    def test_hero_requires_auth(self, client):
        assert client.get("/cockpit/hero").status_code == 401

    def test_decisions_requires_auth(self, client):
        assert client.get("/cockpit/decisions").status_code == 401

    def test_activity_requires_auth(self, client):
        assert client.get("/cockpit/activity").status_code == 401

    def test_drill_requires_auth(self, client):
        assert client.get("/cockpit/drills/backbone").status_code == 401

    def test_refresh_requires_auth(self, client):
        assert client.post("/cockpit/refresh").status_code == 401


# ---------------------------------------------------------------------------
# Endpoint shape (with injected auth)
# ---------------------------------------------------------------------------


class TestCockpitShapes:
    def test_status_shape(self, auth_client):
        r = auth_client.get("/cockpit/status")
        assert r.status_code == 200
        body = r.json()
        for k in ("as_of", "months_remaining", "days_remaining", "tab_counts"):
            assert k in body, f"missing key: {k}"
        # tab_counts populated for every cockpit tab the badge renders.
        for tab in ("decisions", "providers", "transactions", "reporting", "audit"):
            assert tab in body["tab_counts"]

    def test_hero_returns_four_cells(self, auth_client):
        r = auth_client.get("/cockpit/hero")
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) == {"backbone", "placements", "cash", "flags"}
        for cell in body.values():
            assert "label" in cell
            assert "value" in cell
            assert "drill_key" in cell

    def test_decisions_sorts_by_priority(self, auth_client):
        r = auth_client.get("/cockpit/decisions")
        assert r.status_code == 200
        body = r.json()
        assert body["sorted_by"] == "priority"
        assert body["total"] == len(body["items"])
        # HIGH-priority items rank ahead of MEDIUM in the list order
        # (decisions are pre-sorted in cockpit_data, just rendered here).
        priorities = [item["priority"] for item in body["items"]]
        if "HIGH" in priorities and "MEDIUM" in priorities:
            assert priorities.index("HIGH") < priorities.index("MEDIUM")

    def test_drill_404_for_unknown_key(self, auth_client):
        r = auth_client.get("/cockpit/drills/nonsense_key_does_not_exist")
        # Custom HTTPException(404) flows through the structured envelope.
        assert r.status_code == 404
