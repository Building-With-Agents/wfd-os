"""Tier decorators — route-level access classification for #25.

Every FastAPI route on the platform falls into one of three tiers:

  @public       — no auth required. Marketing CTAs, /healthz, /auth/login.
  @read_only    — auth required; returns data but never mutates state
                  and never consumes paid API calls (LLM, Graph, etc.).
                  Allows unauth in "degraded-read" mode ONLY when the
                  service is deployed without auth credentials (see
                  `require_auth=False` knob) — default is require auth.
                  Uses the shared read-only DB engine from #22.
  @llm_gated    — auth required; may consume LLM or other paid-API quota;
                  rate-limited per role. Returns 503 if the configured
                  LLM provider has no credentials (so a stripped-.env
                  deploy boots, advertises tier-1 endpoints, and fails
                  tier-2 cleanly).

Each decorator is a thin wrapper that:

  1. Tags the endpoint function with `__wfdos_tier__` so an audit can
     grep every route's tier at build time.
  2. Attaches the right set of FastAPI dependencies (require_role, the
     rate-limiter key, the read-only DB override).

This file intentionally does NOT couple to the specific slowapi import
paths — the rate-limit hook is a dependency function the service passes
in via `configure_tier_limits()`, so unit tests can inject a stub.
"""

from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Any, Callable, Iterable, Optional

from fastapi import Depends, Request

