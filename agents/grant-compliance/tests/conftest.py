"""Pytest configuration. Provides an in-memory SQLite session per test.

SQLite doesn't have real schemas. Our production models live in the
`grant_compliance` Postgres schema (set on Base.metadata). To let SQLite
tests reuse the same metadata, we `ATTACH DATABASE ':memory:' AS
grant_compliance` on every connection — SQLite's native way of
simulating a schema. Without this, `CREATE TABLE grant_compliance.funders`
fails with "unknown database grant_compliance".
"""

from __future__ import annotations

from collections.abc import Iterator

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from grant_compliance.db.models import Base


@pytest.fixture
def db() -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})

    # SQLite has no real schemas. Attach an in-memory DB under the
    # `grant_compliance` name on every new connection so schema-qualified
    # table references work.
    @event.listens_for(engine, "connect")
    def _attach_grant_compliance_schema(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("ATTACH DATABASE ':memory:' AS grant_compliance")
        cursor.close()

    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
