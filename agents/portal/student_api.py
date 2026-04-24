"""
Student Portal — FastAPI Backend
Serves student dashboard data from PostgreSQL.

Endpoints:
  GET  /api/student/{id}/profile      - Profile + completeness
  GET  /api/student/{id}/matches      - Top job matches
  GET  /api/student/{id}/gap-analysis - Gap analysis + upskilling
  GET  /api/student/{id}/journey      - Pipeline journey stages
  GET  /api/student/{id}/showcase     - Showcase readiness
  POST /api/student/{id}/chat         - AI chat placeholder

Run: uvicorn student_api:app --reload --port 8001
"""
import json
import os
from datetime import datetime
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
import numpy as np


from wfdos_common.auth import (
    SessionMiddleware,
    build_auth_router,
    Session,
    issue_session,
    resolve_role,
)
from wfdos_common.config import settings
from wfdos_common.errors import NotFoundError, install_error_handlers
from wfdos_common.logging import RequestContextMiddleware, configure as configure_logging, get_logger

configure_logging(service_name="student-api")
log = get_logger(__name__)

app = FastAPI(title="Waifinder Student Portal API", version="0.1.0")

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.auth.secret_key,
    cookie_name=settings.auth.cookie_name,
    max_age_seconds=settings.auth.session_ttl_seconds,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# #29 — structured error envelope on every 4xx/5xx.
install_error_handlers(app)


# -----------------------------------------------------------------------------
# Auth — Gary's Phase 4 magic-link flow + a dev-only instant sign-in shortcut.
# Student Portal API is chosen as the host because (a) it's already running with
# SessionMiddleware mounted and (b) the allowlist-driven role resolution lives
# here naturally. Session cookies issued here work across every service sharing
# settings.auth.secret_key (laborpulse, showcase, consulting_api, cockpit).
# -----------------------------------------------------------------------------

app.include_router(build_auth_router())


@app.get("/auth/dev-login")
def dev_login(email: str, response: Response):
    """DEV ONLY: instant sign-in that skips the magic-link email step.

    Gated by the `DEV_AUTH_BYPASS=1` env var — returns 404 otherwise, so
    this endpoint is inert in any deploy where the flag isn't set. Uses
    Gary's Session + issue_session + allowlist end-to-end; only the
    email dispatch is skipped. The email MUST be on one of the four
    WFDOS_AUTH_*_ALLOWLIST env vars (admin / staff / workforce_development
    / student) — unallowlisted emails still 403 so dev-mode can't
    promote arbitrary users.

    Usage:
        GET /auth/dev-login?email=ritu@computingforall.org
    Returns JSON + Set-Cookie on the response. Hit it from the browser
    once, then every other /api/... call on localhost:3000 carries the
    session cookie automatically.

    Remove or disable (DEV_AUTH_BYPASS != 1) before any prod deploy.
    """
    if os.environ.get("DEV_AUTH_BYPASS") != "1":
        raise HTTPException(status_code=404, detail="Not found")

    email_norm = email.strip().lower()
    role = resolve_role(
        email_norm,
        admin_csv=settings.auth.admin_allowlist,
        staff_csv=settings.auth.staff_allowlist,
        student_csv=settings.auth.student_allowlist,
        workforce_development_csv=settings.auth.workforce_development_allowlist,
    )
    if role is None:
        raise HTTPException(
            status_code=403,
            detail=(
                f"{email_norm} is not on any WFDOS_AUTH_*_ALLOWLIST. "
                "Add it to .env and restart the service."
            ),
        )

    sess = Session(email=email_norm, role=role, tenant_id=None)
    token = issue_session(sess, secret_key=settings.auth.secret_key)
    response.set_cookie(
        key=settings.auth.cookie_name,
        value=token,
        max_age=settings.auth.session_ttl_seconds,
        httponly=True,
        secure=False,  # dev — http://localhost
        samesite="lax",
        path="/",
    )
    log.info("auth.dev_login", email=email_norm, role=role)
    return {"status": "ok", "email": email_norm, "role": role}


# =============================================================================
# Public intake endpoints — used by /careers (the student-facing intake page).
# Unauthenticated on purpose: new students haven't signed in yet, this is the
# first touch. Keep the payload minimal and validate server-side.
# =============================================================================


class QuickAnalysisBody(BaseModel):
    resume_text: str
    job_description: str


class QuickAnalysisResult(BaseModel):
    """What Gemini returns — mirrors the prompt's JSON schema."""
    job_title: str | None = None
    match_score: int
    verdict: str
    matched_skills: list[str] = []
    missing_skills: list[str] = []
    partial_matches: list[str] = []
    narrative: str
    growth_tips: list[str] = []


