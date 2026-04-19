"""Tests for wfdos_common.db — engine factory, session, tenant middleware (#22a)."""

from __future__ import annotations

import pytest
from sqlalchemy import text
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from wfdos_common.db import (
    TenantResolver,
    clear_tenant_registry,
    dispose_all,
    get_engine,
    register_tenant,
    registered_tenants,
    resolve_url,
    session_scope,
)


# ---------------------------------------------------------------------------
# Fixture: sqlite in-memory URL per tenant
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _clean_registries():
    """Each test starts with empty engine cache + tenant registry."""
    clear_tenant_registry()
    dispose_all()
    yield
    clear_tenant_registry()
    dispose_all()


@pytest.fixture
def tenant_a_url():
    return "sqlite:///:memory:"


@pytest.fixture
def tenant_b_url():
    return "sqlite:///:memory:"


# ---------------------------------------------------------------------------
# Engine cache
# ---------------------------------------------------------------------------

def test_engine_cached_by_tenant_and_mode(tenant_a_url):
    register_tenant("a", tenant_a_url)

    rw_1 = get_engine("a", read_only=False)
    rw_2 = get_engine("a", read_only=False)
    ro_1 = get_engine("a", read_only=True)

    assert rw_1 is rw_2, "Repeated get_engine with same args should return same Engine"
    assert rw_1 is not ro_1, "Read-only and read-write must be separate engines"


def test_different_tenants_get_different_engines(tenant_a_url, tenant_b_url):
    register_tenant("a", tenant_a_url)
    register_tenant("b", tenant_b_url)
    ea = get_engine("a")
    eb = get_engine("b")
    assert ea is not eb


def test_explicit_url_bypasses_registry():
    """When url= is passed, tenant_id only acts as a cache key."""
    direct = get_engine("test-cache-key", url="sqlite:///:memory:")
    # Second call with same cache key should return same engine object
    direct_2 = get_engine("test-cache-key", url="sqlite:///:memory:")
    assert direct is direct_2


def test_registered_tenants_lists_ids():
    register_tenant("a", "sqlite:///:memory:")
    register_tenant("b", "sqlite:///:memory:")
    assert registered_tenants() == ["a", "b"]


def test_resolve_url_prefers_registry(tenant_a_url):
    register_tenant("custom-tenant", tenant_a_url)
    assert resolve_url("custom-tenant") == tenant_a_url


def test_dispose_all_clears_cache(tenant_a_url):
    register_tenant("a", tenant_a_url)
    e1 = get_engine("a")
    dispose_all()
    e2 = get_engine("a")
    assert e1 is not e2, "dispose_all should force fresh engine on next call"


# ---------------------------------------------------------------------------
# Read-only enforcement
# ---------------------------------------------------------------------------

def test_read_only_engine_rejects_writes_on_sqlite():
    """sqlite PRAGMA query_only=1 makes writes raise. That's the dialect
    this test runs against; on Postgres it's default_transaction_read_only."""
    from sqlalchemy.exc import OperationalError

    register_tenant("ro-test", "sqlite:///:memory:")

    # Prime the write engine + create a table
    with session_scope("ro-test") as s:
        s.execute(text("CREATE TABLE t (id INTEGER, v TEXT)"))

    # Read-only engine is a different physical engine — it opens a fresh
    # in-memory sqlite DB that doesn't have `t`. That alone would fail,
    # so test writes against a file-backed DB where both engines share state.
    import tempfile
    import os

    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        clear_tenant_registry()
        dispose_all()
        register_tenant("file-ro", f"sqlite:///{path}")

        # Write engine: create + insert
        with session_scope("file-ro") as s:
            s.execute(text("CREATE TABLE t (id INTEGER, v TEXT)"))
            s.execute(text("INSERT INTO t VALUES (1, 'hello')"))

        # Read-only engine: can read
        with session_scope("file-ro", read_only=True) as s:
            row = s.execute(text("SELECT v FROM t WHERE id=1")).scalar()
            assert row == "hello"

        # Read-only engine: write must fail
        with pytest.raises(OperationalError):
            with session_scope("file-ro", read_only=True) as s:
                s.execute(text("INSERT INTO t VALUES (2, 'should-fail')"))
    finally:
        # Windows holds the sqlite file open until engines are disposed.
        dispose_all()
        if os.path.exists(path):
            os.remove(path)


# ---------------------------------------------------------------------------
# Session scope
# ---------------------------------------------------------------------------

