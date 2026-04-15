"""wfdos_common.db — multi-tenant SQLAlchemy engine factory + shared queries.

STATUS: STUB — implementation lands in Building-With-Agents/wfd-os#22.

Target scope (from #22):
- wfdos_common.db.engine.get_engine(tenant_id, read_only=False) — per-tenant
  cached engines; separate read-only + read-write pools (supports the
  Tier-1 stripped-.env deploy).
- wfdos_common.db.session — scoped session factory.
- wfdos_common.db.middleware.TenantResolver — FastAPI middleware: Host header
  or X-Tenant-Id → tenant_id resolution.
- wfdos_common.db.queries — shared queries (deduping the skill-lookup and
  profile-lookup SQL currently duplicated across portal services).

Replaces the 28 raw psycopg2 call sites across agents/.
"""
