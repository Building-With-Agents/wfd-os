"""Tests for wfdos_common.logging (#23)."""

from __future__ import annotations

import io
import json
import logging as stdlib_logging
import sys
from contextlib import redirect_stdout

import pytest
import structlog
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from wfdos_common.logging import (
    RequestContextMiddleware,
    bind_context,
    configure,
    current_context,
    get_logger,
    reset_configured,
    set_request_id,
    set_tenant_id,
)


@pytest.fixture(autouse=True)
def _reset_structlog_between_tests():
    reset_configured()
    # Clear context vars so tests don't leak into each other
    set_tenant_id(None)
    set_request_id(None)
    yield
    reset_configured()
    set_tenant_id(None)
    set_request_id(None)


# ---------------------------------------------------------------------------
# configure()
# ---------------------------------------------------------------------------

def test_configure_sets_service_name():
    configure(service_name="consulting-api")
    ctx = current_context()
    assert ctx["service_name"] == "consulting-api"


def test_configure_json_format_emits_parseable_json(capsys):
    configure(service_name="json-test", log_format="json")
    log = get_logger(__name__)

    log.info("event.happened", widget_id=42, extra="foo")

    out = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(out)
    assert payload["event"] == "event.happened"
    assert payload["widget_id"] == 42
    assert payload["extra"] == "foo"
    assert payload["service_name"] == "json-test"
    assert payload["level"] == "info"
    assert "timestamp" in payload


def test_configure_console_format_emits_human_readable(capsys):
    configure(service_name="console-test", log_format="console")
    log = get_logger(__name__)

    log.info("readable.event", key="value")

    out = capsys.readouterr().out
    assert "readable.event" in out
    assert "console-test" in out
    assert "key" in out and "value" in out


def test_configure_is_idempotent():
    configure(service_name="first")
    configure(service_name="second")
    # service_name updates on each call, but processor registration
    # doesn't re-run (would throw if it did on some structlog versions).
    assert current_context()["service_name"] == "second"


def test_configure_respects_log_level_env(monkeypatch, capsys):
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    configure(service_name="level-test")
    log = get_logger(__name__)
    log.info("filtered_out")
    log.warning("kept")
    out = capsys.readouterr().out
    assert "filtered_out" not in out
    assert "kept" in out


# ---------------------------------------------------------------------------
# ContextVars
# ---------------------------------------------------------------------------

def test_context_vars_default_to_none():
    ctx = current_context()
    assert ctx["tenant_id"] is None
    assert ctx["user_id"] is None
    assert ctx["request_id"] is None


def test_set_tenant_id_updates_context():
    set_tenant_id("acme-co")
    assert current_context()["tenant_id"] == "acme-co"


def test_bind_context_manager_scopes_values():
    assert current_context()["tenant_id"] is None
    with bind_context(tenant_id="scoped", request_id="abc"):
        ctx = current_context()
        assert ctx["tenant_id"] == "scoped"
        assert ctx["request_id"] == "abc"
    # ContextVars reset after the with block
    ctx_after = current_context()
    assert ctx_after["tenant_id"] is None
    assert ctx_after["request_id"] is None


def test_bind_context_nested_restores_outer():
    with bind_context(tenant_id="outer"):
        assert current_context()["tenant_id"] == "outer"
        with bind_context(tenant_id="inner"):
            assert current_context()["tenant_id"] == "inner"
        assert current_context()["tenant_id"] == "outer"
    assert current_context()["tenant_id"] is None


def test_context_vars_appear_in_json_log(capsys):
    configure(service_name="ctx-json", log_format="json")
    log = get_logger(__name__)

    with bind_context(tenant_id="t1", request_id="r1", user_id="u1"):
        log.info("with.context")

    out = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(out)
    assert payload["tenant_id"] == "t1"
    assert payload["request_id"] == "r1"
    assert payload["user_id"] == "u1"
    assert payload["service_name"] == "ctx-json"


def test_explicit_event_kwarg_wins_over_contextvar(capsys):
    """If a caller passes tenant_id=... to the log call, that beats the
    ContextVar value (setdefault semantics)."""
    configure(service_name="override", log_format="json")
    log = get_logger(__name__)

    with bind_context(tenant_id="from-cv"):
        log.info("explicit.beats.cv", tenant_id="from-kwarg")

    out = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(out)
    assert payload["tenant_id"] == "from-kwarg"


# ---------------------------------------------------------------------------
# RequestContextMiddleware
# ---------------------------------------------------------------------------

def _make_app():
    async def read_ctx(request):
        # Return what the middleware pinned so tests can assert.
        return JSONResponse({
            "request_id": request.headers.get("x-request-id"),
            "tenant_id": getattr(request.state, "tenant_id", None),
            "ctx": current_context(),
        })

    app = Starlette(routes=[Route("/ctx", read_ctx)])
    app.add_middleware(RequestContextMiddleware)
    return app


def test_middleware_generates_request_id_when_header_missing():
    app = _make_app()
    client = TestClient(app)
    r = client.get("/ctx")
    assert r.status_code == 200
    body = r.json()
    assert body["ctx"]["request_id"] is not None
    # UUIDv4 has 36 chars incl. hyphens
    assert len(body["ctx"]["request_id"]) == 36
    # Response echoes the id back so the client can correlate
    assert r.headers["X-Request-Id"] == body["ctx"]["request_id"]


def test_middleware_honors_incoming_request_id_header():
    app = _make_app()
    client = TestClient(app)
    r = client.get("/ctx", headers={"X-Request-Id": "rid-123"})
    assert r.json()["ctx"]["request_id"] == "rid-123"
    assert r.headers["X-Request-Id"] == "rid-123"


def test_middleware_resets_contextvars_after_response():
    """ContextVars should be None again after the request completes —
    otherwise a later request in the same worker leaks state."""
    app = _make_app()
    client = TestClient(app)
    client.get("/ctx", headers={"X-Request-Id": "first"})
    # Directly inspect context in the test process; after the response
    # the middleware reset should have fired.
    assert current_context()["request_id"] is None


def test_middleware_reads_tenant_from_request_state():
    """When a prior middleware (TenantResolver) set request.state.tenant_id,
    RequestContextMiddleware picks it up into the ContextVar so logs from
    the handler get tenant_id for free.
    """
    from starlette.middleware.base import BaseHTTPMiddleware

    class _StubTenantSetter(BaseHTTPMiddleware):
        async def dispatch(self, request, call_next):
            request.state.tenant_id = "from-upstream-middleware"
            return await call_next(request)

    async def handler(request):
        return JSONResponse({"ctx": current_context()})

    app = Starlette(routes=[Route("/t", handler)])
    # Starlette runs last-added first: RequestContextMiddleware runs AFTER
    # the stub sets request.state.tenant_id.
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(_StubTenantSetter)

    r = TestClient(app).get("/t")
    assert r.status_code == 200
    assert r.json()["ctx"]["tenant_id"] == "from-upstream-middleware"
