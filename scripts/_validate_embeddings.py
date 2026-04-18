"""
Phase 2D Stage 4 — embedding-quality validation.

Picks 5 students across profile shapes + 5 jobs across role shapes
and prints top-5 cross-entity matches for each. Read-only; does not
modify any DB rows. Output is reference material for Ritu, not a
committed artifact.
"""
from __future__ import annotations

import os
import sys
import json
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psycopg2
import psycopg2.extras
from pgconfig import PG_CONFIG
from backfill_embeddings import (  # type: ignore
    render_student,
    render_job,
    extract_job_description,
    JOB_DESC_MAX_CHARS,
)

conn = psycopg2.connect(**PG_CONFIG)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)


def pick_students() -> list[dict]:
    """Pick 5 students across distinct profile shapes."""
    picks: list[dict] = []

    # A — strong UW CS student: 8+ skills + career_objective
    cur.execute("""
        SELECT s.id::text AS id, s.full_name, s.institution, s.degree,
               s.field_of_study, s.graduation_year, s.city, s.state,
               s.legacy_data->>'career_objective' AS career_objective,
               array_agg(DISTINCT sk.skill_name ORDER BY sk.skill_name) AS skills
        FROM students s
        JOIN student_skills ss ON ss.student_id = s.id
        JOIN skills sk ON sk.skill_id = ss.skill_id
        JOIN embeddings e ON e.entity_type='student' AND e.entity_id::uuid = s.id
        WHERE s.institution ILIKE '%University of Washington%'
          AND (s.field_of_study ILIKE '%computer science%'
               OR s.field_of_study ILIKE '%informatics%')
          AND s.legacy_data->>'career_objective' IS NOT NULL
        GROUP BY s.id
        HAVING count(DISTINCT sk.skill_id) >= 8
        LIMIT 1
    """)
    picks.append({"label": "A — UW CS, dense skills + objective", "row": dict(cur.fetchone())})

    # B — parsed resume but missing location OR graduation_year
    cur.execute("""
        SELECT s.id::text AS id, s.full_name, s.institution, s.degree,
               s.field_of_study, s.graduation_year, s.city, s.state,
               s.legacy_data->>'career_objective' AS career_objective,
               array_agg(DISTINCT sk.skill_name ORDER BY sk.skill_name) AS skills
        FROM students s
        JOIN student_skills ss ON ss.student_id = s.id
        JOIN skills sk ON sk.skill_id = ss.skill_id
        JOIN embeddings e ON e.entity_type='student' AND e.entity_id::uuid = s.id
        WHERE s.institution IS NOT NULL
          AND (s.city IS NULL OR s.graduation_year IS NULL)
        GROUP BY s.id
        LIMIT 1
    """)
    picks.append({"label": "B — parsed resume, lighter metadata", "row": dict(cur.fetchone())})

    # C — non-UW student
    cur.execute("""
        SELECT s.id::text AS id, s.full_name, s.institution, s.degree,
               s.field_of_study, s.graduation_year, s.city, s.state,
               s.legacy_data->>'career_objective' AS career_objective,
               array_agg(DISTINCT sk.skill_name ORDER BY sk.skill_name) AS skills
        FROM students s
        JOIN student_skills ss ON ss.student_id = s.id
        JOIN skills sk ON sk.skill_id = ss.skill_id
        JOIN embeddings e ON e.entity_type='student' AND e.entity_id::uuid = s.id
        WHERE s.institution IS NOT NULL
          AND s.institution NOT ILIKE '%University of Washington%'
          AND s.institution NOT ILIKE '%UW%'
        GROUP BY s.id
        HAVING count(DISTINCT sk.skill_id) >= 5
        ORDER BY s.id
        LIMIT 1
    """)
    picks.append({"label": "C — non-UW institution", "row": dict(cur.fetchone())})

    # D — non-traditional background pivoting toward tech
    cur.execute("""
        SELECT s.id::text AS id, s.full_name, s.institution, s.degree,
               s.field_of_study, s.graduation_year, s.city, s.state,
               s.legacy_data->>'career_objective' AS career_objective,
               array_agg(DISTINCT sk.skill_name ORDER BY sk.skill_name) AS skills
        FROM students s
        JOIN student_skills ss ON ss.student_id = s.id
        JOIN skills sk ON sk.skill_id = ss.skill_id
        JOIN embeddings e ON e.entity_type='student' AND e.entity_id::uuid = s.id
        WHERE (s.field_of_study ILIKE '%psychology%'
               OR s.field_of_study ILIKE '%business%'
               OR s.field_of_study ILIKE '%linguist%'
               OR s.field_of_study ILIKE '%biology%'
               OR s.field_of_study ILIKE '%english%')
        GROUP BY s.id
        ORDER BY s.id
        LIMIT 1
    """)
    picks.append({"label": "D — non-traditional pivoting to tech", "row": dict(cur.fetchone())})

    # E — shortest rendered text. Do it in Python (render every student
    # row, keep the shortest among students that weren't already picked).
    cur.execute("""
        SELECT s.id::text AS id, s.full_name, s.institution, s.degree,
               s.field_of_study, s.graduation_year, s.city, s.state,
               s.legacy_data->>'career_objective' AS career_objective,
               array_agg(DISTINCT sk.skill_name ORDER BY sk.skill_name) AS skills
        FROM students s
        JOIN student_skills ss ON ss.student_id = s.id
        JOIN skills sk ON sk.skill_id = ss.skill_id
        JOIN embeddings e ON e.entity_type='student' AND e.entity_id::uuid = s.id
        GROUP BY s.id
    """)
    already = {p["row"]["id"] for p in picks}
    shortest = None
    shortest_len = 10**9
    for r in cur.fetchall():
        r = dict(r)
        if r["id"] in already:
            continue
        text, _ = render_student(r)
        if len(text) < shortest_len:
            shortest = r
            shortest_len = len(text)
    picks.append({"label": "E — shortest rendered text", "row": shortest})

    return picks