class IntakeBody(BaseModel):
    name: str
    email: str
    skills: list[str] = []
    target_roles: list[str] = []
    # Optional: attach a prior quick-gap-analysis result so it gets
    # persisted as a gap_analyses row against the new student. Enables
    # the "save this analysis — create profile" flow on /careers.
    quick_analysis: QuickAnalysisResult | None = None


_QUICK_ANALYSIS_PROMPT = """You are a career advisor analyzing a candidate's fit for a specific job.

CANDIDATE RESUME / SKILLS SUMMARY:
{resume_text}

JOB DESCRIPTION:
{job_description}

Return ONLY valid JSON with this exact structure, no markdown fences, no commentary:

{{
  "job_title": "inferred job title from the JD (short form)",
  "match_score": 0,
  "verdict": "Strong fit" or "Match" or "Weak match" or "Not a fit",
  "matched_skills": [],
  "missing_skills": [],
  "partial_matches": [],
  "narrative": "2-3 sentence plain-English explanation of the candidate's fit",
  "growth_tips": []
}}

Rules:
- match_score is an integer 0-100 reflecting genuine overlap (70+ strong, 50-69 decent, 30-49 weak, <30 bad).
- matched_skills: specific skills/technologies the candidate HAS that the job EXPLICITLY wants.
- missing_skills: specific skills/technologies the job WANTS that the resume doesn't show.
- partial_matches: related-but-not-exact (e.g., "React Native" when job wants "React").
- growth_tips: 2-4 specific, actionable things to work on. Plain English. No jargon like "upskill" or "competency".
- Use exact skill / technology names from the candidate and job. Don't invent generic fluff.
- Narrative: speak TO the candidate ("You're well-positioned…"), not ABOUT them.

Return ONLY the JSON."""


@app.post("/api/student/quick-gap-analysis")
def quick_gap_analysis(body: QuickAnalysisBody):
    """Pre-signup value delivery: candidate pastes a job + their resume,
    we return a match score + skill gaps + growth tips. Stateless — the
    analysis isn't persisted here. To persist, the client passes the
    result back as `quick_analysis` on /api/student/intake, which writes
    it as a gap_analyses row against the new student."""

    resume_text = (body.resume_text or "").strip()
    jd_text = (body.job_description or "").strip()
    if len(resume_text) < 50:
        raise HTTPException(status_code=400, detail="Resume text is too short — paste at least a short skills summary.")
    if len(jd_text) < 50:
        raise HTTPException(status_code=400, detail="Job description is too short — paste at least a paragraph.")
    # Hard caps — prevent abuse + keep Gemini cost bounded.
    if len(resume_text) > 10000 or len(jd_text) > 10000:
        raise HTTPException(status_code=400, detail="Input too large — cap each field at 10,000 characters.")

    # Gemini call. NOTE: policy debt — per CLAUDE.md .cursor/rules/llm-provider.mdc
    # we should route through wfdos_common.llm (Azure OpenAI default). This direct
    # google.generativeai call matches the existing pattern in phase_a scripts +
    # verdict_generator; should be swapped together in a focused LLM-adapter pass.
    import os as _os
    import google.generativeai as _genai  # type: ignore

    api_key = _os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=503,
            detail="Gap-analysis service temporarily unavailable (GEMINI_API_KEY not set).",
        )
    _genai.configure(api_key=api_key)
    model_name = _os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")

    prompt = _QUICK_ANALYSIS_PROMPT.format(
        resume_text=resume_text,
        job_description=jd_text,
    )

    try:
        model = _genai.GenerativeModel(model_name)
        resp = model.generate_content(prompt)
        text = (resp.text or "").strip()
        # Strip markdown fences if the model added any.
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        data = json.loads(text)
    except json.JSONDecodeError as je:
        log.error("quick_gap.json_decode_failed", error=str(je))
        raise HTTPException(status_code=502, detail="Couldn't parse the analysis response — please try again.")
    except Exception as e:
        log.error("quick_gap.llm_call_failed", error=str(e), exc_info=True)
        raise HTTPException(status_code=502, detail=f"Analysis failed: {e}")

    # Light validation + normalization so the frontend gets consistent shape.
    out = {
        "job_title": data.get("job_title") or None,
        "match_score": int(data.get("match_score") or 0),
        "verdict": data.get("verdict") or "Match",
        "matched_skills": data.get("matched_skills") or [],
        "missing_skills": data.get("missing_skills") or [],
        "partial_matches": data.get("partial_matches") or [],
        "narrative": data.get("narrative") or "",
        "growth_tips": data.get("growth_tips") or [],
    }
    log.info("quick_gap.ok", match_score=out["match_score"], gaps=len(out["missing_skills"]))
    return out


