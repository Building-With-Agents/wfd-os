"""wfdos_common.auth — magic-link auth + role-based access (#24).

Public surface:

  tokens     — itsdangerous-backed magic-link + session token sign/verify
  allowlist  — env-driven email → role resolution
  middleware — SessionMiddleware that parses the cookie into request.state.user
  dependencies — require_role(*roles) FastAPI dependency
  routes     — build_auth_router() — mountable /auth/{login,verify,logout,me}
"""

from wfdos_common.auth.allowlist import (
    ALLOWED_ROLES,
    is_allowed,
    resolve_role,
)
from wfdos_common.auth.dependencies import (
    any_role,
    current_user,
    require_role,
)
from wfdos_common.auth.middleware import SessionMiddleware
from wfdos_common.auth.routes import LoginBody, build_auth_router
from wfdos_common.auth.tokens import (
    Session,
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    issue_magic_link,
    issue_session,
    verify_magic_link,
    verify_session,
)

__all__ = [
    "ALLOWED_ROLES",
    "Session",
    "TokenError",
    "TokenExpiredError",
    "TokenInvalidError",
    "SessionMiddleware",
    "LoginBody",
    "any_role",
    "build_auth_router",
    "current_user",
    "is_allowed",
    "issue_magic_link",
    "issue_session",
    "require_role",
    "resolve_role",
    "verify_magic_link",
    "verify_session",
]
