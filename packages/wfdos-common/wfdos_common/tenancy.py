"""White-label tenant resolution (#16).

Every incoming request gets mapped to a tenant by `resolve_tenant()`,
using (in priority order):

  1. An explicit `X-Tenant-Id` header — used by server-side callers +
     the edge proxy in #30 after it inspects the Host header.
  2. The `Host` header, looked up against a per-process registry of
     `{hostname: tenant_id}`.
  3. Fallback to `settings.tenancy.default_tenant_id` (waifinder-flagship).

Brand config (logo, colors, email sender, display name) for the resolved
tenant comes from `get_brand(tenant_id)` — values live in a dict at
startup, migrating to a `tenants` DB table as the tenant list grows
(tracked in the #16 follow-up).

The portal (`portal/student/` Next.js) reads brand config server-side
and injects into the React context for client rendering. Standalone
Python services use brand config for email templates, SharePoint folder
naming, and the auth flow's "From" address.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from wfdos_common.logging import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Brand config
# ---------------------------------------------------------------------------


@dataclass
class BrandConfig:
    """Per-tenant branding config the portal + email templates consume.

    All fields have sane Waifinder-flagship defaults so `get_brand(...)`
    returning a default for an unknown tenant doesn't break rendering.
    """

    tenant_id: str
    display_name: str
    logo_url: str
    primary_color: str  # hex, e.g. "#1c3d5a"
    accent_color: str
    email_from_name: str
    email_from_address: str  # must be an address the Graph app can send-as
    portal_hostname: str  # canonical hostname — used for CORS + link generation
    support_email: str = "support@thewaifinder.com"
    # Extra fields free-form so tests/clients can attach arbitrary config
    # without bumping this dataclass every time.
    extras: dict[str, str] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------


# Hardcoded starter set. A follow-up will move these into a `tenants`
# DB table so adding a new client doesn't require a code deploy.
_DEFAULT_BRANDS: dict[str, BrandConfig] = {
    "waifinder-flagship": BrandConfig(
        tenant_id="waifinder-flagship",
        display_name="Waifinder",
        logo_url="https://platform.thewaifinder.com/assets/waifinder-logo.svg",
        primary_color="#1c3d5a",
        accent_color="#f4a261",
        email_from_name="Waifinder",
        email_from_address="hello@thewaifinder.com",
        portal_hostname="platform.thewaifinder.com",
        support_email="support@thewaifinder.com",
    ),
    "borderplex": BrandConfig(
        tenant_id="borderplex",
        display_name="Workforce Solutions Borderplex",
        logo_url="https://platform.thewaifinder.com/assets/borderplex-logo.svg",
        primary_color="#004c7f",
        accent_color="#f2a900",
        email_from_name="Workforce Solutions Borderplex",
        email_from_address="alma@borderplex.workforce",
        portal_hostname="talent.borderplexwfs.org",
        support_email="alma@borderplex.workforce",
    ),
}


_BRANDS: dict[str, BrandConfig] = dict(_DEFAULT_BRANDS)
_HOST_INDEX: dict[str, str] = {
    b.portal_hostname.lower(): b.tenant_id for b in _BRANDS.values()
}


def register_brand(brand: BrandConfig) -> None:
    """Add or replace a brand registration. Safe to call at startup; not
    safe to call concurrently with resolve_tenant()."""
    _BRANDS[brand.tenant_id] = brand
    _HOST_INDEX[brand.portal_hostname.lower()] = brand.tenant_id


def reset_brands() -> None:
    """Test hook — restore the default registry."""
    _BRANDS.clear()
    _HOST_INDEX.clear()
    for b in _DEFAULT_BRANDS.values():
        _BRANDS[b.tenant_id] = b
        _HOST_INDEX[b.portal_hostname.lower()] = b.tenant_id


def all_brands() -> dict[str, BrandConfig]:
    """Return a shallow copy of the brand registry for introspection."""
    return dict(_BRANDS)


def get_brand(tenant_id: str) -> BrandConfig:
    """Return the brand for `tenant_id`, or the flagship default if unknown."""
    if tenant_id in _BRANDS:
        return _BRANDS[tenant_id]
    log.warning("tenancy.unknown_tenant", tenant_id=tenant_id)
    return _BRANDS["waifinder-flagship"]


# ---------------------------------------------------------------------------
# Resolution
# ---------------------------------------------------------------------------


def resolve_tenant(
    *,
    x_tenant_id: Optional[str] = None,
    host: Optional[str] = None,
    default_tenant_id: str = "waifinder-flagship",
) -> str:
    """Return the tenant_id for the current request context.

    Priority: X-Tenant-Id header → Host header → default.

    The Host header lookup is case-insensitive and strips ports (so
    `platform.thewaifinder.com:443` and `platform.thewaifinder.com` both
    hit the same tenant).
    """
    if x_tenant_id and x_tenant_id.strip():
        return x_tenant_id.strip()
    if host:
        normalized = host.split(":")[0].strip().lower()
        if normalized in _HOST_INDEX:
            return _HOST_INDEX[normalized]
    return default_tenant_id


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class TenantResolutionMiddleware(BaseHTTPMiddleware):
    """Attaches `request.state.tenant_id` + `request.state.brand` to every
    request based on the Host / X-Tenant-Id header. Pairs with
    `wfdos_common.logging.RequestContextMiddleware` which picks up the
    tenant_id into structured log context.
    """

    def __init__(self, app, *, default_tenant_id: str = "waifinder-flagship") -> None:
        super().__init__(app)
        self.default_tenant_id = default_tenant_id

    async def dispatch(self, request: Request, call_next) -> Response:
        tenant_id = resolve_tenant(
            x_tenant_id=request.headers.get("x-tenant-id"),
            host=request.headers.get("host"),
            default_tenant_id=self.default_tenant_id,
        )
        brand = get_brand(tenant_id)
        request.state.tenant_id = tenant_id
        request.state.brand = brand
        response = await call_next(request)
        # Expose the resolved tenant in a response header — useful for
        # debugging misconfigured Host → tenant mappings.
        response.headers.setdefault("X-Tenant-Id", tenant_id)
        return response


__all__ = [
    "BrandConfig",
    "TenantResolutionMiddleware",
    "all_brands",
    "get_brand",
    "register_brand",
    "reset_brands",
    "resolve_tenant",
]
