"""SQLAlchemy engine factory for wfd-os services.

Produces per-tenant, per-mode (read-only vs read-write) SQLAlchemy engines
on demand. Engines are cached so repeated calls with the same arguments
return the same Engine object — no connection-pool thrash.

The factory supports three URL-resolution strategies for a tenant:

1. **Explicit URL** passed to `get_engine(url=...)`. Used by tests that
   spin up sqlite-in-memory DBs.
2. **Per-tenant registry** — `register_tenant(tenant_id, url)` maps a
   tenant_id to a DB URL ahead of time. This is how the platform's
   multi-tenant resolver (see `wfdos_common.db.middleware`) selects a
   DB per Host header.
3. **Fallback to `DATABASE_URL` or `settings.pg.*`** — when no tenant is
   registered, the factory builds a URL from the flagship settings and
   uses it. This is what happens for the Waifinder flagship tenant on a
   single-DB deployment.

Read-only mode adds `default_transaction_read_only=on` at the session
level so queries that try to INSERT/UPDATE/DELETE raise a clear Postgres
error. That's the Tier-1 stripped-`.env` safety net from #25: services
started without write privileges fail fast on any write attempt.

See #22 for the full scope; this file is PR #22a (engine + session +
middleware) only — canonical schema lands in #22b, service migrations
in #22c.
"""

from __future__ import annotations

from threading import Lock
from typing import Optional
from urllib.parse import quote_plus

from sqlalchemy import Engine, create_engine, event

# ---------------------------------------------------------------------------
# Tenant registry
# ---------------------------------------------------------------------------

_tenant_urls: dict[str, str] = {}
_registry_lock = Lock()


def register_tenant(tenant_id: str, url: str) -> None:
    """Register a DB URL for a tenant. Called by deployment code on startup
    for every tenant the service will handle. Unknown tenants fall back to
    the flagship URL from `settings.pg.*`.
    """
    with _registry_lock:
        _tenant_urls[tenant_id] = url


def clear_tenant_registry() -> None:
    """Test helper: drop all registered tenants."""
    with _registry_lock:
        _tenant_urls.clear()


def registered_tenants() -> list[str]:
    """Introspection helper — returns the list of tenant_ids that have a
    URL registered. Useful for startup logging.
    """
    with _registry_lock:
        return sorted(_tenant_urls.keys())


# ---------------------------------------------------------------------------
# URL resolution
# ---------------------------------------------------------------------------

def _url_from_settings() -> str:
    """Build a postgresql URL from wfdos_common.config.settings.pg.*.

    Uses psycopg2 dialect. Password is URL-encoded so special characters
    in the DB password don't break the URL parse. Returns a URL with the
    `sslmode=require` query param when the host is an Azure managed-PG
    hostname; local-docker hosts skip it.
    """
    # Late import so this module can be imported in environments where
    # wfdos_common.config is mocked (tests) or not yet installed.
    from wfdos_common.config import settings

    # DATABASE_URL override wins if set — lets deployments bypass pg.*
    # and provide a full URL (e.g. with custom SSL cert paths).
    import os

    if db_url := os.getenv("DATABASE_URL"):
        return db_url

    host = settings.pg.host or "localhost"
    port = settings.pg.port or 5432
    user = settings.pg.user or "postgres"
    db = settings.pg.database or "wfdos"
    pwd = settings.pg.password or ""

    userinfo = user
    if pwd:
        userinfo = f"{user}:{quote_plus(pwd)}"

    base = f"postgresql+psycopg2://{userinfo}@{host}:{port}/{db}"
    # Heuristic: Azure-managed PG requires SSL; localhost doesn't.
    if "azure.com" in host or "rds.amazonaws.com" in host:
        return f"{base}?sslmode=require"
    return base


def resolve_url(tenant_id: str) -> str:
    """Pick the URL for a tenant. Registry first, settings fallback."""
    with _registry_lock:
        if tenant_id in _tenant_urls:
            return _tenant_urls[tenant_id]
    return _url_from_settings()


# ---------------------------------------------------------------------------
# Engine cache
# ---------------------------------------------------------------------------

_engine_cache: dict[tuple[str, bool], Engine] = {}
_engine_lock = Lock()


def get_engine(
    tenant_id: Optional[str] = None,
    *,
    read_only: bool = False,
    url: Optional[str] = None,
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_pre_ping: bool = True,
    echo: bool = False,
) -> Engine:
    """Return (and cache) a SQLAlchemy Engine for the given tenant + mode.

    Args:
        tenant_id: tenant key. Defaults to `settings.tenancy.default_tenant_id`
            (typically 'waifinder-flagship') when None.
        read_only: if True, every session derived from this engine sets
            `default_transaction_read_only=on`, causing any write to raise
            a Postgres error. Different physical engine from the read-write
            one (separate connection pool).
        url: explicit override. When provided, tenant_id is only used as a
            cache key — URL is not looked up.
        pool_size, max_overflow: SQLAlchemy QueuePool params.
        pool_pre_ping: default True — catches stale connections after PG
            restart / network blip.
        echo: set True for debug-level SQL logging.

    Returns:
        The cached SQLAlchemy Engine. Subsequent calls with identical
        (tenant_id, read_only) return the same object.
    """
    if tenant_id is None:
        from wfdos_common.config import settings

        tenant_id = settings.tenancy.default_tenant_id

    cache_key = (tenant_id, read_only)

    with _engine_lock:
        cached = _engine_cache.get(cache_key)
        if cached is not None:
            return cached

        effective_url = url or resolve_url(tenant_id)

        # SQLAlchemy's SingletonThreadPool (SQLite default) rejects
        # QueuePool kwargs. Pass them only when the dialect actually
        # supports them.
        create_kwargs: dict = {"pool_pre_ping": pool_pre_ping, "echo": echo}
        if not effective_url.startswith("sqlite"):
            create_kwargs["pool_size"] = pool_size
            create_kwargs["max_overflow"] = max_overflow

        engine = create_engine(effective_url, **create_kwargs)

        if read_only:
            _attach_read_only_guard(engine)

        _engine_cache[cache_key] = engine
        return engine


def _attach_read_only_guard(engine: Engine) -> None:
    """Install a connect-time hook that sets the session to read-only.

    Works for both Postgres (native `default_transaction_read_only`) and
    SQLite (sets a `PRAGMA query_only = 1`). Tests run against sqlite
    in-memory so both paths matter.
    """
    dialect_name = engine.dialect.name

    if dialect_name == "postgresql":
        @event.listens_for(engine, "connect")
        def _pg_read_only(dbapi_conn, _record):
            with dbapi_conn.cursor() as cur:
                cur.execute("SET SESSION default_transaction_read_only = ON")
    elif dialect_name == "sqlite":
        @event.listens_for(engine, "connect")
        def _sqlite_read_only(dbapi_conn, _record):
            cur = dbapi_conn.cursor()
            cur.execute("PRAGMA query_only = 1")
            cur.close()
    # Other dialects: read-only is best-effort; raise a clear warning rather
    # than silently letting writes through.
    else:  # pragma: no cover
        import warnings

        warnings.warn(
            f"read_only guard not implemented for dialect {dialect_name!r}; "
            "writes from this engine are NOT protected at the engine level.",
            RuntimeWarning,
            stacklevel=2,
        )


def dispose_all() -> None:
    """Close every cached engine. Called at process shutdown; test helper."""
    with _engine_lock:
        for engine in _engine_cache.values():
            engine.dispose()
        _engine_cache.clear()
