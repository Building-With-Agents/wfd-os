"""
Recruiting (a.k.a. "job_board") DataSource abstraction.

Mirrors the Finance pattern in agents/finance/data_source.py — the API
service only talks through this interface, so a future swap (say,
from raw Postgres to a read-model backed by a vector search service)
is one-file surgery.

Pending-embedding behavior
--------------------------
When student embeddings don't exist yet (embeddings table holds zero
rows where entity_type='student'), every matching query short-circuits
and returns {"matching_status": "pending_student_index"} instead of
fake numbers. Same endpoints "light up" automatically the moment
embeddings land — callers don't change.

As of Phase 2D (2026-04-18) both sides are embedded with
text-embedding-3-small: 103 jobs_enriched rows + 146 student rows
(Tier A pool: institution + parsed resume + >=1 skill). Matching is
live; match_count per job and with_matches in workday_stats are
computed against COSINE_MATCH_THRESHOLD.
"""

from __future__ import annotations

import sys
import os
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional
from uuid import UUID, uuid4

import psycopg2
import psycopg2.extras

# Import pgconfig from scripts/ — matches the pattern in
# agents/marketing/api.py and the migration scripts.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "scripts"))
from pgconfig import PG_CONFIG  # type: ignore  # noqa: E402


# In-flight application statuses (per spec). Applications in these
# statuses count toward a job's "in_flight_app_count" and a workday's
# "apps_in_flight" tally. Draft + rejected + hired stay out.
IN_FLIGHT_APP_STATUSES = (
    "submitted_for_review",
    "approved",
    "packaged",
    "sent",
    "delivered",
)

# Cosine-similarity floor for counting a student as a "match" for a job.
# Picked during Phase 2D Stage 4 validation (see scripts/_validate_*.py):
# - Tech students vs tech jobs score 0.49-0.60 → 2-5 matches each
# - Thin-profile students (minimal skills) score <0.45 → correctly zero
# - Workforce-analytics students vs workforce jobs score 0.54-0.57
# 0.50 is the cleanest cutoff between "real signal" and "grasping".
COSINE_MATCH_THRESHOLD = 0.50


class DataSource(ABC):
    """Shared interface used by api.py."""

    @abstractmethod
    def embeddings_status(self) -> dict: ...

    @abstractmethod
    def list_jobs(self, filters: dict, limit: int = 50, offset: int = 0) -> list[dict]: ...

    @abstractmethod
    def get_job(self, job_id: int) -> Optional[dict]: ...

    @abstractmethod
    def job_matches(self, job_id: int, limit: int = 10) -> dict: ...

    @abstractmethod
    def list_students(self, filters: dict, limit: int = 50, offset: int = 0) -> dict: ...

    @abstractmethod
    def student_matches(self, student_id: str, limit: int = 10) -> dict: ...

    @abstractmethod
    def create_application(self, student_id: str, job_id: int, initiated_by: str) -> dict: ...

    @abstractmethod
    def workday_stats(self) -> dict: ...


# ---------------------------------------------------------------------------
# Postgres implementation
# ---------------------------------------------------------------------------


def _conn():
    """Fresh psycopg2 connection. No pooling today — Python services run
    low-traffic internal traffic, every call is one query."""
    return psycopg2.connect(**PG_CONFIG)


