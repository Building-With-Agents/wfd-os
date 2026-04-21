"""Phase B Task 4 — gap analyses for WSB Cohort 1 (Option B methodology).

Produces one gap_analyses row per (apprentice, top-3 matched job) pair,
using agents/job_board/match_narrative.compute_overlap() — the Phase 2G
structured strengths/gaps extractor.

Methodology (Option B per Ritu, 2026-04-20):
  - strong_matches: student skills that match (bidirectional substring)
    either a structured job requirement or the description prose.
  - gaps: job requirements the student doesn't visibly have, after
    passing through _is_garbage_requirement filter.
  - gap_score: strong / (strong + gaps) * 100 — % of detected
    requirements covered. 100 if zero gaps after filtering.

Inputs:
  - Top-3 matches per apprentice from `cohort_matches` (the new authoritative
    match table from migration 016).
  - Student dict shape expected by compute_overlap:
      {"full_name", "institution", "degree", "field_of_study",
       "graduation_year", "career_objective",
       "skills": [{"name": str}, ...],
       "work_experience": [...]}  (work_experience not used here but included
                                   for parity with compute_overlap callers)
  - Job dict shape expected by compute_overlap:
      {"title", "company", "job_description", "skills_required": [str, ...]}

Side-effect of this task (per Ritu): when `jobs_enriched.skills_required`
is NULL for a WSB job that has matches, we LLM-extract a requirements
list and persist it back to the column. Makes the extraction reusable for
Task 5 narratives and future work.

Tenancy:
  - Matches read scoped to cohort_matches.tenant_id = WSB.
  - Students/jobs read with tenant_id filter.
  - gap_analyses inserts set tenant_id = WSB. target_job_listing_id left
    NULL (FK points to job_listings, incompatible with jobs_enriched.id
    type — see tech debt note in Task 4 report).
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from pathlib import Path

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv


SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from pgconfig import PG_CONFIG  # noqa: E402

# agents/job_board/match_narrative.py is on this branch as an uncommitted
# Phase 2G working file. We import it read-only; we do not modify it.
sys.path.insert(0, str(SCRIPTS_DIR.parent / "agents" / "job_board"))
import match_narrative as mn  # noqa: E402 — uncommitted Phase 2G module


# .env with AZURE_OPENAI_* at repo root
ENV_PATH = Path(r"C:\Users\ritub\Projects\wfd-os\.env")
load_dotenv(ENV_PATH, override=True)

AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AZURE_KEY = os.getenv("AZURE_OPENAI_KEY", "")
CHAT_DEPLOYMENT = "chat-gpt41mini"
API_VERSION = "2024-02-01"

WSB_CODE = "WSB"
TOP_N_FOR_GAP = 3  # 9 apprentices × 3 matches = 27 gap_analyses rows

SKILL_EXTRACTION_PROMPT = """You are extracting technical skills and requirements from a job posting.

Given the job description below, return a JSON array of 8 to 15 concrete technical
skills, tools, languages, frameworks, platforms, or specific hard requirements the
role calls for.

Each entry MUST be:
  - 1 to 4 words
  - A concrete noun phrase naming a skill, tool, or technology
  - NOT a benefit, schedule, pay range, location, or soft-skill sentence
  - NOT ending in a period (no full sentences)

Good examples: "Python", "SQL", "React", "Azure", "Data Analysis", "Machine Learning",
"REST APIs", "Linux", "Docker", "Kubernetes", "Tableau", "PowerBI"

Bad examples (DO NOT RETURN THESE): "3+ years of experience", "Bachelor's degree in CS",
"Strong communication and teamwork", "Competitive salary and benefits", "#J-1234-ABC"

Output: a JSON array of strings. No prose, no prefix, no explanation.

