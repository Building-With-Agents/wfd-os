"""wfdos_common.db — multi-tenant SQLAlchemy engine factory + session + middleware.

Public API:

  get_engine(tenant_id, *, read_only=False)  — cached engine per (tenant, mode)
  register_tenant(tenant_id, url)            — register a DB URL
  resolve_url(tenant_id)                     — introspection: which URL is used
  dispose_all()                              — test/shutdown helper

  session_scope(tenant_id, read_only=False)  — context-managed Session
  db_session(request)                        — FastAPI dependency

  TenantResolver                             — Host-header / X-Tenant-Id middleware

Implemented across PRs #22a (engine + session + middleware — this scope),
#22b (canonical CREATE TABLE schema), #22c (migrate 5 portal services
from raw psycopg2 to these primitives).
"""

from wfdos_common.db.engine import (
    clear_tenant_registry,
    dispose_all,
    get_engine,
    register_tenant,
    registered_tenants,
    resolve_url,
)
from wfdos_common.db.middleware import TenantResolver
from wfdos_common.db.session import db_session, session_scope

__all__ = [
    # engine
    "get_engine",
    "register_tenant",
    "registered_tenants",
    "clear_tenant_registry",
    "resolve_url",
    "dispose_all",
    # session
    "session_scope",
    "db_session",
    # middleware
    "TenantResolver",
]
