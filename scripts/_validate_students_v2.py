"""
Stage 4b — re-validate the same 5 students after student_v2 template change.

Reads the 5 hardcoded entity_ids Ritu reviewed in Stage 4a, renders each
with render_student (now v2), and shows top-5 job matches. Read-only.
"""
from __future__ import annotations

import os
import sys
import textwrap

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import psycopg2
import psycopg2.extras
from pgconfig import PG_CONFIG
from backfill_embeddings import render_student, STUDENT_TEMPLATE_VERSION

# Same 5 rows validated in Stage 4a, so the comparison is apples-to-apples.
FIVE = [
    ("A — UW CS, dense skills + objective",  "04867834-a5aa-441e-bd83-5598c1733def"),
    ("B — parsed resume, lighter metadata",  "012c48d5-7add-46b7-9efe-e3c5167cd548"),
    ("C — non-UW institution",                "0539188f-5427-4fbe-9571-123d3a571fe9"),
    ("D — non-traditional pivoting to tech", "05727e4d-cfe2-49e3-9a47-8b995991a259"),
    ("E — shortest rendered text",            "140f89b1-d2da-4d4a-b642-287972e1aa3d"),
]

conn = psycopg2.connect(**PG_CONFIG)
cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

STUDENT_SQL = """
SELECT s.id::text AS id, s.full_name, s.institution, s.degree,
       s.field_of_study, s.graduation_year, s.city, s.state,
       s.legacy_data->>'career_objective' AS career_objective,
       array_agg(DISTINCT sk.skill_name ORDER BY sk.skill_name) AS skills
FROM students s
JOIN student_skills ss ON ss.student_id = s.id
JOIN skills sk ON sk.skill_id = ss.skill_id
WHERE s.id = %s::uuid
GROUP BY s.id
"""

TOP_JOBS_SQL = """
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
  AND e_s.text_template_version=%s
ORDER BY e_s.embedding <=> e_j.embedding
LIMIT 5
"""

print(f"Template version in use: {STUDENT_TEMPLATE_VERSION}\n")
print("=" * 78)

for label, sid in FIVE:
    cur.execute(STUDENT_SQL, (sid,))
    row = dict(cur.fetchone())
    text, _ = render_student(row)
    print(f"\n[{label}]  entity_id: {row['id']}")
    print(f"  rendered {STUDENT_TEMPLATE_VERSION} ({len(text)} chars):")
    for line in textwrap.wrap(text, 76):
        print(f"    {line}")

    cur.execute(TOP_JOBS_SQL, (sid, STUDENT_TEMPLATE_VERSION))
    matches = cur.fetchall()
    print(f"  top 5 job matches (v2):")
    for m in matches:
        m = dict(m)
        title = (m["title"] or "")[:55]
        company = (m["company"] or "")[:30]
        print(f"    cos={m['cosine']:.4f}  id={m['job_id']:>4s}  {title} @ {company}")

conn.close()