@app.post("/api/student/intake")
def student_intake(body: IntakeBody):
    """Create a new student row from the /careers intake form, or return
    the existing one if this email is already in the pipeline (idempotent
    so resubmits don't duplicate). Tenant defaults to CFA — WSB intake
    goes through the separate phase_a_parse_cohort1_resumes.py flow.

    Returns the new/existing student_id so the frontend can redirect to
    /student?id=<uuid> and show the user their own portal.
    """
    name = (body.name or "").strip()
    email = (body.email or "").strip().lower()
    if not name or "@" not in email:
        raise HTTPException(status_code=400, detail="name and a valid email are required")

    from psycopg2 import sql as _sql  # noqa: F401 — keeps intent clear

    cfa_tenant_id_row = query_one("SELECT id FROM tenants WHERE code='CFA'")
    if not cfa_tenant_id_row:
        raise HTTPException(status_code=500, detail="CFA tenant not seeded; run migration 014")
    tenant_uuid = str(cfa_tenant_id_row["id"])

    # Idempotent check — duplicates collapse to the existing student.
    existing = query_one(
        "SELECT id, full_name FROM students WHERE LOWER(email) = %s AND tenant_id = %s::uuid",
        (email, tenant_uuid),
    )

    conn = get_conn()
    cur = conn.cursor()
    try:
        if existing:
            student_id = str(existing["id"])
            action = "existing"
        else:
            cur.execute(
                """
                INSERT INTO students (
                    id, tenant_id,
                    full_name, email,
                    pipeline_status, pipeline_stage,
                    source_system,
                    availability_status,
                    resume_parsed, showcase_eligible, showcase_active,
                    legacy_data,
                    created_at, updated_at
                ) VALUES (
                    gen_random_uuid(), %s::uuid,
                    %s, %s,
                    'enrolled', 'intake',
                    'careers-intake',
                    'Available now',
                    FALSE, FALSE, FALSE,
                    %s::jsonb,
                    NOW(), NOW()
                )
                RETURNING id
                """,
                (
                    tenant_uuid,
                    name,
                    email,
                    json.dumps({
                        "intake_source": "/careers",
                        "target_roles": body.target_roles,
                    }),
                ),
            )
            student_id = str(cur.fetchone()[0])
            action = "created"

        # Insert student_skills for any selected skills that match the taxonomy
        # (exact case-insensitive match on skills.skill_name). Unknown skills
        # are silently dropped — the intake form's fixed list should all match.
        matched = 0
        for skill_name in (body.skills or [])[:20]:  # cap for sanity
            clean = skill_name.strip()
            if not clean:
                continue
            cur.execute(
                """
                INSERT INTO student_skills (student_id, skill_id, source)
                SELECT %s, skill_id, 'careers-intake'
                FROM skills
                WHERE LOWER(skill_name) = LOWER(%s)
                ON CONFLICT DO NOTHING
                RETURNING student_id
                """,
                (student_id, clean),
            )
            if cur.fetchone():
                matched += 1

        # Persist the quick-gap-analysis result (if supplied from /careers)
        # as a gap_analyses row, so it shows up on the student's dashboard
        # immediately under "Gap Analysis". We only do this on the CREATED
        # path — re-submitting an intake for an existing student shouldn't
        # overwrite their existing analyses.
        gap_persisted = False
        if body.quick_analysis is not None and action == "created":
            qa = body.quick_analysis
            cur.execute(
                """
                INSERT INTO gap_analyses (
                    id, student_id, tenant_id,
                    target_role, target_job_listing_id,
                    gap_score, missing_skills,
                    recommendations, analyzed_at
                ) VALUES (
                    gen_random_uuid(), %s, %s::uuid,
                    %s, NULL,
                    %s, %s,
                    %s::jsonb, NOW()
                )
                """,
                (
                    student_id,
                    tenant_uuid,
                    qa.job_title or "Pasted job description",
                    float(qa.match_score),
                    qa.missing_skills,
                    json.dumps({
                        "source": "careers-quick-gap",
                        "verdict": qa.verdict,
                        "narrative": qa.narrative,
                        "matched_skills": qa.matched_skills,
                        "partial_matches": qa.partial_matches,
                        "growth_tips": qa.growth_tips,
                    }),
                ),
            )
            gap_persisted = True

        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

    log.info(
        "student.intake",
        action=action,
        email=email,
        student_id=student_id,
        skills_requested=len(body.skills or []),
        skills_matched=matched,
        gap_persisted=gap_persisted,
    )
    return {
        "student_id": student_id,
        "email": email,
        "full_name": name,
        "action": action,  # "created" or "existing"
        "skills_matched": matched,
        "gap_persisted": gap_persisted,
    }


