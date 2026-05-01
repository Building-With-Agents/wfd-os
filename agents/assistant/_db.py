"""Shared Postgres helpers for assistant-side agents.

bd_agent and marketing_agent both shelled out their own `_conn`,
`_query`, `_execute` plus a redundant `sys.path` + `pgconfig` fallback
block. Both files used the same wfd-os Postgres credentials that
`wfdos_common.config.PG_CONFIG` already exposes — the duplication was
purely an artifact of the bd-command-center checkpoint import landing
before the wfdos-common config story was wired through. Centralizing
here so a future schema or driver change only touches one file.

`_execute` accepts SQL with or without a `RETURNING` clause: when the
underlying cursor produces a row, the first column is returned;
otherwise we return `cursor.rowcount`. Marketing's INSERT-with-RETURNING
path needs the former, BD's UPDATE/DELETE path needs the latter.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable, Optional

import psycopg2
import psycopg2.extras

from wfdos_common.config import PG_CONFIG


def _conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(**PG_CONFIG)


def _query(sql: str, params: Optional[Iterable[Any]] = None) -> list[dict]:
    """Run a SELECT and return a list of dicts. datetime columns are
    converted to ISO-8601 strings so the result is JSON-safe for the
    LLM tool-result channel."""
    conn = _conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(sql, params or ())
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.isoformat()
        return rows
    finally:
        conn.close()


def _execute(sql: str, params: Optional[Iterable[Any]] = None) -> Any:
    """Run an INSERT/UPDATE/DELETE. Returns the first column of the
    first returned row when the SQL has a RETURNING clause; otherwise
    returns `cur.rowcount`."""
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        returned: Optional[tuple] = None
        try:
            returned = cur.fetchone()
        except psycopg2.ProgrammingError:
            # Statement produced no result set — RETURNING wasn't used.
            returned = None
        conn.commit()
        return returned[0] if returned else cur.rowcount
    finally:
        conn.close()


__all__ = ["_conn", "_query", "_execute"]
