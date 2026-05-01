"""
Recruiting (a.k.a. job_board) API — Phase 2B.

URL prefix for the portal: /api/recruiting/*
Service port:              8012
Backing data:              wfd_os Postgres via PostgresDataSource

Endpoints
  GET  /jobs
       Query: q, city, state, is_remote, seniority, employment_type,
              limit (default 50), offset (default 0)
       Rows from v_jobs_active + match_count (0 until student
       embeddings land) + in_flight_app_count

  GET  /jobs/{job_id}                    Single job, full v_jobs_active row
  GET  /jobs/{job_id}/matches?limit=10   Top-N student matches.
                                         Returns matching_status:
                                         "pending_student_index" when
                                         no student embeddings yet.

  GET  /students                         Query: cohort, pipeline_status, q
  GET  /students/{id}/matches?limit=10   Top-N job matches for a student.

  POST /applications
       Body: { student_id, job_id, initiated_by }
       Inserts row with status='draft', returns new id + timestamps.

  GET  /stats/workday                    open_jobs / with_matches / apps_in_flight
  GET  /health

Recruiting UI doesn't exist yet — endpoints only (Phase 2C builds
the Workday view that consumes these). The /api/recruiting rewrite
goes in portal/student/next.config.mjs in the same commit so the
plumbing is ready when the UI lands.

Directory-naming note: folder is agents/job_board/ with an
underscore (not hyphen) so Python can import agents.job_board.api
cleanly for uvicorn. The sidebar-facing language stays "Recruiting"
— see the URL prefix and all user-visible copy.

Run: uvicorn agents.job_board.api:app --reload --port 8012
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Windows cp1252 safety — matches the pattern in cockpit_api.py.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env", override=False)
except ImportError:  # pragma: no cover
    pass

from agents.job_board.data_source import DataSource, default_source  # noqa: E402
from agents.job_board import match_narrative as mn  # noqa: E402
from wfdos_common.config import settings  # noqa: E402


app = FastAPI(title="WFD OS Recruiting API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.platform.allowed_origins,
    allow_origin_regex=settings.platform.allowed_origin_regex,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    t0 = time.perf_counter()
    response = await call_next(request)
    dur_ms = (time.perf_counter() - t0) * 1000
    print(
        f"[recruiting_api] {request.method} {request.url.path} "
        f"-> {response.status_code} | {dur_ms:.1f}ms",
        flush=True,
    )
    return response


_SOURCE: DataSource = default_source()


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class ApplicationCreate(BaseModel):
    student_id: str
    job_id: int
    initiated_by: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@app.get("/health")
def health():
    return {"ok": True, "service": "recruiting_api", "version": app.version}


@app.get("/jobs")
def list_jobs(
    q: Optional[str] = None,
    city: Optional[str] = None,
    state: Optional[str] = None,
    is_remote: Optional[bool] = None,
    seniority: Optional[str] = None,
    employment_type: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    filters = {
        "q": q,
        "city": city,
        "state": state,
        "is_remote": is_remote,
        "seniority": seniority,
        "employment_type": employment_type,
    }
    rows = _SOURCE.list_jobs(filters, limit=limit, offset=offset)
    return {"jobs": rows, "count": len(rows), "limit": limit, "offset": offset}


@app.get("/jobs/{job_id}")
def get_job(job_id: int):
    row = _SOURCE.get_job(job_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return row


@app.get("/jobs/{job_id}/matches")
def job_matches(job_id: int, limit: int = Query(10, le=50)):
    # Confirm the job exists before running the match query so the user
    # gets a clean 404 on a bad id (not an opaque empty match list).
    if _SOURCE.get_job(job_id) is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return _SOURCE.job_matches(job_id, limit=limit)


@app.get("/students")
def list_students(
    cohort: Optional[str] = None,
    pipeline_status: Optional[str] = None,
    q: Optional[str] = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
):
    return _SOURCE.list_students(
        {"cohort": cohort, "pipeline_status": pipeline_status, "q": q},
        limit=limit,
        offset=offset,
    )


@app.get("/students/{student_id}")
def get_student(student_id: str):
    row = _SOURCE.get_student(student_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
    return {"student": row}


@app.get("/students/{student_id}/matches")
def student_matches(student_id: str, limit: int = Query(10, le=50)):
    return _SOURCE.student_matches(student_id, limit=limit)


@app.get("/students/{student_id}/applications/{job_id}")
def get_student_application_for_job(student_id: str, job_id: int):
    """Duplicate-check endpoint for the student-drill 'Initiate
    Application' button. Returns { application: row } when present,
    { application: null } when not — never 404 (absence is meaningful).
    """
    row = _SOURCE.get_student_application_for_job(student_id, job_id)
    return {"application": row}


MATCH_NARRATIVE_MAX_AGE_DAYS = 30


@app.get("/students/{student_id}/match-narrative")
def get_match_narrative(student_id: str, job_id: int):
    """Phase 2G — return the LLM-generated recruiter's note for the
    (student, job) pair. Cache by input_hash; regenerate when inputs
    change or the cached row is older than MATCH_NARRATIVE_MAX_AGE_DAYS.

    Response shape on success:
      {
        "verdict_line": str,
        "narrative_text": str,
        "match_strengths": [{area, evidence}],
        "match_gaps": [{area, note}],
        "match_partial": [],
        "cosine_similarity": float,
        "calibration_label": str,
        "generated_at": isostring,
        "cached": bool,
      }

    On generation failure, returns 200 with:
      { "error": "narrative_generation_failed",
        "cosine_similarity": float, "calibration_label": str }
    so the UI can render a clean fallback without reading error codes.
    """
    student = _SOURCE.get_student(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail=f"Student {student_id} not found")
    job = _SOURCE.get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    cosine = _SOURCE.get_cosine_for_pair(student_id, job_id)
    if cosine is None:
        # No embeddings on one side — can't calibrate. Surface cleanly.
        return {
            "error": "no_embedding",
            "detail": "Missing embedding for student or job; can't score match.",
        }
    label = mn.calibration_label(cosine)
    input_hash = mn.compute_input_hash(student, job)

    # Cache hit — return fast without touching the LLM.
    cached = _SOURCE.get_cached_narrative(
        student_id, job_id, input_hash, MATCH_NARRATIVE_MAX_AGE_DAYS
    )
    if cached:
        return {
            "verdict_line": cached["verdict_line"],
            "narrative_text": cached["narrative_text"],
            "match_strengths": cached["match_strengths"] or [],
            "match_gaps": cached["match_gaps"] or [],
            "match_partial": cached["match_partial"] or [],
            "cosine_similarity": float(cached["cosine_similarity"]),
            "calibration_label": cached["calibration_label"],
            "generated_at": cached["generated_at"],
            "cached": True,
        }

    # Cache miss — compute + generate + persist.
    overlap = mn.compute_overlap(student, job)
    try:
        narrative = mn.generate_narrative(student, job, overlap, cosine, label)
    except mn.NarrativeError as e:
        print(f"[match_narrative] generate failed student={student_id} "
              f"job={job_id}: {e}", flush=True)
        return {
            "error": "narrative_generation_failed",
            "cosine_similarity": cosine,
            "calibration_label": label,
        }

    saved = _SOURCE.upsert_narrative(
        student_id=student_id,
        job_id=job_id,
        verdict_line=narrative["verdict_line"],
        narrative_text=narrative["narrative_text"],
        match_strengths=overlap["strong_matches"],
        match_gaps=overlap["gaps"],
        match_partial=overlap["partial_matches"],
        calibration_label=label,
        cosine_similarity=cosine,
        input_hash=input_hash,
    )
    return {
        "verdict_line": saved["verdict_line"],
        "narrative_text": saved["narrative_text"],
        "match_strengths": saved["match_strengths"] or [],
        "match_gaps": saved["match_gaps"] or [],
        "match_partial": saved["match_partial"] or [],
        "cosine_similarity": float(saved["cosine_similarity"]),
        "calibration_label": saved["calibration_label"],
        "generated_at": saved["generated_at"],
        "cached": False,
    }


@app.post("/applications", status_code=201)
def create_application(body: ApplicationCreate):
    try:
        row = _SOURCE.create_application(
            student_id=body.student_id,
            job_id=body.job_id,
            initiated_by=body.initiated_by,
        )
    except Exception as e:
        # Common cases: invalid uuid, missing job_id, fk violation.
        # Surface the message so the frontend shows something useful.
        raise HTTPException(status_code=400, detail=str(e))
    return row


@app.get("/stats/workday")
def workday_stats():
    return _SOURCE.workday_stats()


# ---------------------------------------------------------------------------
# Caseload (case manager's student-first view)
# ---------------------------------------------------------------------------


@app.get("/caseload")
def caseload(
    tenant: Optional[str] = Query(None, description="Tenant code: CFA or WSB"),
    cohort: Optional[str] = None,
    tier: Optional[str] = Query(None, description="A | B | C (by completeness)"),
    min_match_score: Optional[float] = Query(None, ge=0.0, le=1.0),
    q: Optional[str] = None,
    limit: int = Query(200, le=500),
):
    """Dinah's home view: one row per student with their best match,
    match count, application count, days-since-last-touch. Click a row
    in the UI → drill into /students/{id} + /students/{id}/matches."""
    filters = {
        "tenant": tenant,
        "cohort": cohort,
        "tier": tier,
        "min_match_score": min_match_score,
        "q": q,
    }
    rows = _SOURCE.caseload(filters, limit=limit)
    return {"rows": rows, "total": len(rows)}


# ---------------------------------------------------------------------------
# Applications pipeline list
# ---------------------------------------------------------------------------


@app.get("/applications")
def list_applications(
    status: Optional[str] = None,
    student_id: Optional[str] = None,
    job_id: Optional[int] = None,
    owning_recruiter_id: Optional[str] = None,
    tenant: Optional[str] = Query(None, description="Tenant code: CFA or WSB"),
    limit: int = Query(500, le=1000),
):
    """All applications with student + job context. Filterable by status
    (draft/submitted_for_review/approved/packaged/sent/delivered/rejected/
    hired), student, job, or recruiter. Sorted newest-updated first."""
    filters = {
        "status": status,
        "student_id": student_id,
        "job_id": job_id,
        "owning_recruiter_id": owning_recruiter_id,
        "tenant": tenant,
    }
    rows = _SOURCE.list_applications(filters, limit=limit)
    return {"rows": rows, "total": len(rows)}


# ---------------------------------------------------------------------------
# Main entry — python -m agents.job_board.api
# ---------------------------------------------------------------------------


if __name__ == "__main__":  # pragma: no cover
    import uvicorn
    port = int(os.environ.get("RECRUITING_API_PORT", "8012"))
    uvicorn.run(
        "agents.job_board.api:app",
        host="127.0.0.1",
        port=port,
        reload=True,
    )
