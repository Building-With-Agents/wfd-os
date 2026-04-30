"""Session factory on top of `wfdos_common.db.engine.get_engine`.

Two access patterns:

1. Context manager (preferred for new code)::

       from wfdos_common.db.session import session_scope

       with session_scope(tenant_id) as session:
           rows = session.execute(...).fetchall()

   Commits on clean exit; rolls back on exception; closes always.

2. FastAPI dependency (matches existing portal-API patterns)::

       from wfdos_common.db.session import db_session

       @app.get("/api/x")
       def handler(session: Session = Depends(db_session)):
           ...

   The dependency resolves `tenant_id` from `request.state.tenant_id`
   (set by `wfdos_common.db.middleware.TenantResolver`) and hands back
   a session that's automatically closed when the request ends.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator, Optional

from sqlalchemy.orm import Session, sessionmaker

from wfdos_common.db.engine import get_engine


@contextmanager
def session_scope(
    tenant_id: Optional[str] = None,
    *,
    read_only: bool = False,
) -> Iterator[Session]:
    """Context-managed Session. Commits on clean exit; rolls back on exception."""
    engine = get_engine(tenant_id, read_only=read_only)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    session = factory()
    try:
        yield session
        if not read_only:
            session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def db_session(request=None, read_only: bool = False) -> Iterator[Session]:
    """FastAPI dependency. Reads tenant from request.state (set by middleware)
    and yields a session that's closed on teardown.

    Usage::

        from fastapi import Depends
        from wfdos_common.db.session import db_session

        @app.get("/api/x")
        def handler(session = Depends(db_session)):
            ...

    When tenant middleware isn't installed, `request.state.tenant_id` is
    missing and the session defaults to the flagship tenant (via
    `settings.tenancy.default_tenant_id`).
    """
    tenant_id: Optional[str] = None
    if request is not None:
        tenant_id = getattr(request.state, "tenant_id", None)
    with session_scope(tenant_id, read_only=read_only) as session:
        yield session
