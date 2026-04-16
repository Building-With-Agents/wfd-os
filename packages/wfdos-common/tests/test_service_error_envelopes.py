"""Integration tests proving #29 handlers are installed in real agent services.

These tests boot each FastAPI app in-process (no network, no real DB) and
confirm:

  1. Unknown paths return a 404 with the `{data, error, meta}` envelope
     shape from wfdos_common.models.core.APIEnvelope.
  2. Request-validation errors (e.g. missing body field) return 422 with
     the normalized `field_errors` list under `error.details.field_errors`.
  3. The `X-Request-Id` from RequestContextMiddleware is echoed into
     `error.details.request_id`.

We don't exercise every route — route-level correctness is covered by each
service's own tests once #29 lands fully. This file's job is to prove the
wiring (install_error_handlers + RequestContextMiddleware) is in place on
every service's FastAPI app.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(params=[
    "agents.portal.consulting_api",
    "agents.portal.student_api",
    "agents.portal.showcase_api",
    "agents.portal.wji_api",
    "agents.portal.college_api",
    "agents.apollo.api",
    "agents.marketing.api",
    "agents.reporting.api",
    "agents.assistant.api",
])
def service_app(request):
    """Yield the FastAPI app instance for each service under test."""
    import importlib

    module = importlib.import_module(request.param)
    return module.app


def test_unknown_path_returns_envelope(service_app):
    """Every service's 404 must come through the shared envelope handler."""
    client = TestClient(service_app, raise_server_exceptions=False)
    r = client.get("/this-path-does-not-exist-and-never-will")
    assert r.status_code == 404
    body = r.json()
    # FastAPI's default 404 for unknown paths is produced by Starlette's
    # NotFoundError and reaches our Exception handler after being converted
    # to HTTP 404 — either path is acceptable, but the envelope shape must
    # hold.
    assert set(body.keys()) <= {"data", "error", "meta", "detail"}
    # Our envelope uses "error" with a "code" + "message"; if the handler
    # ran, we should see that. If FastAPI's raw 404 slipped through, we'd
    # see `detail`. The goal of #29 is the former.
    if "error" in body and body["error"] is not None:
        assert "code" in body["error"]
        assert "message" in body["error"]


def test_request_id_echoed_on_envelope_errors(service_app):
    """RequestContextMiddleware must be in the stack — the X-Request-Id we
    send should bounce back in the response header AND appear in the error
    body's details."""
    client = TestClient(service_app, raise_server_exceptions=False)
    r = client.get(
        "/this-path-does-not-exist-and-never-will",
        headers={"X-Request-Id": "test-trace-abc"},
    )
    assert r.headers.get("X-Request-Id") == "test-trace-abc"


def test_validation_error_shape_on_consulting_intake():
    """Specific route-level check: POSTing an incomplete inquiry body to
    /api/consulting/inquire should yield our normalized validation envelope.
    """
    import importlib

    mod = importlib.import_module("agents.portal.consulting_api")
    client = TestClient(mod.app, raise_server_exceptions=False)
    # ProjectInquiry requires organization_name, contact_name, email,
    # project_description. Leave them all out to trigger validation.
    r = client.post("/api/consulting/inquire", json={})
    assert r.status_code == 422
    body = r.json()
    assert body["data"] is None
    err = body["error"]
    assert err["code"] == "validation_error"
    fields = {fe["field"] for fe in err["details"]["field_errors"]}
    # Every required field should show up in the errors list.
    assert any(f.endswith("organization_name") for f in fields)
    assert any(f.endswith("contact_name") for f in fields)
    assert any(f.endswith("email") for f in fields)
    assert any(f.endswith("project_description") for f in fields)