def test_session_scope_commits_on_success(tenant_a_url):
    register_tenant("a", tenant_a_url)
    with session_scope("a") as s:
        s.execute(text("CREATE TABLE t (id INTEGER)"))
        s.execute(text("INSERT INTO t VALUES (1)"))

    # New session sees the committed data
    with session_scope("a") as s:
        count = s.execute(text("SELECT COUNT(*) FROM t")).scalar()
        assert count == 1


def test_session_scope_rolls_back_on_exception():
    import tempfile
    import os

    fd, path = tempfile.mkstemp(suffix=".sqlite")
    os.close(fd)
    try:
        register_tenant("rollback", f"sqlite:///{path}")
        with session_scope("rollback") as s:
            s.execute(text("CREATE TABLE t (id INTEGER)"))

        with pytest.raises(ValueError):
            with session_scope("rollback") as s:
                s.execute(text("INSERT INTO t VALUES (1)"))
                raise ValueError("boom")

        # INSERT was rolled back
        with session_scope("rollback") as s:
            count = s.execute(text("SELECT COUNT(*) FROM t")).scalar()
            assert count == 0
    finally:
        # Windows holds the sqlite file open until Engine.dispose() is called.
        # Dispose explicitly before os.remove to avoid WinError 32 on cleanup.
        dispose_all()
        if os.path.exists(path):
            os.remove(path)


# ---------------------------------------------------------------------------
# TenantResolver middleware
# ---------------------------------------------------------------------------

def _make_test_app(**mw_kwargs):
    async def read_tenant(request):
        return JSONResponse({"tenant": request.state.tenant_id})

    app = Starlette(routes=[Route("/tenant", read_tenant)])
    app.add_middleware(TenantResolver, **mw_kwargs)
    return app


def test_middleware_x_tenant_id_header_wins():
    app = _make_test_app(
        host_to_tenant={"platform.thewaifinder.com": "waifinder-flagship"},
        default_tenant_id="fallback",
    )
    client = TestClient(app)
    r = client.get("/tenant", headers={"X-Tenant-Id": "explicit-tenant"})
    assert r.status_code == 200
    assert r.json()["tenant"] == "explicit-tenant"


def test_middleware_falls_back_to_host_mapping():
    app = _make_test_app(
        host_to_tenant={"platform.thewaifinder.com": "waifinder-flagship"},
        default_tenant_id="fallback",
    )
    client = TestClient(app)
    r = client.get("/tenant", headers={"Host": "platform.thewaifinder.com"})
    assert r.status_code == 200
    assert r.json()["tenant"] == "waifinder-flagship"


def test_middleware_default_fallback_when_host_unknown():
    app = _make_test_app(
        host_to_tenant={"platform.thewaifinder.com": "waifinder-flagship"},
        default_tenant_id="fallback",
    )
    client = TestClient(app)
    r = client.get("/tenant", headers={"Host": "unknown-host.example.com"})
    assert r.status_code == 200
    assert r.json()["tenant"] == "fallback"


def test_middleware_callable_host_resolver():
    """host_to_tenant can be a callable so the lookup can hit a live DB
    (per #16 white-label runtime config)."""
    def resolver(host: str):
        return f"auto-{host.split('.')[0]}"

    app = _make_test_app(host_to_tenant=resolver, default_tenant_id="fallback")
    client = TestClient(app)
    r = client.get("/tenant", headers={"Host": "acme.clients.example.com"})
    assert r.json()["tenant"] == "auto-acme"


def test_middleware_host_header_ignores_port():
    app = _make_test_app(
        host_to_tenant={"platform.thewaifinder.com": "waifinder-flagship"},
        default_tenant_id="fallback",
    )
    client = TestClient(app)
    r = client.get("/tenant", headers={"Host": "platform.thewaifinder.com:8443"})
    assert r.json()["tenant"] == "waifinder-flagship"


def test_middleware_header_case_insensitive():
    """Starlette headers are case-insensitive; make sure our lookup is too."""
    app = _make_test_app(default_tenant_id="fallback")
    client = TestClient(app)
    # Middleware sets request.state.tenant_id using request.headers.get("x-tenant-id")
    # TestClient normalizes header keys; this verifies both cases work.
    r = client.get("/tenant", headers={"X-TENANT-ID": "caps-tenant"})
    assert r.json()["tenant"] == "caps-tenant"
