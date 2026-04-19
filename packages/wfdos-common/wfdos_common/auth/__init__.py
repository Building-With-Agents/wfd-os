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
from wfdos_common.auth.tiers import (
    ALL_TIERS,
    TIER_LLM_GATED,
    TIER_PUBLIC,
    TIER_READ_ONLY,
    TierTag,
    audit_tier_tags,
    get_tier,
    llm_gated,
    public,
    read_only,
)
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
    "ALL_TIERS",
    "LoginBody",
    "Session",
    "SessionMiddleware",
    "TIER_LLM_GATED",
    "TIER_PUBLIC",
    "TIER_READ_ONLY",
    "TierTag",
    "TokenError",
    "TokenExpiredError",
    "TokenInvalidError",
    "any_role",
    "audit_tier_tags",
    "build_auth_router",
    "current_user",
    "get_tier",
    "is_allowed",
    "issue_magic_link",
    "issue_session",
    "llm_gated",
    "public",
    "read_only",
    "require_role",
    "resolve_role",
    "verify_magic_link",
    "verify_session",
]
