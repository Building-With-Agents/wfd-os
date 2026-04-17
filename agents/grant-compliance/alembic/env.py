"""Alembic environment. Wired to use the same Base metadata as the app.

Schema awareness: all grant-compliance tables live in the
`grant_compliance` Postgres schema (set on Base.metadata). We tell
Alembic to:
  - include_schemas=True so autogenerate diffs our schema vs. the DB
    rather than assuming every table belongs in public
  - version_table_schema=grant_compliance so the alembic_version
    tracking table lives inside our schema (not in public)

Without include_schemas, Alembic autogenerate would try to create every
table on every run because it'd see our schema-qualified models as
"missing" from the public schema it defaults to inspecting.
"""

from __future__ import annotations

from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from grant_compliance.config import get_settings
from grant_compliance.db.models import Base

SCHEMA_NAME = "grant_compliance"

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _include_name(name, type_, parent_names):
    """Scope autogenerate to ONLY the grant_compliance schema.

    Without this filter, include_schemas=True causes Alembic to diff against
    every schema in the database — including `public`, which in wfd-os
    contains the platform's other tables (students, company_scores,
    prospect_companies, etc.). Autogenerate would then try to DROP those
    tables because they're not in our Base.metadata. That's a disaster.

    This callback tells Alembic: for `schema` objects, only consider
    grant_compliance. Everything else (tables, indexes, etc.) is included
    normally, but only within our schema because we've narrowed the schema
    inspection.
    """
    if type_ == "schema":
        return name == SCHEMA_NAME
    return True


def _configure_common(**extra) -> dict:
    """Common kwargs passed to context.configure() in both online and offline."""
    return dict(
        target_metadata=target_metadata,
        include_schemas=True,
        include_name=_include_name,
        version_table_schema=SCHEMA_NAME,
        **extra,
    )


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        **_configure_common(),
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, **_configure_common())
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
