"""FastAPI dependencies for role-based access checks.

Usage on a route:

    from fastapi import Depends
    from wfdos_common.auth import require_role

    @app.get("/api/admin/stats", dependencies=[Depends(require_role("admin"))])
    def admin_stats(): ...

Or as a dependency that returns the Session:

    @app.get("/api/student/me")
    def me(user = Depends(require_role("student", "staff", "admin"))):
        return {"email": user.email}

Unauthenticated requests raise `UnauthorizedError` (401). Authenticated
requests with the wrong role raise `ForbiddenError` (403). Both hit the
envelope handler from `wfdos_common.errors`.
"""

from __future__ import annotations

from typing import Iterable

from starlette.requests import Request

from wfdos_common.auth.tokens import Session
from wfdos_common.errors import ForbiddenError, UnauthorizedError


def require_role(*allowed_roles: str):
    """Build a FastAPI dependency that enforces `allowed_roles`.

    Returns the `Session` for the caller so the route handler can use
    `user.email`, `user.tenant_id`, etc. without reaching into
    `request.state` itself.
    """
    allowed = frozenset(allowed_roles)

    def _dep(request: Request) -> Session:
        user: Session | None = getattr(request.state, "user", None)
        if user is None:
            raise UnauthorizedError("authentication required")
        if allowed and user.role not in allowed:
            raise ForbiddenError(
                f"role '{user.role}' is not allowed on this endpoint",
                details={"required_roles": sorted(allowed), "actual_role": user.role},
            )
        return user

    # Helpful for debugging / introspection.
    _dep.__name__ = f"require_role({','.join(sorted(allowed))})"
    return _dep


def current_user(request: Request) -> Session | None:
    """FastAPI dependency returning the current Session, or None if the
    request is unauthenticated. Use for optional-auth routes."""
    return getattr(request.state, "user", None)


def any_role(roles: Iterable[str]):
    """Alias for require_role that accepts an iterable (readability)."""
    return require_role(*roles)


__all__ = ["require_role", "current_user", "any_role"]
