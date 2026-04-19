"""Structured error envelope + FastAPI exception handlers (#29).

Before #29, every service raised `HTTPException` with a raw string detail
(often a traceback) and caught `except Exception:` with a bare 500.
Clients couldn't distinguish a validation failure from a not-found from an
integration outage, and request IDs leaked into error bodies inconsistently.

After #29, every service gets:

* **`APIError`** — a typed base class for expected failures that carries an
  `error_code`, `http_status`, and an optional `details` dict.
* **Concrete subclasses** — `NotFoundError`, `ValidationFailure`,
  `ConflictError`, `UnauthorizedError`, `ForbiddenError`,
  `ServiceUnavailableError` — services raise these instead of
  `HTTPException(...)` or `except Exception: ... raise HTTPException(500)`.
* **`install_error_handlers(app)`** — one call wires three handlers to the
  FastAPI app:
  - `APIError` → structured envelope with the subclass's `error_code`.
  - Pydantic's `RequestValidationError` → envelope with code
    `validation_error` and a normalized list of field-level problems.
  - Bare `Exception` → envelope with code `internal_error`, status 500,
    plus a logged request-context stack trace (via `wfdos_common.logging`).

Every envelope shape matches `wfdos_common.models.core.APIEnvelope` /
`ErrorDetail`. The `X-Request-Id` from `RequestContextMiddleware` (#23) is
echoed into `error.details.request_id` so clients can reference it when
filing a bug.

Usage::

    from fastapi import FastAPI
    from wfdos_common.errors import install_error_handlers, NotFoundError

    app = FastAPI()
    install_error_handlers(app)

    @app.get("/students/{id}")
    def get_student(id: str):
        row = db.fetch_student(id)
        if row is None:
            raise NotFoundError("student", id)
        return row
"""

from __future__ import annotations

from typing import Any, Optional

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from wfdos_common.logging import current_context, get_logger
from wfdos_common.models.core import APIEnvelope, ErrorDetail

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Typed exception classes
# ---------------------------------------------------------------------------


