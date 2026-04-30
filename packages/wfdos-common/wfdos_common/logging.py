"""wfdos_common.logging — structlog + ContextVars + request middleware (#23).

Services call `configure(service_name=...)` once at startup. Every
log call after that emits JSON (or pretty console) with the current
request's tenant_id / user_id / request_id attached automatically.

Usage::

    # service startup
    from wfdos_common.logging import configure, get_logger, RequestContextMiddleware

    configure(service_name="consulting-api")
    log = get_logger(__name__)

    log.info("service.started", port=8003)

    # FastAPI middleware wiring — order matters: TenantResolver before
    # RequestContextMiddleware so tenant_id is set by the time this reads it.
    from wfdos_common.db import TenantResolver
    app.add_middleware(RequestContextMiddleware)
    app.add_middleware(TenantResolver, ...)

    # inside a handler
    log.info("inquiry.submitted", inquiry_id=42, source="web")

Output (JSON format, default)::

    {"timestamp": "2026-04-16T...", "level": "info", "event": "inquiry.submitted",
     "inquiry_id": 42, "source": "web", "request_id": "a3...",
     "tenant_id": "waifinder-flagship", "service_name": "consulting-api"}

Env vars that affect output:
    LOG_FORMAT   "json" (default) or "console"
    LOG_LEVEL    "DEBUG" | "INFO" (default) | "WARNING" | "ERROR"
"""

from __future__ import annotations

import logging as stdlib_logging
import os
import uuid
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Iterator, Optional

import structlog
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

# ---------------------------------------------------------------------------
# Request-scoped context variables
# ---------------------------------------------------------------------------

_tenant_id_cv: ContextVar[Optional[str]] = ContextVar("wfdos_tenant_id", default=None)
_user_id_cv: ContextVar[Optional[str]] = ContextVar("wfdos_user_id", default=None)
_request_id_cv: ContextVar[Optional[str]] = ContextVar("wfdos_request_id", default=None)
_service_name_cv: ContextVar[Optional[str]] = ContextVar("wfdos_service_name", default=None)


def _inject_context(logger, method_name, event_dict):
    """structlog processor — attach ContextVar values to every log entry
    unless the caller already explicitly set the key.
    """
    for name, cv in (
        ("tenant_id", _tenant_id_cv),
        ("user_id", _user_id_cv),
        ("request_id", _request_id_cv),
        ("service_name", _service_name_cv),
    ):
        value = cv.get()
        if value is not None:
            event_dict.setdefault(name, value)
    return event_dict


# ---------------------------------------------------------------------------
# configure() — called once at service startup
# ---------------------------------------------------------------------------

_configured = False


def configure(
    service_name: str,
    *,
    log_format: Optional[str] = None,
    log_level: Optional[str] = None,
) -> None:
    """Configure structlog + stdlib logging for the current process.

    Idempotent — subsequent calls update the service_name ContextVar but
    don't re-register processors. Use reset_configured() in tests.

    Args:
        service_name: attached to every log entry as `service_name`.
        log_format:  "json" (default) or "console". Overrides LOG_FORMAT env.
        log_level:   "DEBUG"/"INFO"/"WARNING"/"ERROR". Overrides LOG_LEVEL env.
    """
    global _configured

    _service_name_cv.set(service_name)

    if _configured:
        return

    fmt = (log_format or os.getenv("LOG_FORMAT", "json")).lower()
    level_name = (log_level or os.getenv("LOG_LEVEL", "INFO")).upper()
    level = getattr(stdlib_logging, level_name, stdlib_logging.INFO)

    # Ensure stdlib logging flows through at the configured verbosity.
    stdlib_logging.basicConfig(format="%(message)s", level=level)

    renderer = (
        structlog.dev.ConsoleRenderer()
        if fmt == "console"
        else structlog.processors.JSONRenderer()
    )

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            _inject_context,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", utc=True, key="timestamp"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )
    _configured = True


def reset_configured() -> None:
    """Test hook — re-enable configure() to run on next call."""
    global _configured
    _configured = False


def get_logger(name: Optional[str] = None):
    """Return a structlog logger. configure() should have been called
    at service startup; if not, default structlog processors still work
    but formatting may differ from the rest of the stack.
    """
    return structlog.get_logger(name)


# ---------------------------------------------------------------------------
# Context helpers — set/get ContextVars outside middleware
# ---------------------------------------------------------------------------

def set_tenant_id(tenant_id: Optional[str]) -> None:
    _tenant_id_cv.set(tenant_id)


def set_user_id(user_id: Optional[str]) -> None:
    _user_id_cv.set(user_id)


def set_request_id(request_id: Optional[str]) -> None:
    _request_id_cv.set(request_id)


def current_context() -> dict[str, Any]:
    """Snapshot the context vars — useful for tests + debug."""
    return {
        "tenant_id": _tenant_id_cv.get(),
        "user_id": _user_id_cv.get(),
        "request_id": _request_id_cv.get(),
        "service_name": _service_name_cv.get(),
    }


@contextmanager
def bind_context(
    *,
    tenant_id: Optional[str] = None,
    user_id: Optional[str] = None,
    request_id: Optional[str] = None,
) -> Iterator[None]:
    """Context manager — bind values for the duration of the `with` block.

    Useful for background tasks / CLI scripts where there's no HTTP
    request to hook middleware into::

        with bind_context(tenant_id="waifinder-flagship", request_id=batch_id):
            run_the_batch()
    """
    tokens: list[tuple[ContextVar, Any]] = []
    if tenant_id is not None:
        tokens.append((_tenant_id_cv, _tenant_id_cv.set(tenant_id)))
    if user_id is not None:
        tokens.append((_user_id_cv, _user_id_cv.set(user_id)))
    if request_id is not None:
        tokens.append((_request_id_cv, _request_id_cv.set(request_id)))
    try:
        yield
    finally:
        for cv, token in reversed(tokens):
            cv.reset(token)


# ---------------------------------------------------------------------------
# FastAPI / Starlette middleware
# ---------------------------------------------------------------------------

class RequestContextMiddleware(BaseHTTPMiddleware):
    """Sets request_id + tenant_id ContextVars per request.

    tenant_id is read from `request.state.tenant_id` which is set by the
    TenantResolver middleware in `wfdos_common.db.middleware`. **Order
    matters when wiring**: add RequestContextMiddleware *first*, then
    TenantResolver — that way TenantResolver runs before this middleware
    resets its state. (Starlette reverses the order you register: last
    add_middleware runs first.)

    request_id is read from the `X-Request-Id` header if present
    (edge-proxy set), otherwise a new UUIDv4 is generated. The final
    response echoes `X-Request-Id` back so callers can correlate.
    """

    def __init__(self, app, *, header_name: str = "X-Request-Id"):
        super().__init__(app)
        self.header_name = header_name

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(self.header_name) or str(uuid.uuid4())
        req_token = _request_id_cv.set(rid)

        tid = getattr(request.state, "tenant_id", None)
        tid_token = _tenant_id_cv.set(tid) if tid else None

        try:
            response = await call_next(request)
            response.headers[self.header_name] = rid
            return response
        finally:
            _request_id_cv.reset(req_token)
            if tid_token is not None:
                _tenant_id_cv.reset(tid_token)
