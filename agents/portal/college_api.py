"""
College Partner Portal — FastAPI Backend
Serves institution-specific pipeline and demand data.

Run: uvicorn college_api:app --reload --port 8004
"""
import sys, os, json
import numpy as np
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts"))
from pgconfig import PG_CONFIG

app = FastAPI(title="Waifinder College Partner API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3004", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def query(sql, params=None):
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def query_one(sql, params=None):
    rows = query(sql, params)
    return rows[0] if rows else {}


@app.get("/api/college/dashboard/{token}")
def get_college_dashboard(token: str):
    # Get partner info
    partner = query_one("SELECT * FROM college_partners WHERE id = %s", (token,))
    if not partner:
        raise HTTPException(status_code=404, detail="College partner not found")

    pattern = partner['search_pattern']
    institution_name = partner['institution_name']

    # Also match on institution field directly
    institution_pattern = f"%{institution_name.lower().split()[0]}%{institution_name.lower().split()[-1]}%"

    # 1. Graduate pipeline stats
    pipeline = query_one("""
        SELECT
            count(*) as total_in_pipeline,
            count(*) FILTER (WHERE resume_parsed = TRUE) as parsed,
            count(*) FILTER (WHERE showcase_eligible = TRUE) as showcase_eligible,
            count(*) FILTER (WHERE showcase_active = TRUE) as showcase_active,
            count(*) FILTER (WHERE pipeline_status = 'placed') as placed,
            count(*) FILTER (WHERE pipeline_status = 'enrolled') as enrolled,
            count(*) FILTER (WHERE pipeline_status = 'applied') as applied,
            count(*) FILTER (WHERE pipeline_status = 'unknown') as unknown_status
        FROM students
        WHERE legacy_data::text ILIKE %s
           OR institution ILIKE %s
    """, (pattern, institution_pattern))

    total = pipeline.get('total_in_pipeline', 0)
    placed = pipeline.get('placed', 0)
    placement_rate = round(placed / total * 100, 1) if total > 0 else 0

    # Get student IDs for this institution
    student_ids_rows = query("""
        SELECT id FROM students
        WHERE legacy_data::text ILIKE %s OR institution ILIKE %s
    """, (pattern, institution_pattern))
    student_ids = [r['id'] for r in student_ids_rows]

    # 2. Top skills from their graduates
    top_skills = []
    if student_ids:
        placeholders = ",".join(["%s"] * len(student_ids))
        top_skills = query(f"""
            SELECT sk.skill_name, count(DISTINCT ss.student_id) as student_count
            FROM student_skills ss
            JOIN skills sk ON sk.skill_id = ss.skill_id
            WHERE ss.student_id IN ({placeholders})
            GROUP BY sk.skill_name
            ORDER BY count(DISTINCT ss.student_id) DESC
            LIMIT 15
        """, student_ids)

    # 3. Employer demand matching their skills
    # Get the top skills their grads have, find jobs wanting those skills
    grad_skill_names = [s['skill_name'].lower() for s in top_skills[:10]]

    demand_jobs = []
    if grad_skill_names:
        # Find job titles where cfa_skills overlaps with graduate skills
        all_jobs = query("""
            SELECT title, count(*) as listings,
                   avg(salary_min) as avg_salary_min,
                   avg(salary_max) as avg_salary_max,
                   legacy_data->>'cfa_skills' as skills_text
            FROM job_listings
            WHERE is_digital = TRUE AND source = 'lightcast'
            AND legacy_data->>'cfa_skills' IS NOT NULL
            GROUP BY title, legacy_data->>'cfa_skills'
            ORDER BY count(*) DESC
            LIMIT 200
        """)

        # Score each job by how many grad skills it mentions
        job_scores = {}
        for job in all_jobs:
            if not job['skills_text']:
                continue
            job_skills = set(s.strip().lower() for s in job['skills_text'].split(","))
            overlap = len(set(grad_skill_names) & job_skills)
            if overlap > 0:
                title = job['title']
                if title not in job_scores:
                    job_scores[title] = {
                        'title': title,
                        'listings': 0,
                        'matching_skills': overlap,
                        'avg_salary_min': [],
                        'avg_salary_max': [],
                    }
                job_scores[title]['listings'] += job['listings']
                if job.get('avg_salary_min'):
                    job_scores[title]['avg_salary_min'].append(float(job['avg_salary_min']))
                if job.get('avg_salary_max'):
                    job_scores[title]['avg_salary_max'].append(float(job['avg_salary_max']))

        for v in job_scores.values():
            v['avg_salary_min'] = round(sum(v['avg_salary_min']) / len(v['avg_salary_min'])) if v['avg_salary_min'] else None
            v['avg_salary_max'] = round(sum(v['avg_salary_max']) / len(v['avg_salary_max'])) if v['avg_salary_max'] else None

        demand_jobs = sorted(job_scores.values(), key=lambda x: -x['listings'])[:10]

    # 4. Skills gap — what employers need that grads lack
    # Get all skills from top demand jobs
    all_demand_skills = query("""
        WITH skill_mentions AS (
            SELECT trim(unnest(string_to_array(legacy_data->>'cfa_skills', ','))) as skill_name
            FROM job_listings
            WHERE source = 'lightcast' AND is_digital = TRUE
            AND legacy_data->>'cfa_skills' IS NOT NULL
        )
        SELECT skill_name, count(*) as demand_count
        FROM skill_mentions WHERE skill_name != ''
        GROUP BY skill_name
        ORDER BY demand_count DESC
        LIMIT 50
    """)

    grad_skill_set = set(s['skill_name'].lower() for s in top_skills)
    skills_gap = []
    for ds in all_demand_skills:
        if ds['skill_name'].lower() not in grad_skill_set:
            skills_gap.append({
                'skill': ds['skill_name'],
                'employer_demand': ds['demand_count'],
                'message': f"{ds['demand_count']} employers asked for {ds['skill_name']} -- not in your graduates' profiles"
            })
        if len(skills_gap) >= 10:
            break

    # 5. Recent matches -- students with gap analyses
    recent_matches = []
    if student_ids:
        recent_matches = query(f"""
            SELECT s.full_name, ga.target_role, ga.gap_score, ga.analyzed_at
            FROM gap_analyses ga
            JOIN students s ON s.id = ga.student_id
            WHERE ga.student_id IN ({placeholders})
            AND ga.gap_score > 0
            ORDER BY ga.gap_score DESC
            LIMIT 5
        """, student_ids)
        for m in recent_matches:
            if m.get('analyzed_at'):
                m['analyzed_at'] = m['analyzed_at'].isoformat()
            # Privacy: first name + last initial
            parts = (m.get('full_name') or '').split()
            m['display_name'] = f"{parts[0]} {parts[-1][0]}." if len(parts) > 1 else parts[0] if parts else "Student"
            del m['full_name']

    # 6. Morning briefing
    top_gap_skill = skills_gap[0]['skill'] if skills_gap else "cloud computing"
    top_gap_demand = skills_gap[0]['employer_demand'] if skills_gap else 0
    matched_count = len(recent_matches)

    briefing = (
        f"You have {total} graduates currently in the CFA pipeline. "
        f"{len(demand_jobs)} employer role types are looking for skills your graduates have right now. "
        f"Top curriculum signal this month: {top_gap_skill} demand ({top_gap_demand} listings) "
        f"-- not currently in your graduates' skill profiles."
    )

    return {
        "institution": {
            "name": institution_name,
            "contact_name": partner.get('contact_name'),
            "contact_email": partner.get('contact_email'),
            "programs": partner.get('programs', []),
        },
        "briefing": briefing,
        "pipeline": {
            "total_in_pipeline": total,
            "parsed_and_assessed": pipeline.get('parsed', 0),
            "matched_to_roles": matched_count,
            "placed": placed,
            "placement_rate": placement_rate,
            "by_status": {
                "enrolled": pipeline.get('enrolled', 0),
                "applied": pipeline.get('applied', 0),
                "unknown": pipeline.get('unknown_status', 0),
                "placed": placed,
            },
        },
        "top_skills": [{"skill": s['skill_name'], "students": s['student_count']} for s in top_skills],
        "employer_demand": demand_jobs,
        "skills_gap": skills_gap,
        "recent_matches": recent_matches,
        "cfa_contact": {
            "name": "Ritu Bahl",
            "email": "ritu@computingforall.org",
            "role": "Executive Director",
        },
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "college-api", "port": 8004}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
