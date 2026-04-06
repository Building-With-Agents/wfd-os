import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database.models import Base

engine = None
SessionLocal = None


def init_db():
    global engine, SessionLocal
    engine = create_engine(os.getenv("DATABASE_URL", "postgresql://postgres:password@localhost:5432/cfa_grants"))
    SessionLocal = sessionmaker(bind=engine)
    Base.metadata.create_all(bind=engine)


def get_session():
    if SessionLocal is None:
        init_db()
    return SessionLocal()
