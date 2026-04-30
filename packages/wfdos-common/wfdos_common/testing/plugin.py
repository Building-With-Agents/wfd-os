"""Pytest fixture definitions. See wfdos_common.testing.__init__ for overview."""

from __future__ import annotations

from typing import Any, Callable, Optional
from unittest.mock import MagicMock

import pytest
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.testclient import TestClient


# ---------------------------------------------------------------------------
# Tenancy
# ---------------------------------------------------------------------------

@pytest.fixture
def wfdos_tenant_id() -> str:
    """Default tenant used by db / auth fixtures. Override in service conftest
    if a test needs a different value.
    """
    return "test-tenant"


# ---------------------------------------------------------------------------
# Database — sqlite in-memory
# ---------------------------------------------------------------------------

@pytest.fixture
def wfdos_db_engine(wfdos_tenant_id):
    """SQLAlchemy Engine backed by sqlite in-memory, registered as the
    given tenant. The engine cache + tenant registry are cleared before
    AND after each test so tests don't leak state to each other.
    """
    from wfdos_common.db import (
        clear_tenant_registry,
        dispose_all,
        get_engine,
        register_tenant,
    )

    clear_tenant_registry()
    dispose_all()
    register_tenant(wfdos_tenant_id, "sqlite:///:memory:")
    engine = get_engine(wfdos_tenant_id)
    try:
        yield engine
    finally:
        dispose_all()
        clear_tenant_registry()


@pytest.fixture
def wfdos_db_session(wfdos_db_engine, wfdos_tenant_id):
    """Session bound to the in-memory engine. Rolled back at teardown
    (actually the engine is disposed, which is stronger than rollback
    for sqlite in-memory — the whole DB vanishes).
    """
    from wfdos_common.db import session_scope

    with session_scope(wfdos_tenant_id) as session:
        yield session


# ---------------------------------------------------------------------------
# LLM stub — patches wfdos_common.llm.complete
# ---------------------------------------------------------------------------

class _LLMStub:
    """Captures calls to complete() and returns a canned reply.

    Attributes after a test run:
      .calls          list[dict]  — every call's kwargs
      .last_call      dict        — the most recent call's kwargs
      .call_count     int
      .reply          str         — assign to change what complete() returns

    Change the reply mid-test::

        wfdos_llm_stub.reply = "different response"

    Or plug in a function for per-call-dynamic behavior::

        wfdos_llm_stub.reply_fn = lambda messages, **kw: f"echo: {messages[-1]['content']}"
    """

    def __init__(self, reply: str = "stub reply"):
        self.reply = reply
        self.reply_fn: Optional[Callable[..., str]] = None
        self.calls: list[dict[str, Any]] = []

    @property
    def last_call(self) -> Optional[dict[str, Any]]:
        return self.calls[-1] if self.calls else None

    @property
    def call_count(self) -> int:
        return len(self.calls)

    def __call__(self, messages, **kwargs):
        self.calls.append({"messages": messages, **kwargs})
        if self.reply_fn is not None:
            return self.reply_fn(messages, **kwargs)
        return self.reply


@pytest.fixture
def wfdos_llm_stub(monkeypatch):
    """Monkey-patches `wfdos_common.llm.complete` with a controllable stub.

    The stub auto-records every call for assertion. Zero real LLM cost.
    """
    stub = _LLMStub()
    # Patch both the module-level function and the already-imported name
    # in wfdos_common.llm (set during module init).
    import wfdos_common.llm
    import wfdos_common.llm.adapter
    monkeypatch.setattr(wfdos_common.llm, "complete", stub)
    monkeypatch.setattr(wfdos_common.llm.adapter, "complete", stub)
    yield stub


# ---------------------------------------------------------------------------
# Graph stub — patches Microsoft Graph client + email
# ---------------------------------------------------------------------------

class _GraphStub:
    """Collects calls to email + Graph operations so tests can assert on
    what would have been sent without actually hitting Azure.
    """

    def __init__(self):
        self.emails_sent: list[dict[str, Any]] = []
        self.sharepoint_uploads: list[dict[str, Any]] = []
        self.teams_messages: list[dict[str, Any]] = []

    def send_email(self, to, subject, body, html=True, **extra):
        payload = {"to": to, "subject": subject, "body": body, "html": html, **extra}
        self.emails_sent.append(payload)
        return {
            "sent": True,
            "reason": "ok (stubbed)",
            "to": to,
            "subject": subject,
            "status_code": 202,
            "sender": extra.get("sender", "stub@example.com"),
        }

    def notify_internal(self, subject, body):
        return self.send_email("internal@example.com", subject, body)

    @property
    def last_email(self):
        return self.emails_sent[-1] if self.emails_sent else None


@pytest.fixture
def wfdos_graph_stub(monkeypatch):
    """Monkey-patches `wfdos_common.email.send_email` and `notify_internal`
    with capture-only stubs. Extend with more graph patches as the Agent
    ABC + other services need them (#26).
    """
    stub = _GraphStub()
    import wfdos_common.email
    monkeypatch.setattr(wfdos_common.email, "send_email", stub.send_email)
    monkeypatch.setattr(wfdos_common.email, "notify_internal", stub.notify_internal)
    yield stub


# ---------------------------------------------------------------------------
# Auth client — FastAPI TestClient with a fake session cookie
# ---------------------------------------------------------------------------

def _make_auth_client(app, role: str = "staff", user_id: str = "test-user"):
    """Return a TestClient with an X-Test-User-* header baked in.

    STUB until #24 magic-link auth lands: today this just sends marker
    headers that a future `SessionMiddleware` / `require_role` can read.
    After #24, this fixture will sign real session cookies with the
    service's secret.
    """
    client = TestClient(app)
    # Default headers on every request from this client
    client.headers.update({
        "X-Test-User-Id": user_id,
        "X-Test-User-Role": role,
    })
    return client


@pytest.fixture
def wfdos_auth_client():
    """Factory fixture — call it with your service's FastAPI app + role::

        def test_protected(wfdos_auth_client):
            from agents.portal.consulting_api import app
            client = wfdos_auth_client(app, role="staff")
            r = client.get("/api/consulting/pipeline")
            assert r.status_code == 200

    Role values are informational today (X-Test-User-Role header).
    After #24, the role is baked into a signed session cookie.
    """
    return _make_auth_client


# ---------------------------------------------------------------------------
# Logging context cleanup
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_wfdos_logging():
    """ContextVars from wfdos_common.logging can leak across tests on a
    shared worker. Reset before AND after each test.

    autouse=True so every test in a consumer service gets this for free
    when the plugin is loaded.
    """
    from wfdos_common.logging import (
        reset_configured,
        set_request_id,
        set_tenant_id,
        set_user_id,
    )

    set_tenant_id(None)
    set_user_id(None)
    set_request_id(None)
    reset_configured()
    yield
    set_tenant_id(None)
    set_user_id(None)
    set_request_id(None)
    reset_configured()


__all__ = [
    "wfdos_tenant_id",
    "wfdos_db_engine",
    "wfdos_db_session",
    "wfdos_llm_stub",
    "wfdos_graph_stub",
    "wfdos_auth_client",
    "reset_wfdos_logging",
]