@app.get("/api/student/lookup")
def student_lookup(email: str):
    """Email-based lookup for the 'Already have an account?' flow on
    /careers. Case-insensitive. 404 if not found so the frontend can
    nudge the user to fill out the intake form instead."""
    email_norm = (email or "").strip().lower()
    if not email_norm or "@" not in email_norm:
        raise HTTPException(status_code=400, detail="valid email required")

    row = query_one(
        "SELECT id, full_name FROM students WHERE LOWER(email) = %s LIMIT 1",
        (email_norm,),
    )
    if not row:
        raise NotFoundError("student")

    return {
        "student_id": str(row["id"]),
        "full_name": row["full_name"],
    }


def get_conn():
    """Raw DBAPI connection from the wfdos_common.db engine pool.

    Returns a psycopg2-compatible connection object so existing code
    using `conn.cursor(...)`, `conn.commit()`, `conn.close()` keeps
    working unchanged. Close() returns the connection to the pool
    instead of actually closing it.

    Migrated in #22c; previously `psycopg2.connect(**PG_CONFIG)` —
    direct-connect every call with no pooling.
    """
    from wfdos_common.db import get_engine
    return get_engine().raw_connection()


def query(sql, params=None):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_one(sql, params=None):
    rows = query(sql, params)
    if not rows:
        return None
    return rows[0]


# ============================================================
# GET /api/student/{student_id}/profile
# ============================================================
@app.get("/api/student/{student_id}/profile")
def get_profile(student_id: str):
    student = query_one("""
        SELECT id, full_name, email, phone, city, state, zipcode,
               institution, degree, field_of_study, graduation_year,
               linkedin_url, github_url, portfolio_url,
               profile_completeness_score, required_fields_complete,
               preferred_fields_complete, missing_required, missing_preferred,
               showcase_eligible, showcase_active, showcase_activated_date,
               pipeline_status, pipeline_stage, track, cohort_id,
               resume_parsed, parse_confidence_score,
               availability_status, work_authorization,
               data_quality, engagement_level, last_active_date,
               legacy_data,
               created_at
        FROM students WHERE id = %s
    """, (student_id,))

    if not student:
        raise NotFoundError("student")

    # Get skill count — shared query lives in wfdos_common.db.queries (#22c)
    # so the identical lookup in showcase_api.py:322 can use the same impl.
    from wfdos_common.db import get_student_skills
    conn = get_conn()
    try:
        skill_names = get_student_skills(conn, student_id)
    finally:
        conn.close()
    skills = [{"skill_name": name} for name in skill_names]

    # Convert missing arrays to lists
    for key in ['missing_required', 'missing_preferred']:
        if student.get(key) and isinstance(student[key], list):
            pass  # already a list
        elif student.get(key):
            student[key] = list(student[key])

    student['skills'] = [s['skill_name'] for s in skills]
    student['skill_count'] = len(skills)

    # --- Resume summary additions (for the Student Portal summary card) ---
    # Pull career_objective and certifications out of legacy_data (the
    # resume parser stores them there for cohort-1 WSB students).
    legacy = student.get('legacy_data') or {}
    if not isinstance(legacy, dict):
        legacy = {}
    student['career_objective'] = legacy.get('career_objective')
    student['certifications'] = legacy.get('certifications') or []

    # Work experience from student_work_experience (denormalized, sorted
    # by start_date DESC — most recent first).
    work_experience = query("""
        SELECT company, title, start_date, end_date, is_current,
               description
        FROM student_work_experience
        WHERE student_id = %s
        ORDER BY COALESCE(start_date, '1900-01-01') DESC
    """, (student_id,))
    # Serialize dates.
    for row in work_experience:
        for k in ("start_date", "end_date"):
            if row.get(k) is not None:
                row[k] = row[k].isoformat()
    student['work_experience'] = work_experience

    # legacy_data is large + noisy; strip before return.
    student.pop('legacy_data', None)

    # Serialize datetimes
    for k, v in student.items():
        if isinstance(v, datetime):
            student[k] = v.isoformat()

    return student


