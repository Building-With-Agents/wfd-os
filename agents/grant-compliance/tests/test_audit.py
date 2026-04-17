"""Tests for the audit log: append-only behavior and shape."""

from __future__ import annotations

from grant_compliance.audit.log import write_entry
from grant_compliance.db.models import AuditLog


def test_write_entry_appends_row(db):
    entry = write_entry(
        db,
        actor="test_agent",
        actor_kind="agent",
        action="test.action",
        target_type="transaction",
        target_id="abc-123",
        inputs={"foo": "bar"},
        outputs={"baz": 1},
        prompt="hello world",
    )
    db.commit()
    assert entry.id is not None
    assert entry.prompt_hash is not None
    assert len(entry.prompt_hash) == 64  # sha256 hex


def test_audit_entries_are_listable(db):
    for i in range(3):
        write_entry(
            db,
            actor=f"actor_{i}",
            actor_kind="human",
            action="test.iter",
        )
    db.commit()
    rows = db.query(AuditLog).all()
    assert len(rows) == 3


def test_prompt_is_hashed_not_stored(db):
    secret = "personally identifiable information"
    entry = write_entry(
        db,
        actor="a",
        actor_kind="agent",
        action="x",
        prompt=secret,
    )
    db.commit()
    # The hash should not equal the secret in any form
    assert entry.prompt_hash != secret
    # And the secret should not appear anywhere on the row
    assert secret not in str(entry.inputs)
    assert secret not in str(entry.outputs)
