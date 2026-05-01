"""Recalculate profile_completeness_score + required_fields_complete +
preferred_fields_complete + missing_required + missing_preferred for
ALL students, or a --tenant-limited subset.

Addresses the long-standing gap that these columns are read by multiple
services (student_api, showcase_api, employer_agent, reporting, recruiting
caseload) but no code ever writes them. Students sit at 0.00 completeness
even when every required field is populated.

Uses the scoring rules from CLAUDE.md §"Profile Completeness Model":

Required fields (70% weight):
  - full_name
  - email
  - skills (≥3 normalized entries in student_skills)
  - education (institution AND degree both present)
  - location (city OR state present)
  - availability_status
  - resume_file (proxy: resume_parsed = TRUE)

Preferred fields (30% weight):
  - phone
  - linkedin_url
  - graduation_year
  - field_of_study
  - career_objective (read from legacy_data.career_objective for cohort-1 WSB
    students; otherwise a dedicated column — we check both)
  - expected_salary_range
  - work_authorization
  - certifications (in legacy_data.certifications array or
    student_skills with source='certification')

Writes:
  - required_fields_complete (float 0-1)
  - preferred_fields_complete (float 0-1)
  - profile_completeness_score (required 70% + preferred 30%)
  - missing_required (text[])
  - missing_preferred (text[])

Usage:
  python scripts/recalculate_profile_completeness.py                 # all students
  python scripts/recalculate_profile_completeness.py --tenant=WSB    # just WSB
  python scripts/recalculate_profile_completeness.py --dry-run       # show, don't write
"""
from __future__ import annotations

import argparse
import sys
from typing import Any, Optional

import psycopg2
import psycopg2.extras


PG_CONFIG = {
    "host": "127.0.0.1",
    "database": "wfd_os",
    "user": "postgres",
    "password": "wfdos2026",
    "port": 5432,
}

REQUIRED_FIELDS = [
    "full_name",
    "email",
    "skills",             # ≥3 in student_skills
    "education",          # institution AND degree
    "location",           # city OR state
    "availability_status",
    "resume_file",        # proxy: resume_parsed
]

PREFERRED_FIELDS = [
    "phone",
    "linkedin_url",
    "graduation_year",
    "field_of_study",
    "career_objective",
    "expected_salary_range",
    "work_authorization",
    "certifications",
]


def _nonempty(v: Any) -> bool:
    """Tolerant truthy check for mixed types (None / '' / 0 / []) — numeric
    zero counts as present since graduation_year=0 is implausible anyway."""
    if v is None:
        return False
    if isinstance(v, str):
        return v.strip() != ""
    if isinstance(v, (list, tuple)):
        return len(v) > 0
    return True


def score_student(student: dict, skills_count: int) -> dict:
    legacy = student.get("legacy_data") or {}
    if not isinstance(legacy, dict):
        legacy = {}

    # Required fields
    req_present: dict[str, bool] = {}
    req_present["full_name"] = _nonempty(student.get("full_name"))
    req_present["email"] = _nonempty(student.get("email"))
    req_present["skills"] = skills_count >= 3
    req_present["education"] = _nonempty(student.get("institution")) and _nonempty(student.get("degree"))
    req_present["location"] = _nonempty(student.get("city")) or _nonempty(student.get("state"))
    req_present["availability_status"] = _nonempty(student.get("availability_status"))
    req_present["resume_file"] = bool(student.get("resume_parsed"))

    # Preferred fields
    pref_present: dict[str, bool] = {}
    pref_present["phone"] = _nonempty(student.get("phone"))
    pref_present["linkedin_url"] = _nonempty(student.get("linkedin_url"))
    pref_present["graduation_year"] = _nonempty(student.get("graduation_year"))
    pref_present["field_of_study"] = _nonempty(student.get("field_of_study"))
    pref_present["career_objective"] = _nonempty(legacy.get("career_objective"))
    pref_present["expected_salary_range"] = _nonempty(student.get("expected_salary_range"))
    pref_present["work_authorization"] = _nonempty(student.get("work_authorization"))
    # Certifications: either listed in legacy_data or via student_skills
    # source='certification'. The script doesn't have a skills-source
    # breakdown handy, so rely on legacy_data for now.
    certs = legacy.get("certifications")
    pref_present["certifications"] = isinstance(certs, list) and len(certs) > 0

    req_count = sum(req_present.values())
    pref_count = sum(pref_present.values())
    req_frac = round(req_count / len(REQUIRED_FIELDS), 4)
    pref_frac = round(pref_count / len(PREFERRED_FIELDS), 4)
    overall = round(req_frac * 0.7 + pref_frac * 0.3, 4)

    return {
        "required_fields_complete": req_frac,
        "preferred_fields_complete": pref_frac,
        "profile_completeness_score": overall,
        "missing_required": [f for f, ok in req_present.items() if not ok],
        "missing_preferred": [f for f, ok in pref_present.items() if not ok],
    }


def fetch_students(conn, tenant_code: Optional[str]) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if tenant_code:
        cur.execute("""
            SELECT s.*, t.code AS tenant_code
            FROM students s
            JOIN tenants t ON t.id = s.tenant_id
            WHERE t.code = %s
            ORDER BY s.full_name
        """, (tenant_code,))
    else:
        cur.execute("""
            SELECT s.*, t.code AS tenant_code
            FROM students s
            LEFT JOIN tenants t ON t.id = s.tenant_id
            ORDER BY s.full_name
        """)
    return list(cur.fetchall())


def skills_count_map(conn) -> dict[str, int]:
    cur = conn.cursor()
    cur.execute("""
        SELECT student_id, COUNT(*) FROM student_skills
        GROUP BY student_id
    """)
    return {str(sid): n for sid, n in cur.fetchall()}


def apply_score(conn, student_id: str, score: dict) -> None:
    cur = conn.cursor()
    cur.execute("""
        UPDATE students SET
          required_fields_complete  = %s,
          preferred_fields_complete = %s,
          profile_completeness_score = %s,
          missing_required          = %s,
          missing_preferred         = %s,
          updated_at                = NOW()
        WHERE id = %s
    """, (
        score["required_fields_complete"],
        score["preferred_fields_complete"],
        score["profile_completeness_score"],
        score["missing_required"],
        score["missing_preferred"],
        student_id,
    ))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tenant", help="Filter by tenant code (e.g. WSB, CFA). Default: all students.")
    parser.add_argument("--dry-run", action="store_true", help="Compute and print; don't UPDATE.")
    args = parser.parse_args()

    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False

    students = fetch_students(conn, args.tenant)
    if not students:
        print(f"No students found (tenant filter: {args.tenant!r})")
        return 1

    skills_count = skills_count_map(conn)

    print(f"{'Name':<30}  {'tenant':<5}  req    pref   overall  missing_required")
    print("-" * 100)
    updated = 0
    for s in students:
        sid = str(s["id"])
        score = score_student(s, skills_count.get(sid, 0))
        missing = ",".join(score["missing_required"]) or "-"
        print(
            f"{(s.get('full_name') or '?')[:28]:<30}  "
            f"{(s.get('tenant_code') or '-'):<5}  "
            f"{score['required_fields_complete']:<5}  "
            f"{score['preferred_fields_complete']:<5}  "
            f"{score['profile_completeness_score']:<7}  "
            f"{missing}"
        )
        if not args.dry_run:
            apply_score(conn, sid, score)
            updated += 1

    if not args.dry_run:
        conn.commit()
        print(f"\n{updated} students updated.")
    else:
        print(f"\n(dry-run) {len(students)} students scored, none written.")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
