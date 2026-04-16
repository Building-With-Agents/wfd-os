"""
Talent Showcase — FastAPI Backend
Serves showcase candidate data for employer-facing talent browse.

Endpoints:
  GET /api/showcase/candidates  — All showcase-ready students
  GET /api/showcase/filters     — Available filter options

Privacy: Last name initial only. No email/phone exposed.

Run: uvicorn showcase_api:app --reload --port 8002
"""
import sys, os, json
from datetime import datetime, timezone
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts"))
from pgconfig import PG_CONFIG

app = FastAPI(title="Waifinder Talent Showcase API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3003", "http://localhost:3000", "http://127.0.0.1:3003"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn():
    """Raw DBAPI connection from the wfdos_common.db engine pool (#22c)."""
    from wfdos_common.db import get_engine
    return get_engine().raw_connection()


def query(sql, params=None):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


@app.get("/api/showcase/candidates")
def get_candidates(
    skill: str = Query(None, description="Filter by skill name (partial match)"),
    location: str = Query(None, description="Filter by city or state"),
    min_completeness: float = Query(0.0, description="Minimum profile completeness (0-1)"),
    limit: int = Query(50, description="Max candidates to return"),
    offset: int = Query(0, description="Pagination offset"),
):
    """
    Returns showcase-ready candidates with privacy-safe names.
    Uses resume_parsed = true as the current eligibility proxy
    (full showcase_active logic comes later).
    """
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get parsed students with basic profile data
    cur.execute("""
        SELECT
            s.id,
            s.full_name,
            s.city,
            s.state,
            s.institution,
            s.degree,
            s.field_of_study,
            s.graduation_year,
            s.profile_completeness_score,
            s.parse_confidence_score,
            s.pipeline_status,
            s.track,
            s.availability_status,
            s.showcase_eligible,
            s.showcase_active
        FROM students s
        WHERE s.resume_parsed = TRUE
          AND s.profile_completeness_score >= %s
        ORDER BY s.profile_completeness_score DESC, s.full_name
        LIMIT %s OFFSET %s
    """, (min_completeness, limit, offset))

    students = [dict(r) for r in cur.fetchall()]

    if not students:
        conn.close()
        return {"candidates": [], "total": 0, "filters_applied": {}}

    student_ids = [s['id'] for s in students]

    # Batch fetch top 5 skills per student
    placeholders = ",".join(["%s"] * len(student_ids))
    cur.execute(f"""
        WITH deduped AS (
            SELECT DISTINCT ss.student_id, sk.skill_name
            FROM student_skills ss
            JOIN skills sk ON sk.skill_id = ss.skill_id
            WHERE ss.student_id IN ({placeholders})
        ),
        ranked_skills AS (
            SELECT student_id, skill_name,
                   ROW_NUMBER() OVER (PARTITION BY student_id ORDER BY skill_name) as rn
            FROM deduped
        )
        SELECT student_id, skill_name
        FROM ranked_skills
        WHERE rn <= 5
    """, student_ids)

    skills_map = {}
    for row in cur.fetchall():
        sid = row['student_id']
        if sid not in skills_map:
            skills_map[sid] = []
        skills_map[sid].append(row['skill_name'])

    # Batch fetch skill counts per student
    cur.execute(f"""
        SELECT student_id, count(DISTINCT skill_id) as total_skills
        FROM student_skills
        WHERE student_id IN ({placeholders})
        GROUP BY student_id
    """, student_ids)
    skill_counts = {row['student_id']: row['total_skills'] for row in cur.fetchall()}

    # Batch fetch latest gap analysis (top match) per student
    cur.execute(f"""
        SELECT DISTINCT ON (ga.student_id)
            ga.student_id,
            ga.target_role,
            ga.gap_score
        FROM gap_analyses ga
        WHERE ga.student_id IN ({placeholders})
        ORDER BY ga.student_id, ga.analyzed_at DESC
    """, student_ids)
    gap_map = {row['student_id']: row for row in cur.fetchall()}

    # Batch fetch education from student_education table
    cur.execute(f"""
        SELECT DISTINCT ON (se.student_id)
            se.student_id,
            se.institution,
            se.degree,
            se.field_of_study
        FROM student_education se
        WHERE se.student_id IN ({placeholders})
        ORDER BY se.student_id, se.end_date DESC NULLS LAST
    """, student_ids)
    edu_map = {row['student_id']: row for row in cur.fetchall()}

    conn.close()

    # Get total count for pagination
    total_count = len(query(
        "SELECT count(*) as n FROM students WHERE resume_parsed = TRUE AND profile_completeness_score >= %s",
        (min_completeness,)
    ))
    total = query(
        "SELECT count(*) as n FROM students WHERE resume_parsed = TRUE AND profile_completeness_score >= %s",
        (min_completeness,)
    )[0]['n']

    # Build response
    candidates = []
    for s in students:
        sid = s['id']
        name_parts = (s['full_name'] or '').strip().split()
        first_name = name_parts[0] if name_parts else 'Unknown'
        last_initial = name_parts[-1][0].upper() + '.' if len(name_parts) > 1 else ''

        # Skills
        top_skills = skills_map.get(sid, [])
        total_skill_count = skill_counts.get(sid, 0)

        # Filter by skill if requested
        if skill:
            skill_lower = skill.lower()
            has_skill = any(skill_lower in sk.lower() for sk in top_skills)
            if not has_skill:
                # Check full skill list
                all_student_skills = query("""
                    SELECT sk.skill_name FROM student_skills ss
                    JOIN skills sk ON sk.skill_id = ss.skill_id
                    WHERE ss.student_id = %s AND LOWER(sk.skill_name) LIKE %s
                """, (sid, f"%{skill_lower}%"))
                if not all_student_skills:
                    continue

        # Filter by location if requested
        if location:
            loc_lower = location.lower()
            student_loc = f"{s.get('city', '')} {s.get('state', '')}".lower()
            if loc_lower not in student_loc:
                continue

        # Education: prefer student_education table, fall back to main record
        edu = edu_map.get(sid, {})
        education = {
            "institution": edu.get('institution') or s.get('institution'),
            "degree": edu.get('degree') or s.get('degree'),
            "field_of_study": edu.get('field_of_study') or s.get('field_of_study'),
            "graduation_year": s.get('graduation_year'),
        }

        # Top match from gap analysis
        gap = gap_map.get(sid)
        top_match = None
        if gap:
            top_match = {
                "role": gap['target_role'],
                "gap_score": float(gap['gap_score']) if gap['gap_score'] else None,
            }

        # Location
        location_str = ", ".join(filter(None, [s.get('city'), s.get('state')]))

        # Track
        track = s.get('track') or 'direct_placement'

        candidate = {
            "id": str(sid),
            "first_name": first_name,
            "last_initial": last_initial,
            "display_name": f"{first_name} {last_initial}",
            "location": location_str or "Location not set",
            "availability": s.get('availability_status') or "Available now",
            "track": track,
            "profile_completeness": float(s['profile_completeness_score']) if s.get('profile_completeness_score') else 0,
            "parse_confidence": float(s['parse_confidence_score']) if s.get('parse_confidence_score') else 0,
            "top_skills": top_skills,
            "total_skills": total_skill_count,
            "education": education,
            "top_match": top_match,
        }
        candidates.append(candidate)

    return {
        "candidates": candidates,
        "total": total,
        "returned": len(candidates),
        "filters_applied": {
            "skill": skill,
            "location": location,
            "min_completeness": min_completeness,
        },
    }


@app.get("/api/showcase/filters")
def get_filters():
    """Available filter options for the showcase."""
    skills = query("""
        SELECT sk.skill_name, count(DISTINCT ss.student_id) as student_count
        FROM student_skills ss
        JOIN skills sk ON sk.skill_id = ss.skill_id
        JOIN students s ON s.id = ss.student_id
        WHERE s.resume_parsed = TRUE
        GROUP BY sk.skill_name
        HAVING count(DISTINCT ss.student_id) >= 2
        ORDER BY count(DISTINCT ss.student_id) DESC
        LIMIT 30
    """)

    locations = query("""
        SELECT city, state, count(*) as n
        FROM students
        WHERE resume_parsed = TRUE AND city IS NOT NULL
        GROUP BY city, state
        ORDER BY count(*) DESC
        LIMIT 20
    """)

    return {
        "skills": [{"name": s['skill_name'], "count": s['student_count']} for s in skills],
        "locations": [
            {"label": f"{l['city']}, {l['state']}" if l['state'] else l['city'], "count": l['n']}
            for l in locations
        ],
    }


@app.get("/api/showcase/candidates/{student_id}")
def get_candidate_detail(student_id: str):
    """
    Full employer-facing profile for a single candidate.
    Privacy: No email, phone, or personal contact info.
    All contact goes through CFA.
    """
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Core student data (privacy-filtered)
    cur.execute("""
        SELECT id, full_name, city, state, zipcode,
               institution, degree, field_of_study, graduation_year,
               linkedin_url, github_url, portfolio_url,
               profile_completeness_score, parse_confidence_score,
               pipeline_status, track, availability_status,
               showcase_eligible, showcase_active, resume_parsed,
               legacy_data, created_at, updated_at
        FROM students WHERE id = %s
    """, (student_id,))
    student = cur.fetchone()

    if not student:
        conn.close()
        raise HTTPException(status_code=404, detail="Candidate not found")

    student = dict(student)

    # Privacy: first name + last initial only
    name_parts = (student['full_name'] or '').strip().split()
    first_name = name_parts[0] if name_parts else 'Unknown'
    last_initial = name_parts[-1][0].upper() + '.' if len(name_parts) > 1 else ''

    # All skills
    cur.execute("""
        SELECT DISTINCT sk.skill_name, sk.skill_type
        FROM student_skills ss
        JOIN skills sk ON sk.skill_id = ss.skill_id
        WHERE ss.student_id = %s
        ORDER BY sk.skill_name
    """, (student_id,))
    all_skills = [dict(r) for r in cur.fetchall()]

    # Group skills by heuristic categories
    skill_groups = {}
    if all_skills:
        programming = []
        cloud = []
        data = []
        tools = []
        other = []
        prog_kw = {'python', 'java', 'javascript', 'c++', 'c#', 'typescript', 'go',
                    'ruby', 'php', 'swift', 'kotlin', 'rust', 'r', 'sql', 'html', 'css',
                    'bash', 'perl', 'erlang', 'scala'}
        cloud_kw = {'aws', 'azure', 'gcp', 'docker', 'kubernetes', 'terraform',
                    'jenkins', 'ci/cd', 'linux', 'devops', 'cloud'}
        data_kw = {'data', 'machine learning', 'analytics', 'tableau', 'power bi',
                   'pandas', 'numpy', 'matplotlib', 'hadoop', 'spark', 'sql',
                   'database', 'mongodb', 'mysql', 'postgresql', 'elasticsearch'}
        tool_kw = {'git', 'github', 'jira', 'agile', 'scrum', 'confluence',
                   'vscode', 'eclipse', 'android studio', 'figma', 'postman'}

        for sk in all_skills:
            name_lower = sk['skill_name'].lower()
            if any(kw in name_lower for kw in prog_kw):
                programming.append(sk['skill_name'])
            elif any(kw in name_lower for kw in cloud_kw):
                cloud.append(sk['skill_name'])
            elif any(kw in name_lower for kw in data_kw):
                data.append(sk['skill_name'])
            elif any(kw in name_lower for kw in tool_kw):
                tools.append(sk['skill_name'])
            else:
                other.append(sk['skill_name'])

        skill_groups = {}
        if programming:
            skill_groups['Programming Languages'] = programming
        if cloud:
            skill_groups['Cloud & Infrastructure'] = cloud
        if data:
            skill_groups['Data & Analytics'] = data
        if tools:
            skill_groups['Tools & Frameworks'] = tools
        if other:
            skill_groups['Other Skills'] = other

    # Education records
    cur.execute("""
        SELECT institution, degree, field_of_study, start_date, end_date, gpa
        FROM student_education
        WHERE student_id = %s
        ORDER BY end_date DESC NULLS LAST
    """, (student_id,))
    education_records = []
    for row in cur.fetchall():
        r = dict(row)
        for k in ('start_date', 'end_date'):
            if r.get(k):
                r[k] = r[k].isoformat()
        education_records.append(r)

    # Primary education (from main student record if no education records)
    primary_education = {
        "institution": student.get('institution'),
        "degree": student.get('degree'),
        "field_of_study": student.get('field_of_study'),
        "graduation_year": student.get('graduation_year'),
    }

    # Work experience
    cur.execute("""
        SELECT company, title, description, start_date, end_date, is_current
        FROM student_work_experience
        WHERE student_id = %s
        ORDER BY CASE WHEN is_current THEN 0 ELSE 1 END, end_date DESC NULLS FIRST
    """, (student_id,))
    work_experience = []
    for row in cur.fetchall():
        r = dict(row)
        for k in ('start_date', 'end_date'):
            if r.get(k):
                r[k] = r[k].isoformat()
        work_experience.append(r)

    # Gap analysis (best match)
    cur.execute("""
        SELECT target_role, gap_score, recommendations
        FROM gap_analyses
        WHERE student_id = %s
        ORDER BY gap_score DESC
        LIMIT 1
    """, (student_id,))
    best_match = cur.fetchone()

    # Extract career objective and certifications from legacy_data
    legacy = student.get('legacy_data') or {}
    if isinstance(legacy, str):
        try:
            legacy = json.loads(legacy)
        except Exception:
            legacy = {}

    career_objective = legacy.get('career_objective')
    certifications = legacy.get('certifications', [])
    if isinstance(certifications, str):
        try:
            certifications = json.loads(certifications)
        except Exception:
            certifications = []

    conn.close()

    location_str = ", ".join(filter(None, [student.get('city'), student.get('state')]))

    return {
        "id": str(student['id']),
        "first_name": first_name,
        "last_initial": last_initial,
        "display_name": f"{first_name} {last_initial}",
        "location": location_str or "Location not set",
        "availability": student.get('availability_status') or "Available now",
        "track": student.get('track') or "direct_placement",
        "profile_completeness": float(student['profile_completeness_score']) if student.get('profile_completeness_score') else 0,
        "parse_confidence": float(student['parse_confidence_score']) if student.get('parse_confidence_score') else 0,

        "skills_grouped": skill_groups,
        "total_skills": len(all_skills),

        "education": {
            "primary": primary_education,
            "records": education_records,
        },

        "work_experience": [{
            "title": w.get('title'),
            "company_type": _infer_company_type(w.get('company', '')),
            "duration": _compute_duration(w.get('start_date'), w.get('end_date'), w.get('is_current')),
            "is_current": w.get('is_current', False),
            "start_date": w.get('start_date'),
            "end_date": w.get('end_date'),
        } for w in work_experience],

        "certifications": certifications,
        "career_objective": career_objective,

        "best_match": {
            "role": best_match['target_role'],
            "gap_score": float(best_match['gap_score']) if best_match and best_match.get('gap_score') else None,
        } if best_match else None,

        "linkedin_url": student.get('linkedin_url'),
        "github_url": student.get('github_url'),
        "portfolio_url": student.get('portfolio_url'),

        "last_updated": student['updated_at'].isoformat() if student.get('updated_at') else None,
        "resume_verified": bool(student.get('resume_parsed')),

        "contact": {
            "method": "Through Computing for All",
            "email": "info@computingforall.org",
            "subject": f"Hiring inquiry: {first_name} {last_initial}",
            "body": f"I am interested in hiring {first_name} from the CFA Talent Showcase. Please connect us.",
        },
    }


def _infer_company_type(company_name: str) -> str:
    """Infer company type from name for privacy (don't expose actual company)."""
    name = company_name.lower()
    if any(kw in name for kw in ['university', 'college', 'school', 'institute', 'academy']):
        return "Educational Institution"
    if any(kw in name for kw in ['hospital', 'clinic', 'health', 'medical']):
        return "Healthcare Organization"
    if any(kw in name for kw in ['government', 'federal', 'state', 'city', 'county']):
        return "Government Agency"
    if any(kw in name for kw in ['startup', 'inc', 'corp', 'llc', 'ltd']):
        return "Technology Company"
    if any(kw in name for kw in ['bank', 'financial', 'insurance', 'capital']):
        return "Financial Services"
    if any(kw in name for kw in ['consulting', 'solutions', 'services', 'advisory']):
        return "Consulting Firm"
    if any(kw in name for kw in ['restaurant', 'cafe', 'food', 'bar']):
        return "Food & Hospitality"
    if any(kw in name for kw in ['retail', 'store', 'shop']):
        return "Retail"
    return "Private Company"


def _compute_duration(start: str, end: str, is_current: bool) -> str:
    """Compute human-readable duration from date strings."""
    if not start:
        return "Duration unknown"
    try:
        from dateutil.relativedelta import relativedelta
        from datetime import date
        s = date.fromisoformat(start[:10])
        if is_current:
            e = date.today()
        elif end:
            e = date.fromisoformat(end[:10])
        else:
            return "Duration unknown"
        diff = relativedelta(e, s)
        parts = []
        if diff.years:
            parts.append(f"{diff.years} yr{'s' if diff.years > 1 else ''}")
        if diff.months:
            parts.append(f"{diff.months} mo")
        return " ".join(parts) or "< 1 mo"
    except Exception:
        return "Duration available"


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "showcase-api", "port": 8002}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
