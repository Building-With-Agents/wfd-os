"""Audit log writer.

This is the ONLY sanctioned way to write to the audit_log table.
Audit log rows are immutable: never UPDATE or DELETE them. If something
went wrong, write a compensating entry instead.
"""

from __future__ import annotations

import hashlib
from typing import Any, Literal

from sqlalchemy.orm import Session

from grant_compliance.db.models import AuditLog

ActorKind = Literal["human", "agent"]


def write_entry(
    db: Session,
    *,
    actor: str,
    actor_kind: ActorKind,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    inputs: dict[str, Any] | None = None,
    outputs: dict[str, Any] | None = None,
    model: str | None = None,
    prompt: str | None = None,
    note: str | None = None,
) -> AuditLog:
    """Append an entry to the audit log.

    `prompt` is hashed (not stored verbatim) to avoid leaking PII into the log
    while still allowing reproducibility checks. If you need the full prompt
    for debugging, log it separately to your application logs.
    """
    entry = AuditLog(
        actor=actor,
        actor_kind=actor_kind,
        action=action,
        target_type=target_type,
        target_id=target_id,
        inputs=inputs or {},
        outputs=outputs or {},
        model=model,
        prompt_hash=_hash(prompt) if prompt else None,
        note=note,
    )
    db.add(entry)
    db.flush()  # assign id, but defer commit to caller's transaction
    return entry


def _hash(s: str) -> str:
    return hashlib.sha256(s.encode("utf-8")).hexdigest()