class APIError(Exception):
    """Base class for expected API errors.

    Subclasses supply `error_code` + `http_status` class attributes;
    instances pass a `message` (human one-liner) and optional `details`.
    The FastAPI handler installed by `install_error_handlers` turns these
    into the standard `ErrorDetail` envelope.
    """

    error_code: str = "internal_error"
    http_status: int = status.HTTP_500_INTERNAL_SERVER_ERROR

    def __init__(
        self,
        message: str,
        *,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or {}

    def to_error_detail(self) -> ErrorDetail:
        return ErrorDetail(
            code=self.error_code,
            message=self.message,
            details=self.details or None,
        )


class NotFoundError(APIError):
    """The requested resource doesn't exist. Use for GET/PATCH/DELETE of a
    primary key that isn't there; do NOT use for auth-gated lookups where
    existence itself leaks info (raise `ForbiddenError` instead)."""

    error_code = "not_found"
    http_status = status.HTTP_404_NOT_FOUND

    def __init__(
        self,
        resource: str,
        identifier: Optional[str] = None,
        *,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        if identifier is None:
            msg = f"{resource} not found"
        else:
            msg = f"{resource} '{identifier}' not found"
        merged: dict[str, Any] = {"resource": resource}
        if identifier is not None:
            merged["identifier"] = identifier
        if details:
            merged.update(details)
        super().__init__(msg, details=merged)


class ValidationFailure(APIError):
    """A business-rule validation failed (distinct from Pydantic schema
    validation, which gets its own handler). Use for things like 'dates
    must be in the future' or 'can't discharge student with active OJT'."""

    error_code = "validation_error"
    http_status = status.HTTP_422_UNPROCESSABLE_ENTITY


class ConflictError(APIError):
    """Request conflicts with current resource state (e.g. duplicate email,
    stale write, concurrent update)."""

    error_code = "conflict"
    http_status = status.HTTP_409_CONFLICT


class UnauthorizedError(APIError):
    """Caller isn't authenticated. Matches 401."""

    error_code = "unauthorized"
    http_status = status.HTTP_401_UNAUTHORIZED


class ForbiddenError(APIError):
    """Caller is authenticated but not allowed to access this resource."""

    error_code = "forbidden"
    http_status = status.HTTP_403_FORBIDDEN


class ServiceUnavailableError(APIError):
    """An integration dependency (Graph API, LLM provider, DB) is down or
    degraded. Use this so clients know the request might succeed on retry."""

    error_code = "service_unavailable"
    http_status = status.HTTP_503_SERVICE_UNAVAILABLE


# ---------------------------------------------------------------------------
# Envelope helpers
# ---------------------------------------------------------------------------


def _with_request_id(details: Optional[dict[str, Any]]) -> dict[str, Any]:
    """Merge the current request_id from the logging ContextVar into the
    details dict so clients can reference it when filing a bug."""
    ctx = current_context()
    request_id = ctx.get("request_id")
    if request_id is None:
        return dict(details or {})
    merged = dict(details or {})
    merged.setdefault("request_id", request_id)
    return merged


def _envelope(error: ErrorDetail, *, status_code: int) -> JSONResponse:
    # Keep `data` + `meta` in the payload (as null) so clients can rely on
    # the envelope shape; only drop null *within* the error detail so we
    # don't ship empty `details: null` when there's nothing to say.
    payload = {
        "data": None,
        "error": error.model_dump(exclude_none=True),
        "meta": None,
    }
    return JSONResponse(status_code=status_code, content=jsonable_encoder(payload))


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------


async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
    """Turn a raised `APIError` into the standard envelope."""
    detail = exc.to_error_detail()
    detail = ErrorDetail(
        code=detail.code,
        message=detail.message,
        details=_with_request_id(detail.details),
    )
    log.info(
        "api.error",
        error_code=detail.code,
        http_status=exc.http_status,
        message=detail.message,
    )
    return _envelope(detail, status_code=exc.http_status)


async def validation_error_handler(
    _request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Normalize Pydantic's 422 list into the standard envelope.

    Each entry becomes `{"field": "body.name", "type": "...", "msg": "..."}`.
    """
    field_errors: list[dict[str, Any]] = []
    for e in exc.errors():
        loc = e.get("loc", ())
        field = ".".join(str(x) for x in loc)
        field_errors.append(
            {
                "field": field,
                "type": e.get("type"),
                "msg": e.get("msg"),
            }
        )
    detail = ErrorDetail(
        code="validation_error",
        message="Request validation failed",
        details=_with_request_id({"field_errors": field_errors}),
    )
    log.info(
        "api.validation_error",
        field_count=len(field_errors),
    )
    return _envelope(detail, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    """Last-resort handler for truly unexpected errors.

    The stack trace is logged at ERROR (with `exc_info=True` so structlog
    captures it); the client only sees a sanitized envelope with the
    request_id so support can look it up.
    """
    log.error(
        "api.unhandled_exception",
        exc_type=type(exc).__name__,
        exc_info=True,
    )
    detail = ErrorDetail(
        code="internal_error",
        message="An unexpected error occurred.",
        details=_with_request_id({"exception_type": type(exc).__name__}),
    )
    return _envelope(detail, status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


def install_error_handlers(app: FastAPI) -> None:
    """Attach the three standard exception handlers to a FastAPI app.

    Idempotent — calling twice just replaces the handlers.
    """
    app.add_exception_handler(APIError, api_error_handler)  # type: ignore[arg-type]
    app.add_exception_handler(
        RequestValidationError, validation_error_handler  # type: ignore[arg-type]
    )
    app.add_exception_handler(Exception, unhandled_exception_handler)


__all__ = [
    "APIError",
    "NotFoundError",
    "ValidationFailure",
    "ConflictError",
    "UnauthorizedError",
    "ForbiddenError",
    "ServiceUnavailableError",
    "install_error_handlers",
    "api_error_handler",
    "validation_error_handler",
    "unhandled_exception_handler",
]