Job description:
\"\"\"
{job_description}
\"\"\"
"""


def llm_extract_skills(job_description: str) -> list[str]:
    """Call Azure OpenAI chat-gpt41mini to extract a skills-required list.
    Returns a list of strings. Raises on API failure.
    """
    if not job_description or not job_description.strip():
        return []
    url = (
        f"{AZURE_ENDPOINT}/openai/deployments/{CHAT_DEPLOYMENT}"
        f"/chat/completions?api-version={API_VERSION}"
    )
    # Trim long descriptions
    trimmed = job_description[:3000]
    prompt = SKILL_EXTRACTION_PROMPT.format(job_description=trimmed)
    resp = requests.post(
        url,
        headers={"api-key": AZURE_KEY, "Content-Type": "application/json"},
        json={
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.0,
            "max_tokens": 400,
        },
        timeout=30,
    )
    resp.raise_for_status()
    content = resp.json()["choices"][0]["message"]["content"].strip()
    # Strip ```json fences if present
    if content.startswith("```"):
        content = re.sub(r"^```(?:json)?\s*", "", content)
        content = re.sub(r"\s*```\s*$", "", content)
    arr = json.loads(content)
    if not isinstance(arr, list):
        raise ValueError(f"expected JSON array, got {type(arr).__name__}")
    # Keep only strings
    return [s.strip() for s in arr if isinstance(s, str) and s.strip()]


def populate_wsb_job_skills_required(conn, wsb_uuid: str) -> dict:
    """For every WSB job with NULL skills_required, LLM-extract and persist.
    Returns {extracted: N, already_set: M, failed: [ids]}.
    """
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT id, title, job_description, skills_required
        FROM jobs_enriched
        WHERE tenant_id = %s::uuid
        ORDER BY id
        """,
        (wsb_uuid,),
    )
    jobs = cur.fetchall()
    extracted = 0
    already_set = 0
    failed: list[dict] = []
    for j in jobs:
        if j["skills_required"] is not None and len(j["skills_required"]) > 0:
            already_set += 1
            continue
        try:
            skills = llm_extract_skills(j["job_description"] or "")
            # Persist as TEXT[]
            upd = conn.cursor()
            upd.execute(
                "UPDATE jobs_enriched SET skills_required = %s::text[] WHERE id = %s AND tenant_id = %s::uuid",
                (skills, j["id"], wsb_uuid),
            )
            conn.commit()
            extracted += 1
            safe = (j["title"] or "").encode("ascii", "replace").decode("ascii")[:55]
            print(f"  extracted #{j['id']:<4} {safe:<57} → {len(skills)} skills")
            time.sleep(0.1)
        except Exception as e:
            conn.rollback()
            failed.append({"id": j["id"], "title": j["title"], "error": str(e)[:200]})
            print(f"  FAIL #{j['id']}: {str(e)[:200]}")
    return {"extracted": extracted, "already_set": already_set, "failed": failed}


def fetch_student(conn, student_id: str, wsb_uuid: str) -> dict:
    """Build the student dict shape compute_overlap expects, scoped to WSB."""
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT id::text AS id, full_name, email, phone,
               city, state,
               institution, degree, field_of_study, graduation_year,
               linkedin_url, github_url, portfolio_url,
               pipeline_status, pipeline_stage, cohort_id, track,
               legacy_data->>'career_objective' AS career_objective
        FROM students
        WHERE id = %s::uuid AND tenant_id = %s::uuid
        """,
        (student_id, wsb_uuid),
    )
    s = cur.fetchone()
    if not s:
        raise RuntimeError(f"student {student_id} not found in WSB tenant")
    student = dict(s)

    # Skills as list of {name, source} — matches compute_overlap's reading
    # of sk.get("name").
    cur.execute(
        """
        SELECT sk.skill_name AS name, ss.source
        FROM student_skills ss
        JOIN skills sk ON sk.skill_id = ss.skill_id
        WHERE ss.student_id = %s::uuid
        ORDER BY sk.skill_name
        """,
        (student_id,),
    )
    student["skills"] = [dict(r) for r in cur.fetchall()]

    cur.execute(
        """
        SELECT company, title, description AS responsibilities,
               start_date, end_date, is_current
        FROM student_work_experience
        WHERE student_id = %s::uuid
        ORDER BY is_current DESC NULLS LAST,
                 end_date   DESC NULLS FIRST,
                 start_date DESC NULLS LAST
        """,
        (student_id,),
    )
    student["work_experience"] = [dict(r) for r in cur.fetchall()]
    return student


def fetch_job(conn, job_id: int, wsb_uuid: str) -> dict:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT id, title, company, company_domain,
               city, state, country, is_remote,
               employment_type, seniority,
               job_description, skills_required
        FROM jobs_enriched
        WHERE id = %s AND tenant_id = %s::uuid
        """,
        (job_id, wsb_uuid),
    )
    j = cur.fetchone()
    if not j:
        raise RuntimeError(f"job {job_id} not found in WSB tenant")
    return dict(j)


def gap_score_from_overlap(overlap: dict) -> float:
    """Option B gap-score formula — % of detected requirements covered.
    Formula: strong / (strong + gaps) * 100. Returns 100 when no gaps
    were detected (either because the filter dropped everything or the
    student covers all surviving reqs). Returns 0 if both sides empty.
    """
    strong_n = len(overlap.get("strong_matches") or [])
    gaps_n = len(overlap.get("gaps") or [])
    if strong_n == 0 and gaps_n == 0:
        return 0.0
    if gaps_n == 0:
        return 100.0
    return round(strong_n / (strong_n + gaps_n) * 100, 1)


