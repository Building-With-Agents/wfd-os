"""
Reporting Agent — FastAPI Backend
Serves dashboard data from PostgreSQL for the Borderplex Labor Market Intelligence dashboard.

Endpoints:
  GET /api/overview     - Summary metrics
  GET /api/skills       - Top skills demand data
  GET /api/pipeline     - Student pipeline funnel
  GET /api/gaps         - Skills gap analysis (demand vs supply)
  GET /api/jobs         - Top job titles and recent listings

Run: uvicorn api:app --reload --port 8000
"""
from datetime import datetime, timezone
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras

from wfdos_common.config import PG_CONFIG
from wfdos_common.errors import install_error_handlers
from wfdos_common.logging import RequestContextMiddleware

app = FastAPI(title="Waifinder Reporting API", version="0.1.0")

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# #29 — structured error envelope on every 4xx/5xx.
install_error_handlers(app)


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


@app.get("/api/overview")
def overview():
    """Summary metrics for dashboard header."""
    total_jobs = query_one("SELECT count(*) as n FROM job_listings WHERE is_digital = TRUE OR is_digital IS NULL")
    total_students = query_one("SELECT count(*) as n FROM students")
    showcase_active = query_one("SELECT count(*) as n FROM students WHERE showcase_active = TRUE")
    total_employers = query_one("SELECT count(*) as n FROM employers")
    total_skills = query_one("SELECT count(DISTINCT skill_id) FROM student_skills")
    parsed_resumes = query_one("SELECT count(*) as n FROM students WHERE resume_parsed = TRUE")
    digital_pct = query_one("""
        SELECT round(count(*) FILTER (WHERE is_digital = TRUE)::numeric
                     / NULLIF(count(*), 0) * 100, 1) as pct
        FROM job_listings WHERE source = 'lightcast'
    """)

    # Pipeline by stage
    pipeline = query("""
        SELECT pipeline_status, count(*) as n
        FROM students GROUP BY pipeline_status ORDER BY n DESC
    """)

    return {
        "total_jobs": total_jobs.get("n", 0),
        "total_students": total_students.get("n", 0),
        "showcase_active": showcase_active.get("n", 0),
        "total_employers": total_employers.get("n", 0),
        "unique_skills_tracked": total_skills.get("count", 0),
        "resumes_parsed": parsed_resumes.get("n", 0),
        "digital_role_pct": digital_pct.get("pct", 0),
        "pipeline_summary": pipeline,
        "region": "Borderplex / El Paso, TX",
        "last_updated": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/skills")
def skills_demand():
    """Top skills by employer demand from job listings."""
    # Parse skills from Lightcast cfa_skills field
    top_skills = query("""
        WITH skill_mentions AS (
            SELECT unnest(string_to_array(legacy_data->>'cfa_skills', ',')) as skill_raw
            FROM job_listings
            WHERE source = 'lightcast' AND (is_digital = TRUE OR is_digital IS NULL)
            AND legacy_data->>'cfa_skills' IS NOT NULL
        ),
        skill_counts AS (
            SELECT trim(skill_raw) as skill_name, count(*) as demand_count
            FROM skill_mentions
            WHERE trim(skill_raw) != ''
            GROUP BY trim(skill_raw)
        )
        SELECT skill_name, demand_count
        FROM skill_counts
        ORDER BY demand_count DESC
        LIMIT 20
    """)

    total_jobs = query_one("""
        SELECT count(*) as n FROM job_listings
        WHERE source = 'lightcast' AND (is_digital = TRUE OR is_digital IS NULL)
    """)

    for s in top_skills:
        s["pct_of_jobs"] = round(s["demand_count"] / max(total_jobs.get("n", 1), 1) * 100, 1)

    return {
        "top_skills": top_skills,
        "total_digital_jobs": total_jobs.get("n", 0),
        "region": "Washington State (Lightcast Q3-Q4 2024)",
    }


@app.get("/api/pipeline")
def student_pipeline():
    """Student pipeline funnel data."""
    by_status = query("""
        SELECT pipeline_status, count(*) as n
        FROM students GROUP BY pipeline_status ORDER BY n DESC
    """)

    by_quality = query("""
        SELECT data_quality, count(*) as n
        FROM students GROUP BY data_quality ORDER BY n DESC
    """)

    completeness = query("""
        SELECT
            CASE
                WHEN profile_completeness_score >= 0.8 THEN '80-100%'
                WHEN profile_completeness_score >= 0.6 THEN '60-80%'
                WHEN profile_completeness_score >= 0.4 THEN '40-60%'
                WHEN profile_completeness_score >= 0.2 THEN '20-40%'
                ELSE '0-20%'
            END as band,
            count(*) as n
        FROM students GROUP BY 1 ORDER BY 1
    """)

    resume_stats = query_one("""
        SELECT
            count(*) FILTER (WHERE resume_parsed = TRUE) as parsed,
            count(*) FILTER (WHERE resume_blob_path IS NOT NULL AND resume_parsed = FALSE) as unparsed,
            count(*) FILTER (WHERE resume_blob_path IS NULL) as no_resume
        FROM students
    """)

    showcase = query_one("""
        SELECT
            count(*) FILTER (WHERE showcase_eligible = TRUE) as eligible,
            count(*) FILTER (WHERE showcase_active = TRUE) as active
        FROM students
    """)

    return {
        "by_status": by_status,
        "by_quality": by_quality,
        "completeness_distribution": completeness,
        "resume_stats": resume_stats,
        "showcase": showcase,
        "total_students": sum(r["n"] for r in by_status),
    }


@app.get("/api/gaps")
def skills_gaps():
    """Skills gap: employer demand vs student supply."""
    # Demand side: top skills from job listings
    demand = query("""
        WITH skill_mentions AS (
            SELECT trim(unnest(string_to_array(legacy_data->>'cfa_skills', ','))) as skill_name
            FROM job_listings
            WHERE source = 'lightcast' AND (is_digital = TRUE OR is_digital IS NULL)
            AND legacy_data->>'cfa_skills' IS NOT NULL
        )
        SELECT skill_name, count(*) as demand_count
        FROM skill_mentions WHERE skill_name != ''
        GROUP BY skill_name ORDER BY demand_count DESC LIMIT 15
    """)

    # Supply side: skills students actually have
    supply = query("""
        SELECT sk.skill_name, count(DISTINCT ss.student_id) as student_count
        FROM student_skills ss
        JOIN skills sk ON sk.skill_id = ss.skill_id
        GROUP BY sk.skill_name
        ORDER BY count(DISTINCT ss.student_id) DESC
        LIMIT 50
    """)
    supply_map = {s["skill_name"].lower(): s["student_count"] for s in supply}

    # Build gap data
    gap_data = []
    for d in demand:
        name = d["skill_name"]
        student_count = supply_map.get(name.lower(), 0)
        gap_data.append({
            "skill": name,
            "demand": d["demand_count"],
            "supply": student_count,
            "gap": d["demand_count"] - student_count,
        })

    # Most common missing skills from gap_analyses
    critical_gaps = query("""
        SELECT unnest(missing_skills) as skill, count(*) as frequency
        FROM gap_analyses
        GROUP BY 1 ORDER BY 2 DESC LIMIT 10
    """)

    total_demand = sum(d["demand"] for d in gap_data)
    total_supply = sum(d["supply"] for d in gap_data)
    coverage_pct = round(total_supply / max(total_demand, 1) * 100, 1)

    return {
        "gap_data": gap_data,
        "critical_missing_skills": critical_gaps,
        "coverage_pct": coverage_pct,
        "total_gap_analyses": query_one("SELECT count(*) as n FROM gap_analyses").get("n", 0),
    }


@app.get("/api/jobs")
def job_listings_data():
    """Job listing stats and top titles."""
    by_source = query("""
        SELECT source, count(*) as n,
               count(*) FILTER (WHERE is_digital = TRUE) as digital
        FROM job_listings GROUP BY source ORDER BY n DESC
    """)

    top_titles = query("""
        SELECT title, count(*) as n
        FROM job_listings
        WHERE is_digital = TRUE AND source = 'lightcast'
        AND title NOT IN ('Unclassified')
        GROUP BY title ORDER BY n DESC LIMIT 10
    """)

    top_locations = query("""
        SELECT COALESCE(city, 'Unknown') as location, count(*) as n
        FROM job_listings
        WHERE is_digital = TRUE
        GROUP BY city ORDER BY n DESC LIMIT 10
    """)

    return {
        "by_source": by_source,
        "top_titles": top_titles,
        "top_locations": top_locations,
        "total_listings": sum(r["n"] for r in by_source),
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
