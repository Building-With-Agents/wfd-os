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
import sys, os, json
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import psycopg2.extras
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts"))
from pgconfig import PG_CONFIG

from wfdos_common.logging import configure as configure_logging, get_logger

configure_logging(service_name="student-api")
log = get_logger(__name__)

app = FastAPI(title="Waifinder Student Portal API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


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
               created_at
        FROM students WHERE id = %s
    """, (student_id,))

    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

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
    """Top job matches using embedding similarity."""
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
        raise HTTPException(status_code=404, detail="Student not found")

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
        raise HTTPException(status_code=404, detail="Student not found")

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
