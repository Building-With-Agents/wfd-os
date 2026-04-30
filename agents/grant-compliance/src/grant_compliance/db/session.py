"""Database session management."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from grant_compliance.config import get_settings
from grant_compliance.db.models import Base

_settings = get_settings()

# SQLite needs a special connect_args; Postgres does not.
_connect_args = {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}

engine = create_engine(_settings.database_url, connect_args=_connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_db() -> None:
    """Create all tables. For dev use; production uses Alembic migrations."""
    Base.metadata.create_all(engine)


def get_db() -> Iterator[Session]:
    """FastAPI dependency: yields a session, ensures it's closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
