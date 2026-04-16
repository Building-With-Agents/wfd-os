"""wfdos_common.db — multi-tenant SQLAlchemy engine factory + session + middleware.

Public API:

  get_engine(tenant_id, *, read_only=False)  — cached engine per (tenant, mode)
  register_tenant(tenant_id, url)            — register a DB URL
  resolve_url(tenant_id)                     — introspection: which URL is used
  dispose_all()                              — test/shutdown helper

  session_scope(tenant_id, read_only=False)  — context-managed Session
  db_session(request)                        — FastAPI dependency

  TenantResolver                             — Host-header / X-Tenant-Id middleware

  get_student_skills(session, student_id)    — shared query (#22c)
  get_student_skill_count(session, student_id)
  get_student_profile(session, student_id)

Implemented across PRs #22a (engine + session + middleware),
#22b (canonical CREATE TABLE schema), and #22c (portal-service migrations
and shared-query layer).
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
from wfdos_common.db.queries import (
    get_student_profile,
    get_student_skill_count,
    get_student_skills,
)
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
    # shared queries
    "get_student_skills",
    "get_student_skill_count",
    "get_student_profile",
]