# ============================================================
# GET /api/student/{student_id}/matches
# ============================================================
@app.get("/api/student/{student_id}/matches")
def get_matches(student_id: str):
    """Top job matches. Prefers pre-computed cohort_matches rows (produced
    by the Phase B pipeline for tenant-scoped cohorts) when any exist for
    this student; otherwise falls back to on-the-fly embedding similarity
    against job_listings (legacy Lightcast pool)."""

    # Fast path: did Phase B already compute matches for this student?
    # If yes, return them — same shape the frontend expects.
    cohort = query("""
        SELECT cm.job_id,
               cm.cosine_similarity,
               cm.match_rank,
               je.title,
               je.company,
               je.city,
               je.state,
               je.is_remote,
               je.skills_required
        FROM cohort_matches cm
        JOIN jobs_enriched je ON je.id = cm.job_id
        WHERE cm.student_id = %s
        ORDER BY cm.cosine_similarity DESC
        LIMIT 3
    """, (student_id,))

    if cohort:
        # Get the student's skills to compute matched / missing per-row.
        student_skill_rows = query(
            "SELECT LOWER(sk.skill_name) AS s FROM student_skills ss "
            "JOIN skills sk ON sk.skill_id = ss.skill_id WHERE ss.student_id = %s",
            (student_id,),
        )
        student_skill_set = {r['s'] for r in student_skill_rows}

        matches = []
        for r in cohort:
            job_skills = [s.strip() for s in (r.get('skills_required') or []) if s]
            job_skill_lc = {s.lower() for s in job_skills}
            matched = sorted(student_skill_set & job_skill_lc)[:10]
            missing = sorted(job_skill_lc - student_skill_set)[:5]
            matches.append({
                "job_id": str(r['job_id']),
                "title": r['title'],
                "company": r['company'],
                "city": r['city'],
                "state": r['state'],
                "salary_min": None,
                "salary_max": None,
                "match_score": round(float(r['cosine_similarity']) * 100, 1),
                "matched_skills": matched,
                "missing_skills": missing,
                "total_job_skills": len(job_skills),
                "match_source": "cohort_matches",
            })
        return {"matches": matches}

    # Fallback: on-the-fly embedding match against legacy job_listings.
    # Get student skills + embeddings
    student_skills = query("""
        SELECT DISTINCT sk.skill_name, sk.embedding_vector::text as vec
        FROM student_skills ss
        JOIN skills sk ON sk.skill_id = ss.skill_id
        WHERE ss.student_id = %s AND sk.embedding_vector IS NOT NULL
    """, (student_id,))

    if not student_skills:
        return {"matches": [], "message": "No skills found for matching"}

    # Compute student embedding (average of skill vectors)
    vectors = []
    student_skill_names = set()
    for s in student_skills:
        student_skill_names.add(s['skill_name'].lower())
        vals = [float(x) for x in s['vec'].strip("[]").split(",")]
        vectors.append(np.array(vals))

    student_emb = np.mean(vectors, axis=0)
    student_emb = student_emb / np.linalg.norm(student_emb)

    # Get top digital jobs with skills
    jobs = query("""
        SELECT id, title, company_name, city, state,
               salary_min, salary_max, salary_period,
               legacy_data->>'cfa_skills' as skills_text
        FROM job_listings
        WHERE is_digital = TRUE
        AND legacy_data->>'cfa_skills' IS NOT NULL
        AND title NOT ILIKE 'unclassified'
        LIMIT 500
    """)

    # Load skill embeddings for job matching
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT skill_name, embedding_vector::text FROM skills WHERE embedding_vector IS NOT NULL")
    skill_map = {}
    for name, vec_str in cur.fetchall():
        vals = [float(x) for x in vec_str.strip("[]").split(",")]
        skill_map[name.lower()] = np.array(vals)
    conn.close()

    # Score each job
    scored = []
    for job in jobs:
        if not job['skills_text']:
            continue
        job_skills = [s.strip() for s in job['skills_text'].split(",")][:15]
        job_vectors = [skill_map[s.lower()] for s in job_skills if s.lower() in skill_map]
        if not job_vectors:
            continue
        job_emb = np.mean(job_vectors, axis=0)
        job_emb = job_emb / np.linalg.norm(job_emb)
        sim = float(np.dot(student_emb, job_emb))

        # Find overlapping and missing skills
        job_skill_set = set(s.lower() for s in job_skills)
        matched = student_skill_names & job_skill_set
        missing = job_skill_set - student_skill_names

        scored.append({
            "job_id": str(job['id']),
            "title": job['title'],
            "company": job['company_name'],
            "city": job['city'],
            "state": job['state'],
            "salary_min": float(job['salary_min']) if job['salary_min'] else None,
            "salary_max": float(job['salary_max']) if job['salary_max'] else None,
            "match_score": round(sim * 100, 1),
            "matched_skills": sorted(matched)[:10],
            "missing_skills": sorted(missing)[:5],
            "total_job_skills": len(job_skills),
        })

    scored.sort(key=lambda x: -x['match_score'])
    return {"matches": scored[:3]}


