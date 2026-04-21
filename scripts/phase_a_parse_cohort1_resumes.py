"""Phase A — Task 2, Step 2/2: Parse Cohort 1 apprentice resumes locally and
INSERT them as new students tagged tenant=WSB, cohort_id='cohort-1-feb-2026'.

Reads local PDFs from data/cohort1_resumes/, sends each to Gemini 2.5 Flash
using the same EXTRACTION_PROMPT as agents/profile/parse_resumes.py, and
creates a new `students` row (not UPDATE — these are new apprentices, not
Dataverse-migrated records). Also populates student_skills and
student_work_experience.

Decision (b) per Ritu: bypass Azure Blob Storage; parse local files directly.

CLAUDE.md rules: READ from local filesystem + Gemini, WRITE only to
PostgreSQL (target table: `students`, `student_skills`,
`student_work_experience`). No modifications to any legacy system.
"""
from __future__ import annotations

import base64
import json
import os
import sys
import time
from datetime import date
from pathlib import Path

import psycopg2
import google.generativeai as genai
from dotenv import load_dotenv


WORKTREE = Path(r"C:\Users\ritub\Projects\wfd-os\.claude\worktrees\stupefied-tharp-41af25")
ENV_PATH = Path(r"C:\Users\ritub\Projects\wfd-os\.env")
load_dotenv(ENV_PATH, override=True)

RESUME_DIR = WORKTREE / "data" / "cohort1_resumes"
COHORT_ID = "cohort-1-feb-2026"
SOURCE_SYSTEM = "cohort-1-sharepoint-2026-02-23"
PIPELINE_STATUS_NEW = "enrolled"  # per CLAUDE.md Stage 3: Training

PG_CONFIG = {
    "host": "127.0.0.1",
    "database": "wfd_os",
    "user": "postgres",
    "password": "wfdos2026",
    "port": 5432,
}

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")


# Same prompt as agents/profile/parse_resumes.py — kept verbatim so the
# extraction shape matches existing Dataverse-parsed records.
EXTRACTION_PROMPT = """Extract the following structured information from this resume PDF.
Return ONLY valid JSON with these fields (use null for missing fields):

{
  "full_name": "First Last",
  "email": "email@example.com",
  "phone": "555-123-4567",
  "city": "City name",
  "state": "State (2-letter code if US)",
  "zipcode": "12345",
  "institution": "Most recent school/university",
  "degree": "Degree type (e.g. BS, BA, MS, High School Diploma)",
  "field_of_study": "Major or field",
  "graduation_year": 2024,
  "linkedin_url": "https://linkedin.com/in/...",
  "github_url": "https://github.com/...",
  "portfolio_url": "https://...",
  "skills": ["skill1", "skill2", "skill3"],
  "certifications": ["cert1", "cert2"],
  "work_experience": [
    {
      "company": "Company Name",
      "title": "Job Title",
      "start_date": "2023-01",
      "end_date": "2024-06",
      "is_current": false
    }
  ],
  "career_objective": "Brief summary or objective if stated",
  "work_authorization": "US Citizen / Green Card / OPT / etc if mentioned"
}

Be thorough. Extract ALL skills mentioned anywhere in the resume.
For education, use the most recent or highest degree.
Return ONLY the JSON object, no other text."""


def parse_pdf_with_gemini(pdf_bytes: bytes) -> dict:
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
    model = genai.GenerativeModel(GEMINI_MODEL)
    resp = model.generate_content([
        {"mime_type": "application/pdf", "data": pdf_b64},
        EXTRACTION_PROMPT,
    ])
    text = resp.text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    return json.loads(text)


def calculate_confidence(p: dict) -> float:
    """Mirror of parse_resumes.py::calculate_confidence."""
    checks = [
        p.get("full_name") is not None,
        p.get("email") is not None,
        p.get("phone") is not None,
        p.get("city") is not None or p.get("state") is not None,
        p.get("institution") is not None,
        p.get("degree") is not None,
        bool(p.get("skills") and len(p["skills"]) >= 1),
        bool(p.get("skills") and len(p["skills"]) >= 3),
        bool(p.get("work_experience")),
        p.get("field_of_study") is not None,
    ]
    return round(sum(checks) / len(checks), 2)


def classify_data_quality(conf: float) -> str:
    if conf >= 0.8:
        return "complete"
    if conf >= 0.5:
        return "partial"
    return "minimal"