def _dictfetchall(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _serialize(row: dict) -> dict:
    """JSON-safe dict: UUID → str, datetime → isoformat. Arrays stay as
    Python lists. Leaves None untouched."""
    import datetime as _dt
    out = {}
    for k, v in row.items():
        if isinstance(v, UUID):
            out[k] = str(v)
        elif isinstance(v, (_dt.datetime, _dt.date)):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


class PostgresDataSource(DataSource):
    """Reads/writes the wfd_os schema via psycopg2."""

    # ---- embeddings health ------------------------------------------------

    def embeddings_status(self) -> dict:
        """Count embeddings by entity_type. Used by matching endpoints to
        decide between pending_student_index and live cosine."""
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT entity_type, COUNT(*) FROM embeddings GROUP BY entity_type"
            )
            counts = {r[0]: r[1] for r in cur.fetchall()}
        return {
            "by_entity_type": counts,
            "student_count": counts.get("student", 0),
            "jobs_enriched_count": counts.get("jobs_enriched", 0),
            "student_index_ready": counts.get("student", 0) > 0,
        }

    # ---- jobs -------------------------------------------------------------

    def list_jobs(self, filters: dict, limit: int = 50, offset: int = 0) -> list[dict]:
        clauses, params = _build_job_filters(filters)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        # match_count per job: student embeddings whose cosine similarity
        # to the job embedding clears COSINE_MATCH_THRESHOLD. Subquery
        # runs once per returned job; with ~150 students and an HNSW
        # index the fan-out is well under 10ms/job. Returns 0 for jobs
        # that have no corresponding row in the embeddings table yet
        # (COALESCE over the inner subquery's NULL).
        cosine_distance_max = 1 - COSINE_MATCH_THRESHOLD
        sql = f"""
            SELECT
              j.*,
              (SELECT COUNT(*) FROM applications a
                 WHERE a.job_id = j.job_id
                   AND a.status = ANY(%s)) AS in_flight_app_count,
              COALESCE((
                SELECT COUNT(*) FROM embeddings e_s
                WHERE e_s.entity_type = 'student'
                  AND (e_s.embedding <=> (
                    SELECT embedding FROM embeddings
                    WHERE entity_type = 'jobs_enriched'
                      AND entity_id = j.job_id::text
                  )) <= %s
              ), 0) AS match_count
            FROM v_jobs_active j
            {where}
            ORDER BY j.posted_at DESC NULLS LAST, j.job_id DESC
            LIMIT %s OFFSET %s
        """
        with _conn() as conn, conn.cursor() as cur:
            # Parameter order tracks SQL %s order: in-flight statuses,
            # cosine distance ceiling, then filter params, then paging.
            cur.execute(
                sql,
                [list(IN_FLIGHT_APP_STATUSES), cosine_distance_max]
                + params
                + [limit, offset],
            )
            rows = _dictfetchall(cur)
        return [_serialize(r) for r in rows]

    def get_job(self, job_id: int) -> Optional[dict]:
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM v_jobs_active WHERE job_id = %s",
                (job_id,),
            )
            rows = _dictfetchall(cur)
        if not rows:
            return None
        return _serialize(rows[0])

    def job_matches(self, job_id: int, limit: int = 10) -> dict:
        emb = self.embeddings_status()
        if not emb["student_index_ready"]:
            return {
                "matches": [],
                "matching_status": "pending_student_index",
                "note": "Student embeddings not yet generated",
                "embeddings_status": emb,
            }
        # When embeddings exist, cosine match students against the job.
        # Dropped in for future; query is live-ready against pgvector.
        sql = """
            SELECT
              s.id,
              s.full_name,
              s.cohort_id,
              s.pipeline_status,
              1 - (e_s.embedding <=> e_j.embedding) AS cosine,
              EXISTS (
                SELECT 1 FROM applications a
                WHERE a.student_id = s.id AND a.job_id = %s
              ) AS existing_application
            FROM embeddings e_s
            JOIN students s ON s.id::text = e_s.entity_id
            CROSS JOIN (
              SELECT embedding FROM embeddings
              WHERE entity_type = 'jobs_enriched' AND entity_id = %s
            ) e_j
            WHERE e_s.entity_type = 'student'
            ORDER BY e_s.embedding <=> e_j.embedding
            LIMIT %s
        """
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (job_id, str(job_id), limit))
            rows = _dictfetchall(cur)
        matches = []
        for r in rows:
            d = _serialize(r)
            # Placeholder for skill_overlap per spec — will compute from
            # student_skills / job_listing_skills join once the matching
            # pipeline is promoted from prototype to production.
            d["skill_overlap"] = None
            d["cohort_label"] = d.get("cohort_id") or "(unassigned)"
            matches.append(d)
        return {
            "matches": matches,
            "matching_status": "ready",
            "embeddings_status": emb,
        }

    # ---- students ---------------------------------------------------------

    def list_students(self, filters: dict, limit: int = 50, offset: int = 0) -> dict:
        clauses, params = _build_student_filters(filters)
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
        sql = f"""
            SELECT
              id, full_name, email, city, state, institution,
              degree, field_of_study, graduation_year,
              cohort_id, track, pipeline_status, pipeline_stage,
              profile_completeness_score,
              showcase_eligible, showcase_active
            FROM students
            {where}
            ORDER BY last_active_date DESC NULLS LAST, id
            LIMIT %s OFFSET %s
        """
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(sql, params + [limit, offset])
            rows = [_serialize(r) for r in _dictfetchall(cur)]

        emb = self.embeddings_status()
        if not emb["student_index_ready"]:
            return {
                "students": rows,
                "matching_status": "pending_student_index",
                "note": "Student embeddings not yet generated — per-student job recommendations unavailable",
                "embeddings_status": emb,
            }
        # When embeddings exist, attach top 3 job matches per student.
        # Per-student recommendations run as a second query per row; for
        # the initial MVP that's fine — 50-row pages are cheap.
        for r in rows:
            r["top_matches"] = self.student_matches(r["id"], limit=3)["matches"]
        return {
            "students": rows,
            "matching_status": "ready",
            "embeddings_status": emb,
        }

    def student_matches(self, student_id: str, limit: int = 10) -> dict:
        emb = self.embeddings_status()
        if not emb["student_index_ready"]:
            return {
                "matches": [],
                "matching_status": "pending_student_index",
                "note": "Student embeddings not yet generated",
                "embeddings_status": emb,
            }
        sql = """
            SELECT
              j.job_id, j.title, j.company, j.city, j.state, j.is_remote,
              1 - (e_j.embedding <=> e_s.embedding) AS cosine,
              EXISTS (
                SELECT 1 FROM applications a
                WHERE a.student_id = %s::uuid AND a.job_id = j.job_id
              ) AS existing_application
            FROM embeddings e_j
            JOIN v_jobs_active j ON j.job_id::text = e_j.entity_id
            CROSS JOIN (
              SELECT embedding FROM embeddings
              WHERE entity_type = 'student' AND entity_id = %s
            ) e_s
            WHERE e_j.entity_type = 'jobs_enriched'
            ORDER BY e_j.embedding <=> e_s.embedding
            LIMIT %s
        """
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(sql, (student_id, student_id, limit))
            rows = [_serialize(r) for r in _dictfetchall(cur)]
        return {
            "matches": rows,
            "matching_status": "ready",
            "embeddings_status": emb,
        }

    # ---- applications -----------------------------------------------------

    def create_application(self, student_id: str, job_id: int, initiated_by: str) -> dict:
        new_id = str(uuid4())
        with _conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO applications
                    (id, student_id, job_id, initiated_by, status)
                VALUES (%s, %s, %s, %s, 'draft')
                RETURNING id, student_id, job_id, status, initiated_by,
                          created_at, last_status_change_at
                """,
                (new_id, student_id, job_id, initiated_by),
            )
            row = _dictfetchall(cur)[0]
            conn.commit()
        return _serialize(row)

    # ---- stats ------------------------------------------------------------

    def workday_stats(self) -> dict:
        emb = self.embeddings_status()
        with _conn() as conn, conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) FROM v_jobs_active")
            open_jobs = cur.fetchone()[0]
            cur.execute(
                "SELECT COUNT(*) FROM applications WHERE status = ANY(%s)",
                (list(IN_FLIGHT_APP_STATUSES),),
            )
            apps_in_flight = cur.fetchone()[0]
        # with_matches: 0 until student embeddings land. When they do,
        # count jobs that have >=1 student above the cosine threshold.
        with_matches = 0 if not emb["student_index_ready"] else _count_jobs_with_matches()
        return {
            "open_jobs": open_jobs,
            "with_matches": with_matches,
            "apps_in_flight": apps_in_flight,
            "matching_status": "ready" if emb["student_index_ready"] else "pending_student_index",
            "embeddings_status": emb,
        }


def _count_jobs_with_matches() -> int:
    """Count jobs with at least one student match above COSINE_MATCH_THRESHOLD.

    Used by workday_stats for the "With matches" hero cell. Runs one
    cross-table query against the embeddings table; at today's scale
    (103 jobs × ~150 students) this returns in ~100ms. Both sides were
    embedded with text-embedding-3-small, so cosine is directly
    comparable.
    """
    cosine_distance_max = 1 - COSINE_MATCH_THRESHOLD
    sql = """
        SELECT COUNT(DISTINCT e_j.entity_id)
        FROM embeddings e_j
        JOIN embeddings e_s
          ON e_s.entity_type = 'student'
         AND (e_j.embedding <=> e_s.embedding) <= %s
        WHERE e_j.entity_type = 'jobs_enriched'
    """
    with _conn() as conn, conn.cursor() as cur:
        cur.execute(sql, (cosine_distance_max,))
        return cur.fetchone()[0] or 0


# ---------------------------------------------------------------------------
# Filter builders (shared SQL WHERE construction — keeps api handlers lean)
# ---------------------------------------------------------------------------


def _build_job_filters(filters: dict) -> tuple[list[str], list]:
    clauses: list[str] = []
    params: list = []
    q = filters.get("q")
    if q:
        clauses.append("(j.title ILIKE %s OR j.company ILIKE %s OR j.description ILIKE %s)")
        like = f"%{q}%"
        params.extend([like, like, like])
    if filters.get("city"):
        clauses.append("j.city ILIKE %s")
        params.append(filters["city"])
    if filters.get("state"):
        clauses.append("j.state ILIKE %s")
        params.append(filters["state"])
    if filters.get("is_remote") is not None:
        clauses.append("j.is_remote = %s")
        params.append(filters["is_remote"])
    if filters.get("seniority"):
        clauses.append("j.seniority ILIKE %s")
        params.append(filters["seniority"])
    if filters.get("employment_type"):
        clauses.append("j.employment_type ILIKE %s")
        params.append(filters["employment_type"])
    return clauses, params


def _build_student_filters(filters: dict) -> tuple[list[str], list]:
    clauses: list[str] = []
    params: list = []
    if filters.get("cohort"):
        clauses.append("cohort_id = %s")
        params.append(filters["cohort"])
    if filters.get("pipeline_status"):
        clauses.append("pipeline_status = %s")
        params.append(filters["pipeline_status"])
    q = filters.get("q")
    if q:
        clauses.append("(full_name ILIKE %s OR email ILIKE %s OR institution ILIKE %s)")
        like = f"%{q}%"
        params.extend([like, like, like])
    return clauses, params


# ---------------------------------------------------------------------------
# Default factory
# ---------------------------------------------------------------------------


def default_source() -> DataSource:
    """Single source for the recruiting API. Env-var hook for future swap."""
    src = os.environ.get("RECRUITING_SOURCE", "postgres").lower()
    if src == "postgres":
        return PostgresDataSource()
    raise ValueError(f"Unknown RECRUITING_SOURCE: {src!r}")