def lookup_tenant_uuid(conn, code: str) -> str:
    cur = conn.cursor()
    cur.execute("SELECT id FROM tenants WHERE code = %s", (code,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"tenant code {code!r} not seeded")
    return str(row[0])


def main() -> int:
    print("=" * 70)
    print("Phase B Task 4 — Gap analyses (Option B: compute_overlap per match)")
    print("=" * 70)

    if not AZURE_ENDPOINT or not AZURE_KEY:
        print("ERROR: AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_KEY not set")
        return 2

    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False

    wsb = lookup_tenant_uuid(conn, WSB_CODE)
    cfa = lookup_tenant_uuid(conn, "CFA")
    print(f"WSB tenant_id: {wsb}")
    print()

    # --- Step 1: populate jobs_enriched.skills_required for any WSB job missing it ---
    print("Step 1: Extract skills_required for WSB jobs (where NULL)…")
    ext = populate_wsb_job_skills_required(conn, wsb)
    print(f"  extracted: {ext['extracted']}  already_set: {ext['already_set']}  "
          f"failed: {len(ext['failed'])}")
    if ext["failed"]:
        print("  Failures (proceeding; those jobs won't get gap analyses):")
        for f in ext["failed"]:
            print(f"    - #{f['id']}: {f['error']}")
    print()

    # --- Baseline counts for verification ---
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM gap_analyses WHERE tenant_id = %s::uuid", (cfa,))
    cfa_before = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM gap_analyses WHERE tenant_id = %s::uuid", (wsb,))
    wsb_before = cur.fetchone()[0]
    print(f"gap_analyses before: CFA={cfa_before}  WSB={wsb_before}")

    # --- Step 2: clear prior WSB gap_analyses so re-runs are idempotent ---
    cur.execute("DELETE FROM gap_analyses WHERE tenant_id = %s::uuid", (wsb,))
    deleted_prior = cur.rowcount
    print(f"  deleted {deleted_prior} prior WSB rows (idempotent reset)")
    print()

    # --- Step 3: fetch top-N matches per apprentice from cohort_matches ---
    cur.execute(
        """
        SELECT cm.student_id, cm.job_id, cm.match_rank,
               cm.cosine_similarity, cm.id AS cohort_match_id,
               s.full_name
        FROM cohort_matches cm
        JOIN students s ON s.id = cm.student_id
        WHERE cm.tenant_id = %s::uuid
          AND cm.match_rank <= %s
        ORDER BY s.full_name, cm.match_rank
        """,
        (wsb, TOP_N_FOR_GAP),
    )
    top_matches = cur.fetchall()
    print(f"Step 2: top-{TOP_N_FOR_GAP} matches to gap-analyze: {len(top_matches)} (expected {9 * TOP_N_FOR_GAP})")
    print()

    # --- Step 4: compute_overlap + insert per (apprentice, job) ---
    total_inserted = 0
    per_apprentice_counts: dict[str, int] = {}
    skipped: list[dict] = []
    failed: list[dict] = []
    sample_rows: list[dict] = []

    for (student_id, job_id, match_rank, cosine, cohort_match_id, full_name) in top_matches:
        try:
            student = fetch_student(conn, str(student_id), wsb)
            job = fetch_job(conn, job_id, wsb)

            # Skip jobs that couldn't get skills_required extracted
            if not job.get("skills_required"):
                # Still run compute_overlap — it'll just produce 0 gaps
                # (and strengths only from description-match). Flag it.
                print(f"  WARN job #{job_id}: skills_required is empty (extraction failed or empty)")

            overlap = mn.compute_overlap(student, job)
            gap_score = gap_score_from_overlap(overlap)

            # missing_skills (TEXT[]) = gap areas (strings)
            missing_skills = [g["area"] for g in (overlap.get("gaps") or [])]

            # Recommendations JSONB — Phase-B shape per Ritu's spec
            recommendations = {
                "cosine_similarity": float(cosine),
                "cohort_match_id": str(cohort_match_id),
                "jobs_enriched_id": int(job_id),
                "match_rank": int(match_rank),
                "job_title": job.get("title"),
                "job_company": job.get("company"),
                "strong_matches": overlap.get("strong_matches") or [],
                "partial_matches": overlap.get("partial_matches") or [],
                "gaps": overlap.get("gaps") or [],
            }

            cur.execute(
                """
                INSERT INTO gap_analyses (
                    id, student_id, target_role, target_job_listing_id,
                    gap_score, missing_skills, recommendations,
                    analyzed_at, tenant_id
                ) VALUES (
                    gen_random_uuid(), %s::uuid, %s, NULL,
                    %s, %s, %s::jsonb,
                    NOW(), %s::uuid
                )
                RETURNING id
                """,
                (
                    str(student_id),
                    job.get("title"),
                    gap_score,
                    missing_skills,
                    json.dumps(recommendations),
                    wsb,
                ),
            )
            new_id = cur.fetchone()[0]
            conn.commit()
            total_inserted += 1
            per_apprentice_counts[full_name] = per_apprentice_counts.get(full_name, 0) + 1

            # Capture a spot-check sample row (the first one)
            if len(sample_rows) < 1:
                sample_rows.append({
                    "id": str(new_id),
                    "student": full_name,
                    "job_id": job_id,
                    "job_title": job.get("title"),
                    "match_rank": match_rank,
                    "cosine": float(cosine),
                    "gap_score": gap_score,
                    "strengths": overlap.get("strong_matches") or [],
                    "gaps": overlap.get("gaps") or [],
                    "missing_skills": missing_skills,
                })

            strong_n = len(overlap.get("strong_matches") or [])
            gaps_n = len(overlap.get("gaps") or [])
            safe_title = (job.get("title") or "").encode("ascii", "replace").decode("ascii")[:40]
            print(f"  {full_name[:25]:<27} rank {match_rank}  #{job_id:<4} "
                  f"{safe_title:<42} cos={float(cosine):.3f}  "
                  f"strengths={strong_n}  gaps={gaps_n}  gap_score={gap_score}")
        except Exception as e:
            conn.rollback()
            failed.append({
                "student_id": str(student_id), "job_id": job_id,
                "full_name": full_name, "error": str(e)[:200],
            })
            print(f"  FAIL {full_name} × #{job_id}: {str(e)[:200]}")

    # --- Step 5: verify ---
    cur.execute("SELECT COUNT(*) FROM gap_analyses WHERE tenant_id = %s::uuid", (cfa,))
    cfa_after = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM gap_analyses WHERE tenant_id = %s::uuid", (wsb,))
    wsb_after = cur.fetchone()[0]

    conn.close()

    print()
    print("=" * 70)
    print(f"Inserted: {total_inserted}  Failed: {len(failed)}")
    print(f"gap_analyses after:  CFA={cfa_after}  WSB={wsb_after}")
    cfa_ok = cfa_after == cfa_before
    wsb_ok = wsb_after == total_inserted
    print(f"  CFA drift: {'NONE' if cfa_ok else 'CHANGED'} (expected {cfa_before}, got {cfa_after})")
    print(f"  WSB count: {'OK' if wsb_ok else 'MISMATCH'} (expected {total_inserted}, got {wsb_after})")

    print()
    print("Per-apprentice gap analysis counts:")
    for name, n in sorted(per_apprentice_counts.items()):
        tag = "OK" if n == TOP_N_FOR_GAP else "WARN"
        print(f"  [{tag}] {name:<30} {n} gap analyses")

    if failed:
        print()
        print("Failures:")
        for f in failed:
            print(f"  - {f['full_name']} × #{f['job_id']}: {f['error']}")

    if sample_rows:
        s = sample_rows[0]
        print()
        print("=" * 70)
        print(f"SAMPLE gap analysis — {s['student']} × '{s['job_title'][:55]}'")
        print("=" * 70)
        print(f"  gap_analyses.id:    {s['id']}")
        print(f"  gap_score:          {s['gap_score']}")
        print(f"  match_rank:         {s['match_rank']}")
        print(f"  cosine_similarity:  {s['cosine']:.4f}")
        print(f"  strong_matches ({len(s['strengths'])}):")
        for m in s["strengths"]:
            safe = (m.get("area") or "").encode("ascii", "replace").decode("ascii")
            print(f"    • {safe}  — {m.get('evidence')}")
        print(f"  gaps ({len(s['gaps'])}):")
        for g in s["gaps"]:
            safe = (g.get("area") or "").encode("ascii", "replace").decode("ascii")
            print(f"    • {safe}  — {g.get('note')}")
        print(f"  missing_skills[] (text array):  {s['missing_skills']}")

    return 0 if (not failed and cfa_ok and wsb_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
