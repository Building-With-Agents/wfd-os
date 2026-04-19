"""Tests for wfdos_common.testing — the shared fixtures plugin (#28).

These tests exercise the fixtures themselves (meta-tests) so future
regressions to the plugin are caught. Consumers just use the fixtures
directly from their own test files; they don't write tests like these.
"""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from sqlalchemy import text


# ---------------------------------------------------------------------------
# wfdos_tenant_id + wfdos_db_engine + wfdos_db_session
# ---------------------------------------------------------------------------

def test_tenant_id_default(wfdos_tenant_id):
    assert wfdos_tenant_id == "test-tenant"


def test_db_engine_is_sqlite_in_memory(wfdos_db_engine):
    assert wfdos_db_engine.dialect.name == "sqlite"


def test_db_session_roundtrip(wfdos_db_session):
    wfdos_db_session.execute(text("CREATE TABLE t (id INTEGER, v TEXT)"))
    wfdos_db_session.execute(text("INSERT INTO t VALUES (1, 'hello')"))
    row = wfdos_db_session.execute(text("SELECT v FROM t WHERE id=1")).scalar()
    assert row == "hello"


def test_db_fixtures_isolate_across_tests_part_a(wfdos_db_session):
    """Companion to ..._part_b: each test gets a fresh DB."""
    wfdos_db_session.execute(text("CREATE TABLE isolation (x INTEGER)"))
    wfdos_db_session.execute(text("INSERT INTO isolation VALUES (999)"))


def test_db_fixtures_isolate_across_tests_part_b(wfdos_db_session):
    """If isolation works, the table from part_a is gone."""
    result = wfdos_db_session.execute(
        text("SELECT name FROM sqlite_master WHERE type='table' AND name='isolation'")
    ).fetchone()
    assert result is None, "isolation table leaked from previous test"


# ---------------------------------------------------------------------------
# wfdos_llm_stub
# ---------------------------------------------------------------------------

def test_llm_stub_returns_canned_reply(wfdos_llm_stub):
    from wfdos_common.llm import complete

    out = complete([{"role": "user", "content": "hi"}], tier="default")
    assert out == "stub reply"


def test_llm_stub_captures_calls(wfdos_llm_stub):
    from wfdos_common.llm import complete

    complete([{"role": "user", "content": "one"}], tier="default", max_tokens=10)
    complete([{"role": "user", "content": "two"}], tier="synthesis")

    assert wfdos_llm_stub.call_count == 2
    assert wfdos_llm_stub.last_call["messages"][0]["content"] == "two"
    assert wfdos_llm_stub.calls[0]["max_tokens"] == 10


def test_llm_stub_supports_dynamic_reply_fn(wfdos_llm_stub):
    from wfdos_common.llm import complete

    wfdos_llm_stub.reply_fn = lambda messages, **kw: f"echo: {messages[-1]['content']}"
    out = complete([{"role": "user", "content": "foo"}])
    assert out == "echo: foo"


def test_llm_stub_reply_mutable(wfdos_llm_stub):
    from wfdos_common.llm import complete

    wfdos_llm_stub.reply = "first"
    assert complete([{"role": "user", "content": "x"}]) == "first"
    wfdos_llm_stub.reply = "second"
    assert complete([{"role": "user", "content": "x"}]) == "second"


# ---------------------------------------------------------------------------
# wfdos_graph_stub
# ---------------------------------------------------------------------------

def test_graph_stub_captures_email_send(wfdos_graph_stub):
    from wfdos_common.email import send_email

    result = send_email("to@example.com", "subj", "body", html=False)
    assert result["sent"] is True
    assert result["status_code"] == 202
    assert wfdos_graph_stub.last_email["to"] == "to@example.com"
    assert wfdos_graph_stub.last_email["subject"] == "subj"


def test_graph_stub_notify_internal(wfdos_graph_stub):
    from wfdos_common.email import notify_internal

    notify_internal("ping", "internal body")
    assert wfdos_graph_stub.last_email["to"] == "internal@example.com"
    assert wfdos_graph_stub.last_email["subject"] == "ping"


# ---------------------------------------------------------------------------
# wfdos_auth_client
# ---------------------------------------------------------------------------

def test_auth_client_sets_marker_headers(wfdos_auth_client):
    app = FastAPI()

    @app.get("/who")
    def who(request: Request):
        return {
            "role": request.headers.get("x-test-user-role"),
            "user_id": request.headers.get("x-test-user-id"),
        }

    client = wfdos_auth_client(app, role="admin", user_id="u-42")
    r = client.get("/who")
    assert r.status_code == 200
    assert r.json() == {"role": "admin", "user_id": "u-42"}


def test_auth_client_defaults_to_staff():
    from wfdos_common.testing.plugin import _make_auth_client

    app = FastAPI()

    @app.get("/r")
    def r(request: Request):
        return {"role": request.headers.get("x-test-user-role")}

    client = _make_auth_client(app)
    assert client.get("/r").json() == {"role": "staff"}


# ---------------------------------------------------------------------------
# reset_wfdos_logging autouse
# ---------------------------------------------------------------------------

def test_autouse_clears_contextvars_before_test():
    from wfdos_common.logging import current_context

    ctx = current_context()
    assert ctx["tenant_id"] is None
    assert ctx["user_id"] is None
    assert ctx["request_id"] is None