def pick_jobs() -> list[dict]:
    picks: list[dict] = []

    # a — pure software engineering (not data, not AI)
    cur.execute("""
        SELECT id::text AS id, title, company, location, city, state,
               seniority, employment_type, is_remote, skills_required,
               job_description
        FROM jobs_enriched
        WHERE title ILIKE '%software engineer%'
          AND title NOT ILIKE '%ai%'
          AND title NOT ILIKE '%ml%'
          AND title NOT ILIKE '%machine learning%'
          AND title NOT ILIKE '%data%'
        ORDER BY id LIMIT 1
    """)
    r = cur.fetchone()
    picks.append({"label": "a — pure software engineering", "row": dict(r) if r else None})

    # b — data engineering
    cur.execute("""
        SELECT id::text AS id, title, company, location, city, state,
               seniority, employment_type, is_remote, skills_required,
               job_description
        FROM jobs_enriched
        WHERE title ILIKE '%data engineer%'
        ORDER BY id LIMIT 1
    """)
    picks.append({"label": "b — data engineering", "row": dict(cur.fetchone())})

    # c — AI/ML
    cur.execute("""
        SELECT id::text AS id, title, company, location, city, state,
               seniority, employment_type, is_remote, skills_required,
               job_description
        FROM jobs_enriched
        WHERE (title ILIKE '%ai engineer%' OR title ILIKE '%ml engineer%'
               OR title ILIKE '%machine learning%')
          AND id != 96
        ORDER BY id LIMIT 1
    """)
    picks.append({"label": "c — AI/ML", "row": dict(cur.fetchone())})

    # d — non-technical / adjacent (workforce development, program mgmt)
    cur.execute("""
        SELECT id::text AS id, title, company, location, city, state,
               seniority, employment_type, is_remote, skills_required,
               job_description
        FROM jobs_enriched
        WHERE title NOT ILIKE '%engineer%'
          AND title NOT ILIKE '%developer%'
          AND title NOT ILIKE '%analyst%'
          AND title NOT ILIKE '%data%'
          AND title NOT ILIKE '%software%'
          AND title NOT ILIKE '%ai/%'
          AND id IN (80, 81, 82, 83)
        ORDER BY id LIMIT 1
    """)
    r = cur.fetchone()
    if r is None:
        cur.execute("""
            SELECT id::text AS id, title, company, location, city, state,
                   seniority, employment_type, is_remote, skills_required,
                   job_description
            FROM jobs_enriched
            WHERE title ILIKE '%workforce%' OR title ILIKE '%manager%'
               OR title ILIKE '%director%' OR title ILIKE '%business%'
            ORDER BY id LIMIT 1
        """)
        r = cur.fetchone()
    picks.append({"label": "d — non-technical/adjacent", "row": dict(r)})

    # e — Blue Origin id=96 (the fallback-to-raw case)
    cur.execute("""
        SELECT id::text AS id, title, company, location, city, state,
               seniority, employment_type, is_remote, skills_required,
               job_description
        FROM jobs_enriched WHERE id=96
    """)
    picks.append({"label": "e — id=96 Blue Origin (raw fallback)", "row": dict(cur.fetchone())})

    return picks


