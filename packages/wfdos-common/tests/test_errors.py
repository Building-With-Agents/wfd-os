"""Tests for wfdos_common.errors — structured envelope + FastAPI handlers (#29)."""

from __future__ import annotations

from fastapi import Body, FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from wfdos_common.errors import (
    APIError,
    ConflictError,
    ForbiddenError,
    NotFoundError,
    ServiceUnavailableError,
    UnauthorizedError,
    ValidationFailure,
    install_error_handlers,
)
from wfdos_common.logging import RequestContextMiddleware


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class _Item(BaseModel):
    name: str
    qty: int


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    install_error_handlers(app)

    @app.get("/items/{item_id}")
    def get_item(item_id: str) -> dict:
        if item_id == "missing":
            raise NotFoundError("item", item_id)
        if item_id == "conflict":
            raise ConflictError("item already in pending state")
        if item_id == "noauth":
            raise UnauthorizedError("missing bearer token")
        if item_id == "forbidden":
            raise ForbiddenError("caller lacks role 'admin'")
        if item_id == "downstream":
            raise ServiceUnavailableError("graph api 503")
        if item_id == "rule":
            raise ValidationFailure("qty must be positive", details={"field": "qty"})
        if item_id == "boom":
            raise RuntimeError("kaboom")  # triggers unhandled-exception path
        return {"item_id": item_id}

    @app.post("/items")
    def create_item(item: _Item = Body(...)) -> dict:
        return {"received": item.model_dump()}

    return app


# ---------------------------------------------------------------------------
# Typed APIError subclasses
# ---------------------------------------------------------------------------


def test_not_found_envelope():
    client = TestClient(_make_app())
    r = client.get("/items/missing")
    assert r.status_code == 404
    body = r.json()
    assert body["data"] is None
    err = body["error"]
    assert err["code"] == "not_found"
    assert "item" in err["message"]
    assert err["details"]["resource"] == "item"
    assert err["details"]["identifier"] == "missing"


def test_conflict_envelope():
    client = TestClient(_make_app())
    r = client.get("/items/conflict")
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_unauthorized_envelope():
    client = TestClient(_make_app())
    r = client.get("/items/noauth")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_forbidden_envelope():
    client = TestClient(_make_app())
    r = client.get("/items/forbidden")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_service_unavailable_envelope():
    client = TestClient(_make_app())
    r = client.get("/items/downstream")
    assert r.status_code == 503
    assert r.json()["error"]["code"] == "service_unavailable"


def test_validation_failure_envelope():
    client = TestClient(_make_app())
    r = client.get("/items/rule")
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error"
    assert err["details"]["field"] == "qty"


# ---------------------------------------------------------------------------
# Pydantic schema validation (422)
# ---------------------------------------------------------------------------


def test_pydantic_validation_normalized_to_envelope():
    client = TestClient(_make_app())
    r = client.post("/items", json={"name": "x"})  # missing qty
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error"
    field_errors = err["details"]["field_errors"]
    assert any(fe["field"].endswith("qty") for fe in field_errors)


def test_pydantic_wrong_type_error_shape():
    client = TestClient(_make_app())
    r = client.post("/items", json={"name": "x", "qty": "not-an-int"})
    assert r.status_code == 422
    err = r.json()["error"]
    assert err["code"] == "validation_error"
    field_errors = err["details"]["field_errors"]
    qty_err = next(fe for fe in field_errors if fe["field"].endswith("qty"))
    # Pydantic v2 code for "input should be a valid integer" starts with "int_"
    assert "int" in qty_err["type"]


# ---------------------------------------------------------------------------
# Unhandled exception path
# ---------------------------------------------------------------------------


def test_unhandled_exception_sanitized():
    """Raw RuntimeError → 500 envelope with exception_type but no stack trace."""
    client = TestClient(_make_app(), raise_server_exceptions=False)
    r = client.get("/items/boom")
    assert r.status_code == 500
    err = r.json()["error"]
    assert err["code"] == "internal_error"
    assert err["details"]["exception_type"] == "RuntimeError"
    # Never leak the raw exception message to the client.
    assert "kaboom" not in err["message"]


# ---------------------------------------------------------------------------
# Request-id echoed into error body
# ---------------------------------------------------------------------------


def test_request_id_echoed_in_error_details():
    client = TestClient(_make_app())
    r = client.get("/items/missing", headers={"X-Request-Id": "trace-42"})
    assert r.status_code == 404
    assert r.json()["error"]["details"]["request_id"] == "trace-42"
    assert r.headers["X-Request-Id"] == "trace-42"


# ---------------------------------------------------------------------------
# Envelope shape invariants
# ---------------------------------------------------------------------------


def test_envelope_has_data_none_on_error():
    client = TestClient(_make_app())
    r = client.get("/items/missing")
    body = r.json()
    assert set(body.keys()) <= {"data", "error", "meta"}
    assert body["data"] is None
    assert body.get("meta") is None or isinstance(body["meta"], dict)


def test_api_error_subclass_attrs():
    """Class attrs are authoritative; instances inherit them."""
    assert NotFoundError.http_status == 404
    assert NotFoundError.error_code == "not_found"
    assert ConflictError.http_status == 409
    assert ServiceUnavailableError.http_status == 503


def test_api_error_to_error_detail():
    err = APIError("oops", details={"foo": "bar"})
    ed = err.to_error_detail()
    assert ed.code == "internal_error"
    assert ed.message == "oops"
    assert ed.details == {"foo": "bar"}