# ============================================================
# GET /api/student/{student_id}/gap-detail/{job_id}
# ============================================================
@app.get("/api/student/{student_id}/gap-detail/{job_id}")
def get_gap_detail(student_id: str, job_id: int):
    """Detailed per-(student, job) gap view for the Student Portal drill:
    LLM narrative + structured strengths/gaps/verdict + career pathway
    (the student's other top matches as context for progression).

    Reads from match_narratives + gap_analyses + jobs_enriched + cohort_matches
    — all populated by the Phase B pipeline. Assumes the (student, job) pair
    exists in cohort_matches; returns 404 otherwise."""

    # The job + match core
    core = query_one("""
        SELECT je.id AS job_id, je.title, je.company, je.city, je.state,
               je.is_remote, je.skills_required, je.job_description,
               cm.cosine_similarity, cm.match_rank
        FROM jobs_enriched je
        JOIN cohort_matches cm ON cm.job_id = je.id AND cm.student_id = %s
        WHERE je.id = %s
    """, (student_id, job_id))

    if not core:
        raise NotFoundError("cohort_match")

    # The LLM narrative (Priority 1 per spec)
    narrative = query_one("""
        SELECT verdict_line, narrative_text,
               match_strengths, match_gaps, match_partial,
               calibration_label, cosine_similarity, generated_at
        FROM match_narratives
        WHERE student_id = %s AND job_id = %s
    """, (student_id, job_id))

    # Gap analysis for this specific (student, job) pair. The
    # gap_analyses table stores target_role as a string rather than an
    # FK id (target_job_listing_id is nullable and not populated by
    # Phase B4), so match by title-equality via jobs_enriched.
    gap = query_one("""
        SELECT ga.id, ga.target_role, ga.gap_score, ga.missing_skills,
               ga.recommendations, ga.analyzed_at
        FROM gap_analyses ga
        WHERE ga.student_id = %s
          AND ga.target_role = (SELECT title FROM jobs_enriched WHERE id = %s)
        ORDER BY ga.analyzed_at DESC
        LIMIT 1
    """, (student_id, job_id))

    # Career pathway — the student's other matches, for progression context
    pathway = query("""
        SELECT cm.job_id, cm.cosine_similarity, cm.match_rank,
               je.title, je.company, je.city, je.state,
               mn.verdict_line, mn.calibration_label,
               ga.gap_score,
               ga.missing_skills
        FROM cohort_matches cm
        JOIN jobs_enriched je ON je.id = cm.job_id
        LEFT JOIN match_narratives mn
               ON mn.student_id = cm.student_id AND mn.job_id = cm.job_id
        LEFT JOIN gap_analyses ga
               ON ga.student_id = cm.student_id AND ga.target_role = je.title
        WHERE cm.student_id = %s AND cm.job_id <> %s
        ORDER BY cm.cosine_similarity DESC
        LIMIT 5
    """, (student_id, job_id))

    # Serialize datetimes + floats
    def ser(row):
        if not row:
            return row
        for k, v in row.items():
            if isinstance(v, datetime):
                row[k] = v.isoformat()
            elif hasattr(v, "quantize"):  # Decimal
                row[k] = float(v)
        return row

    ser(core)
    if core:
        # cosine_similarity Decimal → float
        if core.get('cosine_similarity') is not None:
            core['cosine_similarity'] = float(core['cosine_similarity'])
    ser(narrative) if narrative else None
    if narrative and narrative.get('cosine_similarity') is not None:
        narrative['cosine_similarity'] = float(narrative['cosine_similarity'])
    ser(gap) if gap else None
    if gap and gap.get('gap_score') is not None:
        gap['gap_score'] = float(gap['gap_score'])

    pathway_out = []
    for p in pathway:
        ser(p)
        if p.get('cosine_similarity') is not None:
            p['cosine_similarity'] = float(p['cosine_similarity'])
        if p.get('gap_score') is not None:
            p['gap_score'] = float(p['gap_score'])
        pathway_out.append(p)

    return {
        "core": core,
        "narrative": narrative,
        "gap_analysis": gap,
        "career_pathway": pathway_out,
    }