def top_job_matches_for_student(student_id: str, k: int = 5) -> list[dict]:
    cur.execute(
        """
        SELECT e_j.entity_id AS job_id,
               je.title,
               je.company,
               1 - (e_s.embedding <=> e_j.embedding) AS cosine
        FROM embeddings e_s
        JOIN embeddings e_j
          ON e_j.entity_type='jobs_enriched'
         AND e_j.text_template_version='job_v1'
        JOIN jobs_enriched je ON je.id = e_j.entity_id::int
        WHERE e_s.entity_type='student'
          AND e_s.entity_id=%s
          AND e_s.text_template_version='student_v1'
        ORDER BY e_s.embedding <=> e_j.embedding
        LIMIT %s
        """,
        (student_id, k),
    )
    return [dict(r) for r in cur.fetchall()]


def top_student_matches_for_job(job_id: str, k: int = 5) -> list[dict]:
    cur.execute(
        """
        SELECT e_s.entity_id AS student_id,
               s.full_name,
               s.institution,
               s.field_of_study,
               (SELECT array_agg(sk.skill_name ORDER BY sk.skill_name)
                FROM (SELECT sk2.skill_name FROM student_skills ss
                      JOIN skills sk2 ON sk2.skill_id = ss.skill_id
                      WHERE ss.student_id = s.id
                      ORDER BY sk2.skill_name LIMIT 3) sk) AS top_skills,
               1 - (e_j.embedding <=> e_s.embedding) AS cosine
        FROM embeddings e_j
        JOIN embeddings e_s
          ON e_s.entity_type='student'
         AND e_s.text_template_version='student_v1'
        JOIN students s ON s.id = e_s.entity_id::uuid
        WHERE e_j.entity_type='jobs_enriched'
          AND e_j.entity_id=%s
          AND e_j.text_template_version='job_v1'
        ORDER BY e_j.embedding <=> e_s.embedding
        LIMIT %s
        """,
        (job_id, k),
    )
    return [dict(r) for r in cur.fetchall()]


def prepare_job_text(row: dict) -> tuple[str, str]:
    """Reproduce the text that was embedded (re-extract the description).
    Returns (rendered_text, extraction_marker).
    """
    raw = row.get("job_description")
    marker = "job_description_raw"
    if raw and raw.strip():
        extracted, _ = extract_job_description(raw)
        if extracted is not None:
            row = dict(row)
            row["job_description"] = extracted
            marker = "job_description_extracted"
        else:
            row = dict(row)
            t = raw.strip()
            if len(t) > JOB_DESC_MAX_CHARS:
                t = t[:JOB_DESC_MAX_CHARS].rstrip() + "..."
            row["job_description"] = t
    text, _ = render_job(row)
    return text, marker


def redact_name(name: str | None) -> str:
    if not name:
        return "—"
    return name[:2] + "***"


def hr():
    print("=" * 78)


# ============================================================
# STUDENTS
# ============================================================
print()
hr(); print("STUDENTS — top 5 job matches each"); hr()

for pick in pick_students():
    row = pick["row"]
    text, _ = render_student(row)
    print(f"\n[{pick['label']}]")
    print(f"  entity_id: {row['id']}")
    print(f"  rendered student_v1 text ({len(text)} chars):")
    for line in textwrap.wrap(text, 76):
        print(f"    {line}")
    print(f"  top 5 job matches:")
    for m in top_job_matches_for_student(row["id"]):
        title = (m["title"] or "")[:55]
        company = (m["company"] or "")[:30]
        print(f"    cos={m['cosine']:.4f}  id={m['job_id']:>4s}  {title} @ {company}")


# ============================================================
# JOBS
# ============================================================
print()
hr(); print("JOBS — top 5 student matches each"); hr()

for pick in pick_jobs():
    row = pick["row"]
    if not row:
        continue
    text, marker = prepare_job_text(row)
    print(f"\n[{pick['label']}]")
    print(f"  entity_id: {row['id']}  —  {row['title']} @ {row['company']}")
    print(f"  embedded text marker: {marker}")
    first_300 = text[:300].replace("\n", " ")
    print(f"  rendered job_v1 text (first 300 chars):")
    for line in textwrap.wrap(first_300, 76):
        print(f"    {line}")
    print(f"  top 5 student matches:")
    for m in top_student_matches_for_job(row["id"]):
        inst = (m["institution"] or "—")[:38]
        fos = (m["field_of_study"] or "—")[:32]
        sk = (m["top_skills"] or [])[:3]
        sk_str = ", ".join(sk) if sk else "—"
        name = redact_name(m["full_name"])
        print(f"    cos={m['cosine']:.4f}  {name:8s} {inst:38s} | {fos:32s} | skills: {sk_str}")


print()
conn.close()