def normalize_date(val):
    """Fix partial dates: YYYY -> YYYY-01-01, YYYY-MM -> YYYY-MM-01.
    Returns None if unparseable.
    """
    if not val:
        return None
    s = str(val)
    if len(s) == 4:
        s = s + "-01-01"
    elif len(s) == 7:
        s = s + "-01"
    try:
        date.fromisoformat(s)
        return s
    except Exception:
        return None


def wsb_tenant_id(conn) -> str:
    cur = conn.cursor()
    cur.execute("SELECT id FROM tenants WHERE code = 'WSB'")
    row = cur.fetchone()
    if not row:
        raise RuntimeError("WSB tenant not seeded — run migration 014 first")
    return str(row[0])


def insert_apprentice(conn, tenant_uuid: str, filename: str, parsed: dict, confidence: float) -> str:
    """Create a new student row + skills + work experience. Returns the new UUID."""
    cur = conn.cursor()
    skills = parsed.get("skills") or []
    work_exp = parsed.get("work_experience") or []
    certs = parsed.get("certifications") or []
    data_quality = classify_data_quality(confidence)

    # INSERT students (new row, not UPDATE)
    cur.execute("""
        INSERT INTO students (
            id,
            tenant_id,
            full_name, email, phone,
            city, state, zipcode,
            institution, degree, field_of_study, graduation_year,
            linkedin_url, github_url, portfolio_url,
            work_authorization,
            resume_parsed, parse_confidence_score,
            showcase_eligible, showcase_active,
            source_system, original_record_id, migration_date,
            pipeline_status, data_quality,
            cohort_id,
            legacy_data,
            created_at, updated_at
        ) VALUES (
            gen_random_uuid(),
            %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s,
            %s,
            TRUE, %s,
            FALSE, FALSE,
            %s, %s, NOW(),
            %s, %s,
            %s,
            %s::jsonb,
            NOW(), NOW()
        )
        RETURNING id
    """, (
        tenant_uuid,
        (parsed.get("full_name") or "")[:255] or filename.replace(".pdf", ""),
        parsed.get("email"),
        parsed.get("phone"),
        parsed.get("city"),
        parsed.get("state"),
        parsed.get("zipcode"),
        parsed.get("institution"),
        parsed.get("degree"),
        parsed.get("field_of_study"),
        parsed.get("graduation_year"),
        parsed.get("linkedin_url"),
        parsed.get("github_url"),
        parsed.get("portfolio_url"),
        parsed.get("work_authorization"),
        confidence,
        SOURCE_SYSTEM,
        filename,
        PIPELINE_STATUS_NEW,
        data_quality,
        COHORT_ID,
        json.dumps({
            "resume_local_path": f"data/cohort1_resumes/{filename}",
            "resume_source": "sharepoint/cfatechsectorleadership/UTEP & Borderplex/Feb 23rd 2026 Cohort Resumes",
            "resume_parsed_data": {"skills_extracted": skills, "work_count": len(work_exp)},
            "certifications": certs,
            "career_objective": parsed.get("career_objective"),
        }),
    ))
    student_id = str(cur.fetchone()[0])

    # student_skills — exact-match taxonomy lookup (same pattern as parse_resumes.py)
    for skill_name in (skills or [])[:50]:
        cur.execute("""
            INSERT INTO student_skills (student_id, skill_id, source)
            SELECT %s, skill_id, 'resume_parse'
            FROM skills
            WHERE LOWER(skill_name) = LOWER(%s)
            ON CONFLICT DO NOTHING
        """, (student_id, skill_name.strip()))

    # student_work_experience
    for exp in (work_exp or [])[:10]:
        if not (exp.get("company") or exp.get("title")):
            continue
        start = normalize_date(exp.get("start_date"))
        end = normalize_date(exp.get("end_date"))
        cur.execute("""
            INSERT INTO student_work_experience
                (student_id, company, title, start_date, end_date, is_current)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (
            student_id,
            (exp.get("company") or "")[:255],
            (exp.get("title") or "")[:255],
            start,
            end,
            bool(exp.get("is_current", False)),
        ))

    return student_id


def ingested_count_for_cohort(conn) -> int:
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM students WHERE cohort_id = %s", (COHORT_ID,))
    return cur.fetchone()[0]


def main() -> int:
    print("=" * 60)
    print("Phase A Task 2 — Step 2: Parse + INSERT Cohort 1 apprentices")
    print("=" * 60)

    if not os.getenv("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY missing from .env")
        return 2

    if not RESUME_DIR.exists():
        print(f"ERROR: {RESUME_DIR} does not exist — run the SharePoint fetch first")
        return 3

    pdfs = sorted(RESUME_DIR.glob("*.pdf"))
    if not pdfs:
        print(f"ERROR: no PDFs found in {RESUME_DIR}")
        return 4

    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False

    already = ingested_count_for_cohort(conn)
    if already > 0:
        print(f"WARNING: {already} apprentices already ingested under cohort_id='{COHORT_ID}'.")
        print("Re-running this script would create duplicates.")
        print("If you want to re-ingest, DELETE existing cohort-1 rows first.")
        conn.close()
        return 5

    tenant_uuid = wsb_tenant_id(conn)
    print(f"WSB tenant_id: {tenant_uuid}")
    print(f"cohort_id:     {COHORT_ID}")
    print(f"source_system: {SOURCE_SYSTEM}")
    print(f"resumes found: {len(pdfs)}")
    print()

    summary = []
    ok = 0
    fail = 0

    for i, pdf in enumerate(pdfs, 1):
        progress = f"[{i}/{len(pdfs)}]"
        filename = pdf.name
        try:
            pdf_bytes = pdf.read_bytes()
            if len(pdf_bytes) < 500:
                print(f"{progress} SKIP too-small {filename} ({len(pdf_bytes)} bytes)")
                fail += 1
                continue

            parsed = parse_pdf_with_gemini(pdf_bytes)
            conf = calculate_confidence(parsed)
            student_id = insert_apprentice(conn, tenant_uuid, filename, parsed, conf)
            conn.commit()

            skills_count = len(parsed.get("skills") or [])
            work_count = len(parsed.get("work_experience") or [])
            tier = "HIGH" if conf >= 0.8 else "MED" if conf >= 0.5 else "LOW"
            name = parsed.get("full_name") or filename
            print(f"{progress} {tier} conf={conf} skills={skills_count} work={work_count}  {name}")
            summary.append({
                "file": filename,
                "student_id": student_id,
                "full_name": parsed.get("full_name"),
                "email": parsed.get("email"),
                "phone": parsed.get("phone"),
                "city_state": f"{parsed.get('city') or ''}{', ' + parsed.get('state') if parsed.get('state') else ''}".strip(),
                "institution": parsed.get("institution"),
                "degree": parsed.get("degree"),
                "field_of_study": parsed.get("field_of_study"),
                "graduation_year": parsed.get("graduation_year"),
                "top_skills": (parsed.get("skills") or [])[:8],
                "total_skills": skills_count,
                "work_entries": work_count,
                "confidence": conf,
                "tier": tier,
            })
            ok += 1
            # Gemini rate-limit courtesy
            time.sleep(4)

        except json.JSONDecodeError as e:
            conn.rollback()
            fail += 1
            print(f"{progress} JSON_ERROR {filename}: {e}")
        except Exception as e:
            conn.rollback()
            fail += 1
            err = str(e)[:200]
            print(f"{progress} FAIL {filename}: {err}")
            # Light rate-limit pause on known 429
            if "429" in err or "resource_exhausted" in err.lower() or "quota" in err.lower():
                print("  (rate-limited — pausing 30s)")
                time.sleep(30)

    conn.close()

    print()
    print("=" * 60)
    print(f"Ingestion done: {ok} ok, {fail} failed out of {len(pdfs)}")
    print("=" * 60)
    print()
    print("Per-apprentice spot-check summary:")
    for row in summary:
        print()
        print(f"  {row['full_name']}  (tier {row['tier']}, conf {row['confidence']})")
        print(f"    file:        {row['file']}")
        print(f"    student_id:  {row['student_id']}")
        print(f"    email:       {row['email']}")
        print(f"    phone:       {row['phone']}")
        print(f"    location:    {row['city_state']}")
        print(f"    education:   {row['degree']} {row['field_of_study']} at {row['institution']} ({row['graduation_year']})")
        print(f"    top skills:  {', '.join(row['top_skills'])}")
        print(f"    skills/work: {row['total_skills']} skills, {row['work_entries']} work entries")

    # Emit a JSON digest so the summary doc can pick it up
    digest_path = WORKTREE / "data" / "cohort1_ingestion_digest.json"
    digest_path.write_text(json.dumps({
        "ok": ok,
        "fail": fail,
        "total": len(pdfs),
        "apprentices": summary,
    }, indent=2), encoding="utf-8")
    print()
    print(f"Digest written: {digest_path}")

    return 0 if fail == 0 else 6


if __name__ == "__main__":
    sys.exit(main())
