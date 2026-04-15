import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database.models import Base
from wfdos_common.config import ConfigurationError

engine = None
SessionLocal = None


def init_db():
    """Initialize the grant-agent DB engine.

    DATABASE_URL must be set. A weak fallback default was removed in #19
    so misconfiguration fails loudly rather than silently running against
    a default-credential local database.

    TODO(#22): replaced by wfdos_common.db.engine.get_engine() with
    tenant-aware pooling. At that point this function disappears entirely.
    """
    global engine, SessionLocal
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ConfigurationError(
            "DATABASE_URL is required for the grant agent. "
            "Set it in your .env / environment as a standard PostgreSQL "
            "SQLAlchemy URL. The previous weak default was removed in #19."
        )
    engine = create_engine(database_url)
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)


def get_session():
    if SessionLocal is None:
        init_db()
    return SessionLocal()