# ============================================================
# GET /api/student/{student_id}/gap-analysis
# ============================================================
@app.get("/api/student/{student_id}/gap-analysis")
def get_gap_analysis(student_id: str):
    # Get latest gap analysis
    gap = query_one("""
        SELECT ga.id, ga.target_role, ga.gap_score,
               ga.missing_skills, ga.recommendations,
               ga.analyzed_at,
               jl.title as job_title, jl.company_name
        FROM gap_analyses ga
        LEFT JOIN job_listings jl ON jl.id = ga.target_job_listing_id
        WHERE ga.student_id = %s
        ORDER BY ga.analyzed_at DESC
        LIMIT 1
    """, (student_id,))

    if not gap:
        return {
            "has_analysis": False,
            "message": "No gap analysis available. Complete your profile to generate one."
        }

    # Parse recommendations
    recs = gap.get('recommendations')
    if isinstance(recs, str):
        recs = json.loads(recs)

    upskilling = recs.get('upskilling', []) if recs else []

    # Build skill gap items with learning resources
    skill_gaps = []
    for skill in (gap.get('missing_skills') or [])[:5]:
        # Find matching upskilling recommendation
        rec = next((u for u in upskilling if u.get('skill', '').lower() == skill.lower()), None)

        skill_gaps.append({
            "skill": skill,
            "recommendation": rec.get('recommendation', 'New skill area') if rec else 'Consider a structured course',
            "transferable_from": rec.get('transferable_from') if rec else None,
            "priority_score": rec.get('priority_score', 0) if rec else 0,
            # Placeholder resources until we build a resources table
            "resource": {
                "title": f"Learn {skill}",
                "provider": "LinkedIn Learning",
                "duration_hours": 4,
                "is_free": False,
                "url": "#",
            }
        })

    total_hours = sum(sg['resource']['duration_hours'] for sg in skill_gaps)

    return {
        "has_analysis": True,
        "gap_score": float(gap['gap_score']) if gap['gap_score'] else 0,
        "target_role": gap.get('target_role') or gap.get('job_title'),
        "company": gap.get('company_name'),
        "missing_skills_count": len(gap.get('missing_skills') or []),
        "skill_gaps": skill_gaps,
        "hours_to_close": total_hours,
        "matched_count": recs.get('matched_count', 0) if recs else 0,
        "total_job_skills": recs.get('total_job_skills', 0) if recs else 0,
        "analyzed_at": gap['analyzed_at'].isoformat() if gap.get('analyzed_at') else None,
    }


# ============================================================
# GET /api/student/{student_id}/journey
# ============================================================
@app.get("/api/student/{student_id}/journey")
def get_journey(student_id: str):
    student = query_one("""
        SELECT pipeline_status, pipeline_stage, track, cohort_id,
               showcase_eligible, showcase_active,
               profile_completeness_score, resume_parsed
        FROM students WHERE id = %s
    """, (student_id,))

    if not student:
        raise NotFoundError("student")

    # Get journey records
    journeys = query("""
        SELECT stage, entered_at, exited_at, notes
        FROM student_journeys
        WHERE student_id = %s
        ORDER BY entered_at
    """, (student_id,))

    # Define the 7 stages
    all_stages = [
        {"id": 1, "name": "Intake", "key": "intake"},
        {"id": 2, "name": "Assessment", "key": "assessment"},
        {"id": 3, "name": "Training", "key": "training"},
        {"id": 4, "name": "OJT", "key": "ojt"},
        {"id": 5, "name": "Job Ready", "key": "job_ready"},
        {"id": 6, "name": "Showcased", "key": "showcased"},
        {"id": 7, "name": "Placed", "key": "placed"},
    ]

    # Determine current stage from profile data
    completed_stages = set()
    current_stage = 1  # default to intake

    if student.get('resume_parsed'):
        completed_stages.add(1)  # intake done
        current_stage = 2
    if student.get('profile_completeness_score') and float(student['profile_completeness_score']) > 0.4:
        completed_stages.add(2)  # assessment done
        current_stage = 3
    if student.get('pipeline_status') in ('enrolled', 'completed'):
        completed_stages.add(3)
        current_stage = 4
    if student.get('showcase_eligible'):
        completed_stages.update({3, 4, 5})
        current_stage = 5
    if student.get('showcase_active'):
        completed_stages.update({3, 4, 5, 6})
        current_stage = 6

    # Build stage list with status
    stages = []
    for stage in all_stages:
        stages.append({
            "id": stage['id'],
            "name": stage['name'],
            "completed": stage['id'] in completed_stages,
            "current": stage['id'] == current_stage,
        })

    # Next step based on current stage
    next_steps = {
        1: "Upload your resume to complete intake",
        2: "Complete your profile to unlock assessment",
        3: "Continue training milestones",
        4: "Complete OJT assignment",
        5: "Finalize profile for Talent Showcase",
        6: "Respond to employer interest",
        7: "Congratulations - you're placed!",
    }

    weeks_estimate = {1: 1, 2: 2, 3: 8, 4: 4, 5: 2, 6: 4, 7: 0}

    return {
        "stages": stages,
        "current_stage": current_stage,
        "track": student.get('track') or "direct_placement",
        "cohort": student.get('cohort_id'),
        "next_step": next_steps.get(current_stage, "Continue your journey"),
        "estimated_weeks_to_next": weeks_estimate.get(current_stage, 2),
        "journey_records": [{
            "stage": j['stage'],
            "entered_at": j['entered_at'].isoformat() if j.get('entered_at') else None,
        } for j in journeys],
    }


