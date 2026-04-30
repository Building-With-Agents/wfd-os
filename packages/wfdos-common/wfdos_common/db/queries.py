"""Shared SQL queries for wfd-os services.

The first two entries dedupe the near-identical skill-lookup SQL that
previously lived in both `agents/portal/student_api.py` and
`agents/portal/showcase_api.py`. Call sites migrate to these functions
as services are flipped to the engine factory.

Each function accepts either a SQLAlchemy Session (preferred for new code)
or a raw psycopg2 connection (so services mid-migration keep working
without fully converting to SQLAlchemy first).
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session


def get_student_skills(
    session_or_conn: Any,
    student_id: str | int,
) -> list[str]:
    """Return the distinct skill names for a student, sorted alphabetically.

    Dedupes:
      - student_api.py lines 81-87 (`SELECT DISTINCT sk.skill_name FROM
        student_skills ss JOIN skills sk ON sk.skill_id = ss.skill_id WHERE
        ss.student_id = %s ORDER BY sk.skill_name`)
      - showcase_api.py lines 322-327 (same query, different alias-level
        wrapping for the ranked_skills CTE)

    Callers pass either a SQLAlchemy Session or a raw psycopg2 connection.
    Returns a plain list[str] so callers' JSON-serialization paths don't
    change.
    """
    sql = """
        SELECT DISTINCT sk.skill_name
        FROM student_skills ss
        JOIN skills sk ON sk.skill_id = ss.skill_id
        WHERE ss.student_id = :student_id
        ORDER BY sk.skill_name
    """
    # SQLAlchemy Session path
    if isinstance(session_or_conn, Session):
        result = session_or_conn.execute(text(sql), {"student_id": student_id})
        return [row[0] for row in result]

    # Raw psycopg2 connection path — use %s + positional params so callers
    # mid-migration can pass their existing conn objects.
    raw_sql = sql.replace(":student_id", "%s")
    cur = session_or_conn.cursor()
    try:
        cur.execute(raw_sql, (student_id,))
        return [row[0] for row in cur.fetchall()]
    finally:
        cur.close()


def get_student_skill_count(
    session_or_conn: Any,
    student_id: str | int,
) -> int:
    """Count distinct skill_ids for a student. Used by student_api.py
    checklist + showcase_api.py per-student total_skill_count batch.
    """
    sql = """
        SELECT COUNT(DISTINCT skill_id)
        FROM student_skills
        WHERE student_id = :student_id
    """
    if isinstance(session_or_conn, Session):
        result = session_or_conn.execute(text(sql), {"student_id": student_id})
        return int(result.scalar() or 0)

    raw_sql = sql.replace(":student_id", "%s")
    cur = session_or_conn.cursor()
    try:
        cur.execute(raw_sql, (student_id,))
        row = cur.fetchone()
        return int(row[0] or 0) if row else 0
    finally:
        cur.close()


def get_student_profile(
    session_or_conn: Any,
    student_id: str | int,
) -> Optional[dict]:
    """Fetch a single student row as a dict. Returns None if not found.

    Dedupe target: `agents/portal/student_api.py` get_profile SELECT
    (line 62) and related SELECT in showcase_api.py. Column list is the
    union of what both services SELECT.
    """
    sql = """
        SELECT id, full_name, email, phone, city, state, zipcode,
               institution, degree, field_of_study, graduation_year,
               linkedin_url, github_url, portfolio_url,
               profile_completeness_score, missing_required, missing_preferred,
               showcase_eligible, showcase_active,
               pipeline_status, track, availability_status,
               resume_parsed, parse_confidence_score,
               created_at
        FROM students
        WHERE id = :student_id
    """
    # SQLAlchemy Session path — returns Row mappings as dicts
    if isinstance(session_or_conn, Session):
        result = session_or_conn.execute(text(sql), {"student_id": student_id})
        row = result.mappings().fetchone()
        return dict(row) if row else None

    # Raw psycopg2 path — use RealDictCursor for dict output
    import psycopg2.extras

    raw_sql = sql.replace(":student_id", "%s")
    cur = session_or_conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(raw_sql, (student_id,))
        row = cur.fetchone()
        return dict(row) if row else None
    finally:
        cur.close()
