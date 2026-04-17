"""/grants — read-only listing of grants."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from grant_compliance.api.schemas import GrantOut
from grant_compliance.db.models import Grant
from grant_compliance.db.session import get_db

router = APIRouter(prefix="/grants", tags=["grants"])


@router.get("", response_model=list[GrantOut])
def list_grants(db: Session = Depends(get_db)) -> list[Grant]:
    return list(db.execute(select(Grant)).scalars())


@router.get("/{grant_id}", response_model=GrantOut)
def get_grant(grant_id: str, db: Session = Depends(get_db)) -> Grant:
    from fastapi import HTTPException

    grant = db.get(Grant, grant_id)
    if not grant:
        raise HTTPException(status_code=404, detail="Grant not found")
    return grant
