"""Tests for wfdos_common.tenancy — white-label brand config + resolution (#16)."""

from __future__ import annotations

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from wfdos_common.tenancy import (
    BrandConfig,
    TenantResolutionMiddleware,
    all_brands,
    get_brand,
    register_brand,
    reset_brands,
    resolve_tenant,
)


@pytest.fixture(autouse=True)
def _reset():
    reset_brands()
    yield
    reset_brands()


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


def test_default_brands_include_flagship_and_borderplex():
    brands = all_brands()
    assert "waifinder-flagship" in brands
    assert "borderplex" in brands


def test_get_brand_known_returns_config():
    b = get_brand("waifinder-flagship")
    assert b.display_name == "Waifinder"
    assert b.portal_hostname == "platform.thewaifinder.com"


def test_get_brand_unknown_falls_back_to_flagship():
    b = get_brand("this-tenant-does-not-exist")
    assert b.tenant_id == "waifinder-flagship"


def test_register_brand_adds_to_registry_and_host_index():
    register_brand(
        BrandConfig(
            tenant_id="acme",
            display_name="Acme Workforce",
            logo_url="https://acme.example.com/logo.svg",
            primary_color="#111111",
            accent_color="#222222",
            email_from_name="Acme",
            email_from_address="hr@acme.example.com",
            portal_hostname="talent.acme.example.com",
        )
    )
    assert "acme" in all_brands()
    # Host resolution now picks it up.
    tid = resolve_tenant(host="talent.acme.example.com")
    assert tid == "acme"


# ---------------------------------------------------------------------------
# resolve_tenant
# ---------------------------------------------------------------------------


def test_x_tenant_id_header_wins():
    tid = resolve_tenant(x_tenant_id="borderplex", host="platform.thewaifinder.com")
    assert tid == "borderplex"


def test_host_header_resolves_tenant():
    tid = resolve_tenant(host="platform.thewaifinder.com")
    assert tid == "waifinder-flagship"


def test_host_with_port_still_resolves():
    tid = resolve_tenant(host="platform.thewaifinder.com:8443")
    assert tid == "waifinder-flagship"


def test_host_case_insensitive():
    tid = resolve_tenant(host="PLATFORM.THEWAIFINDER.COM")
    assert tid == "waifinder-flagship"


def test_unknown_host_falls_back_to_default():
    tid = resolve_tenant(
        host="never-registered.example.com",
        default_tenant_id="waifinder-flagship",
    )
    assert tid == "waifinder-flagship"


def test_empty_header_does_not_win_over_host():
    tid = resolve_tenant(x_tenant_id="  ", host="platform.thewaifinder.com")
    assert tid == "waifinder-flagship"


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


def _mk_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(TenantResolutionMiddleware, default_tenant_id="waifinder-flagship")

    @app.get("/echo")
    def echo(request: Request):
        return {
            "tenant_id": request.state.tenant_id,
            "brand_name": request.state.brand.display_name,
            "hostname": request.state.brand.portal_hostname,
        }

    return app


def test_middleware_resolves_via_host_header():
    client = TestClient(_mk_app())
    r = client.get("/echo", headers={"Host": "platform.thewaifinder.com"})
    assert r.status_code == 200
    body = r.json()
    assert body["tenant_id"] == "waifinder-flagship"
    assert body["brand_name"] == "Waifinder"


def test_middleware_resolves_via_x_tenant_id_header():
    client = TestClient(_mk_app())
    r = client.get("/echo", headers={"X-Tenant-Id": "borderplex"})
    assert r.status_code == 200
    assert r.json()["tenant_id"] == "borderplex"


def test_middleware_echoes_x_tenant_id_response_header():
    client = TestClient(_mk_app())
    r = client.get("/echo", headers={"X-Tenant-Id": "borderplex"})
    assert r.headers["X-Tenant-Id"] == "borderplex"


def test_middleware_falls_back_to_default_for_unknown_host():
    client = TestClient(_mk_app())
    r = client.get("/echo", headers={"Host": "unknown.example.com"})
    assert r.json()["tenant_id"] == "waifinder-flagship"


def test_brand_config_has_required_fields():
    b = get_brand("borderplex")
    assert b.display_name
    assert b.logo_url
    assert b.primary_color.startswith("#")
    assert b.accent_color.startswith("#")
    assert "@" in b.email_from_address
    assert b.portal_hostname