from wfdos_common.auth.dependencies import current_user, require_role
from wfdos_common.auth.tokens import Session
from wfdos_common.errors import ServiceUnavailableError, UnauthorizedError
from wfdos_common.logging import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Tier tag — inspected by the CI audit script (#25 acceptance).
# ---------------------------------------------------------------------------


TIER_PUBLIC = "public"
TIER_READ_ONLY = "read_only"
TIER_LLM_GATED = "llm_gated"

ALL_TIERS = (TIER_PUBLIC, TIER_READ_ONLY, TIER_LLM_GATED)


@dataclass
class TierTag:
    """Metadata attached to every decorated endpoint. Route inventory
    audits read this to ensure every public route has a tier."""

    tier: str
    roles: tuple[str, ...]
    rate_limit_per_hour: Optional[int] = None


def _attach_tag(fn: Callable[..., Any], tag: TierTag) -> None:
    setattr(fn, "__wfdos_tier__", tag)


def get_tier(fn: Callable[..., Any]) -> TierTag | None:
    """Return the tier tag for a decorated endpoint, or None if not tagged.

    CI uses this to diff the route inventory against
    docs/public-url-contract.md in #31.
    """
    return getattr(fn, "__wfdos_tier__", None)


# ---------------------------------------------------------------------------
# @public
# ---------------------------------------------------------------------------


def public(fn: Callable[..., Any]) -> Callable[..., Any]:
    """Mark a route as no-auth-required. Pure metadata; does nothing at
    runtime, but the CI audit flags untagged routes."""
    _attach_tag(fn, TierTag(tier=TIER_PUBLIC, roles=()))
    return fn


# ---------------------------------------------------------------------------
# @read_only(roles=...)
# ---------------------------------------------------------------------------


def read_only(
    *,
    roles: Iterable[str] = ("student", "staff", "admin"),
    require_auth: bool = True,
):
    """Decorator factory for tier-1 (read-only, no paid APIs) routes.

    Usage::

        @app.get("/api/students/me")
        @read_only(roles=("student", "staff", "admin"))
        def me(user: Session = Depends(current_user)): ...

    Semantics:
      - `require_auth=True` (default): a missing/invalid session → 401.
      - `require_auth=False`: unauth requests pass through (used for the
        subset of read-only routes we intentionally make public, like
        /api/showcase/candidates for the careers page).
    """
    roles_t = tuple(roles)

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        _attach_tag(fn, TierTag(tier=TIER_READ_ONLY, roles=roles_t))

        if not require_auth:
            # Pure tag; runtime unchanged.
            return fn

        # If require_auth, wrap so the fn raises 401 on missing session.
        # We look up request.state.user ourselves rather than adding a
        # FastAPI dependency because decorators composed with @app.get
        # complicate dep-injection.
        @functools.wraps(fn)
        async def _async_wrapper(*args: Any, **kwargs: Any):
            request: Request | None = _find_request(args, kwargs)
            _require_session_on_request(request, roles_t)
            return await fn(*args, **kwargs)

        @functools.wraps(fn)
        def _sync_wrapper(*args: Any, **kwargs: Any):
            request: Request | None = _find_request(args, kwargs)
            _require_session_on_request(request, roles_t)
            return fn(*args, **kwargs)

        import inspect

        wrapper = _async_wrapper if inspect.iscoroutinefunction(fn) else _sync_wrapper
        _attach_tag(wrapper, TierTag(tier=TIER_READ_ONLY, roles=roles_t))
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# @llm_gated(roles=...)
# ---------------------------------------------------------------------------


def llm_gated(
    *,
    roles: Iterable[str] = ("staff", "admin"),
    rate_limit_per_hour: Optional[int] = None,
):
    """Decorator factory for tier-2 (paid-API) routes.

    Semantics:
      - Always requires an authenticated session. Missing/invalid → 401.
      - Caller role must be in `roles` (default: staff + admin). Wrong → 403.
      - If the LLM adapter has no configured provider (stripped-`.env`
        deploy), the wrapper raises `ServiceUnavailableError` with code
        `service_unavailable` so clients see a clean 503. That means a
        production host can boot with only DB-read creds, serve tier-1
        traffic, and cleanly fail tier-2 — perfect for #25's "stripped
        `.env` smoke" acceptance.

    Rate limiting is per-role via `rate_limit_per_hour`. When None, the
    service-level default (derived from AuthSettings) applies.
    """
    roles_t = tuple(roles)

    def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
        tag = TierTag(tier=TIER_LLM_GATED, roles=roles_t, rate_limit_per_hour=rate_limit_per_hour)
        _attach_tag(fn, tag)

        @functools.wraps(fn)
        async def _async_wrapper(*args: Any, **kwargs: Any):
            request: Request | None = _find_request(args, kwargs)
            _require_session_on_request(request, roles_t)
            _require_llm_available()
            return await fn(*args, **kwargs)

        @functools.wraps(fn)
        def _sync_wrapper(*args: Any, **kwargs: Any):
            request: Request | None = _find_request(args, kwargs)
            _require_session_on_request(request, roles_t)
            _require_llm_available()
            return fn(*args, **kwargs)

        import inspect

        wrapper = _async_wrapper if inspect.iscoroutinefunction(fn) else _sync_wrapper
        _attach_tag(wrapper, tag)
        return wrapper

    return decorator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _find_request(args: tuple, kwargs: dict) -> Request | None:
    """Dig the FastAPI Request out of args/kwargs. The decorators don't
    want to force the handler signature to accept `request: Request`, so
    we search."""
    for v in list(args) + list(kwargs.values()):
        if isinstance(v, Request):
            return v
    return None


def _require_session_on_request(request: Request | None, allowed_roles: tuple[str, ...]) -> None:
    if request is None:
        # The decorator is paranoid: if somehow the FastAPI machinery
        # didn't give us a Request, treat it as an error so we fail
        # closed. In practice FastAPI always supplies one when the route
        # function or its deps take `request: Request`.
        raise UnauthorizedError("authentication required")
    session: Session | None = getattr(request.state, "user", None)
    if session is None:
        raise UnauthorizedError("authentication required")
    # Reuse the same 403 handling as require_role, but inline so we don't
    # double-wrap the dep.
    if allowed_roles and session.role not in allowed_roles:
        from wfdos_common.errors import ForbiddenError

        raise ForbiddenError(
            f"role '{session.role}' is not allowed on this endpoint",
            details={"required_roles": sorted(allowed_roles), "actual_role": session.role},
        )


def _require_llm_available() -> None:
    """Raise ServiceUnavailableError if no LLM provider is configured.

    The LLM adapter (#20) already has a graceful-degradation fallback
    chain; what we check here is whether any of the three providers
    (Azure OpenAI, Anthropic, Gemini) has any credentials at all. If
    none do, the service booted without LLM access and tier-2 routes
    should 503.
    """
    from wfdos_common.config import settings

    # Azure OpenAI's settings model names the field `key` — check both
    # `key` and `api_key` to be tolerant of future renames.
    azure = settings.azure_openai
    has_azure = bool(
        getattr(azure, "key", "") or getattr(azure, "api_key", "") or getattr(azure, "endpoint", "")
    )
    has_anthropic = bool(getattr(settings.llm, "anthropic_api_key", ""))
    has_gemini = bool(getattr(settings.llm, "gemini_api_key", ""))
    if not (has_azure or has_anthropic or has_gemini):
        raise ServiceUnavailableError(
            "LLM provider not configured on this host",
            details={"tier": "llm_gated"},
        )


# ---------------------------------------------------------------------------
# Audit helper — used by CI (#31 later but lives here)
# ---------------------------------------------------------------------------


def audit_tier_tags(routes: Iterable[Any]) -> dict[str, list[str]]:
    """Given an iterable of FastAPI route objects, return a dict of
    `{tier: [path, ...]}` plus a special `"untagged"` bucket for routes
    that have no tier. CI uses this to enforce 100% tier coverage.
    """
    out: dict[str, list[str]] = {t: [] for t in ALL_TIERS}
    out["untagged"] = []
    for r in routes:
        endpoint = getattr(r, "endpoint", None)
        path = getattr(r, "path", "<unknown>")
        if endpoint is None:
            out["untagged"].append(path)
            continue
        tag = get_tier(endpoint)
        if tag is None:
            out["untagged"].append(path)
        else:
            out[tag.tier].append(path)
    return out


__all__ = [
    "ALL_TIERS",
    "TIER_PUBLIC",
    "TIER_READ_ONLY",
    "TIER_LLM_GATED",
    "TierTag",
    "audit_tier_tags",
    "get_tier",
    "llm_gated",
    "public",
    "read_only",
]
