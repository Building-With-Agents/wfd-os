"""FastAPI/Starlette middleware that resolves a tenant_id and attaches it
to `request.state.tenant_id` for downstream handlers and the session
dependency.

Resolution order (first match wins):

1. `X-Tenant-Id` header. Set by the nginx edge proxy (#30) once the
   full-platform deployment lands. Trust this header because it's set
   INSIDE the trust boundary — nginx doesn't forward it from clients.
2. `Host` header. Matched against a tenants table / static mapping
   passed into the middleware constructor. `platform.thewaifinder.com`
   -> `waifinder-flagship`; client white-label hosts -> their tenant_id.
3. Default fallback: `settings.tenancy.default_tenant_id` (typically
   `waifinder-flagship`).

The middleware does NOT touch the DB — it only pins a string on
`request.state`. Actual engine selection happens when a handler calls
`wfdos_common.db.session.db_session` (or the `session_scope()` context
manager), which looks up `request.state.tenant_id`.

See #22 (engine factory) and #16 (white-label runtime config).
"""

from __future__ import annotations

from typing import Callable, Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.types import ASGIApp


class TenantResolver(BaseHTTPMiddleware):
    """Resolve a tenant_id per request and stash on `request.state.tenant_id`.

    Args:
        app: the ASGI app (FastAPI / Starlette).
        host_to_tenant: optional mapping of Host header -> tenant_id. If
            omitted, all hosts fall through to the default tenant. Pass a
            function rather than a dict if the mapping needs to be
            refreshed live from a DB (per #16 white-label runtime config).
        default_tenant_id: tenant used when no header/host match. If None,
            reads `settings.tenancy.default_tenant_id` at request time.
    """

    def __init__(
        self,
        app: ASGIApp,
        *,
        host_to_tenant: Optional[dict[str, str] | Callable[[str], Optional[str]]] = None,
        default_tenant_id: Optional[str] = None,
    ):
        super().__init__(app)
        self._host_to_tenant = host_to_tenant
        self._default_tenant_id = default_tenant_id

    async def dispatch(self, request: Request, call_next):
        request.state.tenant_id = self._resolve(request)
        return await call_next(request)

    def _resolve(self, request: Request) -> str:
        # 1. Explicit header from the edge proxy.
        hdr = request.headers.get("x-tenant-id")
        if hdr:
            return hdr

        # 2. Host header -> tenant mapping.
        host = request.headers.get("host", "").split(":", 1)[0].lower()
        if host and self._host_to_tenant is not None:
            if callable(self._host_to_tenant):
                mapped = self._host_to_tenant(host)
            else:
                mapped = self._host_to_tenant.get(host)
            if mapped:
                return mapped

        # 3. Fallback to default.
        if self._default_tenant_id:
            return self._default_tenant_id
        from wfdos_common.config import settings

        return settings.tenancy.default_tenant_id