# ============================================================
# GET /api/student/{student_id}/showcase
# ============================================================
@app.get("/api/student/{student_id}/showcase")
def get_showcase(student_id: str):
    student = query_one("""
        SELECT showcase_eligible, showcase_active, showcase_activated_date,
               profile_completeness_score, missing_required, resume_parsed
        FROM students WHERE id = %s
    """, (student_id,))

    if not student:
        raise NotFoundError("student")

    # Get skill count
    skill_count = query_one(
        "SELECT count(DISTINCT skill_id) as n FROM student_skills WHERE student_id = %s",
        (student_id,)
    )

    # Build checklist
    missing = student.get('missing_required') or []
    if isinstance(missing, str):
        missing = json.loads(missing)

    checklist = [
        {
            "id": "resume",
            "label": "Resume uploaded",
            "completed": bool(student.get('resume_parsed')),
        },
        {
            "id": "skills",
            "label": "3+ skills verified",
            "completed": (skill_count.get('n', 0) or 0) >= 3,
        },
        {
            "id": "education",
            "label": "Education confirmed",
            "completed": "education" not in missing,
        },
        {
            "id": "location",
            "label": "Location confirmed",
            "completed": "location" not in missing,
        },
        {
            "id": "availability",
            "label": "Availability status set",
            "completed": "availability_status" not in missing,
            "action_label": "Set now" if "availability_status" in missing else None,
            "action_link": "#availability" if "availability_status" in missing else None,
        },
    ]

    completed_count = sum(1 for c in checklist if c['completed'])

    return {
        "showcase_active": bool(student.get('showcase_active')),
        "showcase_eligible": bool(student.get('showcase_eligible')),
        "profile_completeness": float(student['profile_completeness_score']) if student.get('profile_completeness_score') else 0,
        "checklist": checklist,
        "completed_items": completed_count,
        "total_items": len(checklist),
        "employer_views": 0,  # Placeholder until tracking is built
        "employer_shortlists": 0,
    }


# ============================================================
# POST /api/student/{student_id}/chat
# ============================================================
class ChatMessage(BaseModel):
    message: str

@app.post("/api/student/{student_id}/chat")
def chat(student_id: str, msg: ChatMessage):
    """Route to the Student Agent (Gemini Flash) on port 8009."""
    import httpx
    try:
        r = httpx.post(
            "http://localhost:8009/api/assistant/chat",
            json={
                "session_id": f"student-{student_id}",
                "agent_type": "student",
                "user_role": "student",
                "user_id": student_id,
                "message": msg.message,
            },
            timeout=30.0,
        )
        if r.status_code == 200:
            data = r.json()
            return {
                "response": data.get("response", ""),
                "suggestions": data.get("suggestions"),
                "status": "ok",
            }
    except Exception as e:
        log.error("chat.student_agent.failed", error_type=type(e).__name__, error=str(e), exc_info=True)

    return {
        "response": "I'm having trouble connecting right now. Try again in a moment, or explore your dashboard for insights.",
        "status": "error",
    }


# ============================================================
# Health check
# ============================================================
@app.get("/api/stats")
def get_stats():
    """Platform-wide stats for the CFA homepage."""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT
            (SELECT count(*) FROM students) as total_students,
            (SELECT count(*) FROM students WHERE resume_parsed = TRUE) as parsed_students,
            (SELECT count(*) FROM job_listings WHERE is_digital = TRUE OR is_digital IS NULL) as job_listings,
            (SELECT count(*) FROM employers) as total_employers,
            (SELECT count(DISTINCT sk.skill_id) FROM student_skills sk) as skills_tracked
    """)
    row = dict(cur.fetchone())
    conn.close()
    row["regions_count"] = 3  # WA, TX (Borderplex), Remote
    return row


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "student-portal-api", "port": 8001}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
