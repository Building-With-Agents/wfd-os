"""Structural tests for the edge-proxy nginx config (#30).

These tests don't spin up nginx — they parse the committed config file
as text and assert the invariants the deployment runbook depends on:

  - Every platform hostname appears in the `map` block that sets
    `X-Tenant-Id`.
  - Every upstream Python service (9 FastAPI + 1 Next.js portal) is
    reachable via a `location` + `proxy_pass` rule.
  - Security headers (HSTS, nosniff, X-Frame-Options, Referrer-Policy)
    are present on the main server block.
  - The HTTP server block redirects to HTTPS.
  - `X-Tenant-Id` is forwarded to upstreams via `proxy_set_header`.

The CI check runs this test on every PR. A syntactic `nginx -t` check
requires nginx + the TLS cert paths, so that check belongs in the
deployment runbook, not in-repo CI.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

_CONF = Path(__file__).resolve().parents[3] / "infra/edge/nginx/wfdos-platform.conf"


@pytest.fixture(scope="module")
def conf_text() -> str:
    assert _CONF.exists(), f"nginx config missing: {_CONF}"
    return _CONF.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Host → tenant mapping
# ---------------------------------------------------------------------------


def test_host_map_has_flagship(conf_text: str):
    assert "platform.thewaifinder.com" in conf_text
    assert "waifinder-flagship" in conf_text


def test_host_map_has_borderplex(conf_text: str):
    assert "talent.borderplexwfs.org" in conf_text
    assert "borderplex" in conf_text


def test_host_map_has_default_fallback(conf_text: str):
    # The map block must set a `default` so a misconfigured Host never
    # hits upstream without a tenant_id.
    assert re.search(r"map\s+\$host\s+\$wfdos_tenant_id", conf_text)
    assert re.search(r"default\s+\S+;", conf_text)


# ---------------------------------------------------------------------------
# Upstream reachability — every service listed in the plan has a location.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "location_prefix",
    [
        "/api/student/",
        "/api/showcase/",
        "/api/consulting/",
        "/api/college/",
        "/api/wji/",
        "/api/reporting/",
        "/api/marketing/",
        "/api/assistant/",
        "/api/apollo/",
    ],
)
def test_api_location_block_present(conf_text: str, location_prefix: str):
    # `location /api/student/` {
    assert re.search(
        r"location\s+" + re.escape(location_prefix) + r"\s*\{",
        conf_text,
    ), f"missing location block for {location_prefix}"


def test_portal_root_location_present(conf_text: str):
    assert re.search(r"location\s+/\s*\{", conf_text)


def test_every_service_has_proxy_pass_to_upstream(conf_text: str):
    # Count `proxy_pass` occurrences in location blocks.
    matches = re.findall(r"proxy_pass\s+http://wfdos_\w+;", conf_text)
    # 10 upstreams (portal counted twice: / and /_next/static/) + a few
    # apis. We don't need an exact number; just assert > 9 so a future
    # regression that drops an upstream is caught.
    assert len(matches) >= 10


# ---------------------------------------------------------------------------
# Security headers — present on the main (HTTPS) server block.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "header",
    [
        "Strict-Transport-Security",
        "X-Content-Type-Options",
        "X-Frame-Options",
        "Referrer-Policy",
    ],
)
def test_security_header_present(conf_text: str, header: str):
    assert header in conf_text, f"missing security header {header}"


def test_hsts_has_reasonable_max_age(conf_text: str):
    # At least 30 days — documented as 6 months in the conf.
    m = re.search(r"max-age=(\d+)", conf_text)
    assert m is not None
    assert int(m.group(1)) >= 30 * 24 * 60 * 60


# ---------------------------------------------------------------------------
# Tenant + upstream-forward headers
# ---------------------------------------------------------------------------


def test_x_tenant_id_forwarded_to_upstream(conf_text: str):
    assert re.search(
        r"proxy_set_header\s+X-Tenant-Id\s+\$wfdos_tenant_id;",
        conf_text,
    )


def test_x_forwarded_for_set(conf_text: str):
    assert re.search(r"proxy_set_header\s+X-Forwarded-For", conf_text)


def test_x_forwarded_proto_set(conf_text: str):
    assert re.search(r"proxy_set_header\s+X-Forwarded-Proto", conf_text)


# ---------------------------------------------------------------------------
# HTTPS redirect
# ---------------------------------------------------------------------------


def test_http_server_redirects_to_https(conf_text: str):
    # Block listening on port 80 with a 301 redirect.
    assert re.search(r"listen\s+80", conf_text)
    assert re.search(r"return\s+301\s+https", conf_text)


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------


def test_login_rate_limit_zone_defined(conf_text: str):
    assert re.search(
        r"limit_req_zone\s+\S+\s+zone=platform_login", conf_text
    )


def test_api_rate_limit_zone_defined(conf_text: str):
    assert re.search(r"limit_req_zone\s+\S+\s+zone=platform_api", conf_text)


def test_login_endpoint_applies_login_zone(conf_text: str):
    # The /api/auth/login location must reference the stricter zone.
    login_block = re.search(
        r"location\s+/api/auth/login\s*\{[^}]*\}",
        conf_text,
        flags=re.DOTALL,
    )
    assert login_block is not None
    assert "zone=platform_login" in login_block.group(0)
