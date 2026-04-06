"""
Career Services Agent -- Gap Analysis

For each student, finds the best-matching job(s) from job_listings,
compares the student's skills against the job's required skills,
identifies missing skills, computes a gap score (0-100), and
recommends upskilling priorities.

Gap score (normalized):
  100 = student has ALL core skills the job requires
  0   = student has NONE of the core skills
  Uses top 15 skills per job as "core" requirements rather than
  the full Lightcast taxonomy (which can list 30-60 skills).

Skill name normalization:
  Strips parenthetical qualifiers like "(Programming Language)"
  Case-insensitive matching
  Common alias mapping (e.g. "C#" <-> "C# (Programming Language)")

Stores results in gap_analyses table.
"""
import sys, os, json, re, psycopg2
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts"))
from pgconfig import PG_CONFIG

# Job titles to exclude from matching
TITLE_BLOCKLIST = {"unclassified", "not specified", "various", "multiple positions"}

# Max core skills to use for gap scoring
CORE_SKILLS_LIMIT = 15


def normalize_skill_name(name):
    """
    Normalize a skill name for matching:
    - Strip parenthetical qualifiers: "Python (Programming Language)" -> "Python"
    - Lowercase
    - Strip whitespace
    """
    if not name:
        return ""
    # Strip parenthetical content
    normalized = re.sub(r'\s*\([^)]*\)', '', name)
    # Strip trailing punctuation
    normalized = normalized.strip().strip('.,;:')
    return normalized.lower()


def load_skill_embeddings(conn):
    """Load skill name -> embedding vector map. Keyed by normalized name."""
    cur = conn.cursor()
    cur.execute("""
        SELECT skill_name, embedding_vector::text
        FROM skills WHERE embedding_vector IS NOT NULL
    """)
    result = {}
    raw_to_normalized = {}  # maps normalized -> original for display
    for name, vec_str in cur.fetchall():
        vals = [float(x) for x in vec_str.strip("[]").split(",")]
        vec = np.array(vals)
        # Store under both original lowercase and normalized name
        result[name.lower()] = vec
        norm = normalize_skill_name(name)
        if norm and norm not in result:
            result[norm] = vec
        raw_to_normalized[name.lower()] = norm
    return result, raw_to_normalized


def get_student_skills(conn, student_id):
    """Get distinct skills for a student."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT sk.skill_name
        FROM student_skills ss
        JOIN skills sk ON sk.skill_id = ss.skill_id
        WHERE ss.student_id = %s
    """, (student_id,))
    return [row[0] for row in cur.fetchall()]


def get_job_skills(conn, job_id, core_only=True):
    """
    Get skills for a job listing from cfa_skills field.
    If core_only=True, returns only the first CORE_SKILLS_LIMIT skills
    (Lightcast lists skills roughly by importance/frequency).
    """
    cur = conn.cursor()
    cur.execute("""
        SELECT legacy_data->>'cfa_skills' as skills_text
        FROM job_listings WHERE id = %s
    """, (job_id,))
    row = cur.fetchone()
    if not row or not row[0]:
        return [], []
    all_skills = [s.strip() for s in row[0].split(",") if s.strip()]
    core = all_skills[:CORE_SKILLS_LIMIT] if core_only else all_skills
    return core, all_skills


def cosine_sim(a, b):
    dot = np.dot(a, b)
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    return float(dot / norm) if norm > 0 else 0.0


def compute_student_embedding(student_skills, skill_map):
    """Average embedding of student skills (tries both raw and normalized names)."""
    vectors = []
    for s in student_skills:
        key = s.lower()
        if key in skill_map:
            vectors.append(skill_map[key])
        else:
            norm_key = normalize_skill_name(s)
            if norm_key in skill_map:
                vectors.append(skill_map[norm_key])
    if not vectors:
        return None
    avg = np.mean(vectors, axis=0)
    return avg / np.linalg.norm(avg)


def find_best_job_matches(conn, student_id, student_skills, skill_map, top_n=3):
    """Find the top N matching jobs for a student using embedding similarity."""
    student_emb = compute_student_embedding(student_skills, skill_map)
    if student_emb is None:
        return []

    cur = conn.cursor()
    # Get digital Lightcast jobs with skills
    cur.execute("""
        SELECT id, title, company_name, legacy_data->>'cfa_skills' as skills_text
        FROM job_listings
        WHERE source = 'lightcast' AND is_digital = TRUE
        AND legacy_data->>'cfa_skills' IS NOT NULL
    """)
    jobs = cur.fetchall()

    scored = []
    for jid, title, company, skills_text in jobs:
        if not skills_text:
            continue
        # Filter out blocklisted titles
        if title and title.lower().strip() in TITLE_BLOCKLIST:
            continue
        job_skills = [s.strip() for s in skills_text.split(",") if s.strip()]
        # Use core skills (first 15) for matching embedding too
        core_skills = job_skills[:CORE_SKILLS_LIMIT]
        job_vectors = []
        for s in core_skills:
            key = s.lower()
            if key in skill_map:
                job_vectors.append(skill_map[key])
            else:
                norm_key = normalize_skill_name(s)
                if norm_key in skill_map:
                    job_vectors.append(skill_map[norm_key])
        if not job_vectors:
            continue
        job_emb = np.mean(job_vectors, axis=0)
        job_emb = job_emb / np.linalg.norm(job_emb)
        sim = cosine_sim(student_emb, job_emb)
        scored.append((jid, title, company, job_skills, sim))

    scored.sort(key=lambda x: -x[4])
    return scored[:top_n]


def analyze_gap(student_skills, job_skills, skill_map):
    """
    Compute gap analysis between student skills and job requirements.

    Uses normalized skill names for matching:
    "Python (Programming Language)" matches "Python"
    "C# (Programming Language)" matches "C#"

    Scores against core skills (first 15) not full taxonomy.

    Returns:
        gap_score: 0-100 (100 = all core skills covered)
        matched_skills: skills the student has that the job wants
        missing_skills: skills the job wants that the student lacks
        near_matches: student skills semantically close to missing job skills
    """
    # Build normalized lookup sets
    student_raw = set(s.lower() for s in student_skills)
    student_norm = set(normalize_skill_name(s) for s in student_skills)
    student_all = student_raw | student_norm

    # Use only core skills (first CORE_SKILLS_LIMIT) for scoring
    core_job_skills = job_skills[:CORE_SKILLS_LIMIT]
    job_raw = set(s.lower() for s in core_job_skills)
    job_norm = set(normalize_skill_name(s) for s in core_job_skills)

    # Build mapping: normalized job skill -> original name
    job_norm_to_raw = {}
    for s in core_job_skills:
        job_norm_to_raw[normalize_skill_name(s)] = s.lower()
        job_norm_to_raw[s.lower()] = s.lower()

    # Exact matches: check raw-raw, raw-norm, norm-raw, norm-norm
    exact_matches = set()
    for js_raw in job_raw:
        js_norm = normalize_skill_name(js_raw)
        if js_raw in student_all or js_norm in student_all:
            exact_matches.add(js_raw)

    # For remaining job skills, check semantic similarity
    remaining_job = job_raw - exact_matches
    semantic_matches = set()
    near_matches = {}  # missing_skill -> closest student skill

    for js in remaining_job:
        # Try both raw and normalized keys in skill_map
        js_vec = skill_map.get(js)
        if js_vec is None:
            js_vec = skill_map.get(normalize_skill_name(js))
        if js_vec is None:
            continue

        best_sim = 0.0
        best_student_skill = None
        for ss in student_raw:
            ss_vec = skill_map.get(ss)
            if ss_vec is None:
                ss_vec = skill_map.get(normalize_skill_name(ss))
            if ss_vec is None:
                continue
            sim = cosine_sim(js_vec, ss_vec)
            if sim > best_sim:
                best_sim = sim
                best_student_skill = ss

        if best_sim >= 0.75:
            semantic_matches.add(js)
            near_matches[js] = (best_student_skill, round(best_sim, 3))
        elif best_sim >= 0.5:
            near_matches[js] = (best_student_skill, round(best_sim, 3))

    total_matched = len(exact_matches) + len(semantic_matches)
    total_core = len(job_raw)
    gap_score = round((total_matched / total_core * 100), 1) if total_core > 0 else 0

    truly_missing = job_raw - exact_matches - semantic_matches
    missing_list = sorted(truly_missing)

    return {
        "gap_score": gap_score,
        "matched_count": total_matched,
        "total_job_skills": total_core,
        "exact_matches": sorted(exact_matches),
        "semantic_matches": sorted(semantic_matches),
        "missing_skills": missing_list,
        "near_matches": near_matches,
    }


def recommend_upskilling(gap_result, skill_map, top_n=5):
    """
    Prioritize which missing skills to learn first.

    Priority factors:
    1. Skills that are closest to student's existing skills (easiest to learn)
    2. Skills that appear in multiple job listings (most marketable)
    """
    missing = gap_result["missing_skills"]
    near = gap_result["near_matches"]

    priorities = []
    for skill in missing:
        # Check if student has a near-match (transferable skill)
        near_info = near.get(skill)
        transferable = near_info[0] if near_info else None
        similarity = near_info[1] if near_info else 0.0

        # Priority score: higher = learn this first
        # Near-matches get higher priority (easier bridge)
        priority = similarity * 100  # 0-100 based on similarity to existing skills

        priorities.append({
            "skill": skill,
            "priority_score": round(priority, 1),
            "transferable_from": transferable,
            "similarity_to_existing": similarity,
            "recommendation": (
                f"Build on your {transferable} experience (similarity: {similarity})"
                if transferable
                else "New skill area - consider a structured course"
            ),
        })

    # Sort by priority (highest first = easiest to bridge)
    priorities.sort(key=lambda x: -x["priority_score"])
    return priorities[:top_n]


def run_gap_analysis(conn, student_ids=None, limit=10, verbose=True):
    """
    Run gap analysis for specified students or top N by skill count.
    """
    cur = conn.cursor()
    skill_map, norm_map = load_skill_embeddings(conn)
    print(f"Loaded {len(skill_map)} skill embeddings\n")

    if student_ids:
        placeholders = ",".join(["%s"] * len(student_ids))
        cur.execute(f"""
            SELECT s.id, s.full_name
            FROM students s
            WHERE s.id IN ({placeholders})
        """, student_ids)
    else:
        cur.execute("""
            SELECT s.id, s.full_name
            FROM students s
            JOIN student_skills ss ON ss.student_id = s.id
            GROUP BY s.id, s.full_name
            ORDER BY count(DISTINCT ss.skill_id) DESC
            LIMIT %s
        """, (limit,))

    students = cur.fetchall()
    results = []

    for student_id, name in students:
        if verbose:
            print(f"{'='*60}")
            print(f"Student: {name}")
            print(f"{'='*60}")

        student_skills = get_student_skills(conn, student_id)
        if verbose:
            print(f"  Skills ({len(student_skills)}): {', '.join(student_skills[:10])}...")

        # Find best matching jobs
        top_matches = find_best_job_matches(
            conn, student_id, student_skills, skill_map, top_n=3
        )

        if not top_matches:
            if verbose:
                print("  No matching jobs found.\n")
            continue

        for rank, (job_id, job_title, company, job_skills, match_sim) in enumerate(top_matches, 1):
            if verbose and rank == 1:
                print(f"\n  Top match: {job_title} (similarity: {match_sim:.3f})")
                print(f"  Job skills ({len(job_skills)}): {', '.join(job_skills[:10])}...")

            # Run gap analysis
            gap = analyze_gap(student_skills, job_skills, skill_map)

            # Get upskilling recommendations
            upskilling = recommend_upskilling(gap, skill_map, top_n=5)

            if verbose and rank == 1:
                print(f"\n  GAP SCORE: {gap['gap_score']}/100")
                print(f"  Matched: {gap['matched_count']}/{gap['total_job_skills']} job skills")
                print(f"    Exact matches: {len(gap['exact_matches'])}")
                print(f"    Semantic matches: {len(gap['semantic_matches'])}")
                print(f"  Missing: {len(gap['missing_skills'])} skills")
                if gap['missing_skills'][:5]:
                    print(f"    Top missing: {', '.join(gap['missing_skills'][:5])}")
                print(f"\n  UPSKILLING PRIORITIES:")
                for i, rec in enumerate(upskilling, 1):
                    print(f"    {i}. {rec['skill']} (priority: {rec['priority_score']})")
                    print(f"       {rec['recommendation']}")
                print()

            # Store in gap_analyses table
            cur.execute("""
                INSERT INTO gap_analyses (
                    student_id, target_role, target_job_listing_id,
                    gap_score, missing_skills, recommendations, analyzed_at
                ) VALUES (%s, %s, %s, %s, %s, %s, NOW())
                RETURNING id
            """, (
                student_id,
                job_title,
                job_id,
                gap["gap_score"],
                gap["missing_skills"],
                json.dumps({
                    "match_similarity": round(match_sim, 3),
                    "matched_count": gap["matched_count"],
                    "total_job_skills": gap["total_job_skills"],
                    "exact_matches": gap["exact_matches"],
                    "semantic_matches": gap["semantic_matches"],
                    "near_matches": {k: list(v) for k, v in gap["near_matches"].items()},
                    "upskilling": upskilling,
                }),
            ))

            results.append({
                "student": name,
                "student_id": student_id,
                "job": job_title,
                "job_id": job_id,
                "match_similarity": match_sim,
                "gap_score": gap["gap_score"],
                "matched": gap["matched_count"],
                "total": gap["total_job_skills"],
                "missing_count": len(gap["missing_skills"]),
            })

    conn.commit()
    return results


def main():
    print("=" * 60)
    print("Career Services Agent -- Gap Analysis")
    print("=" * 60)

    conn = psycopg2.connect(**PG_CONFIG)

    # Clear previous gap analyses for clean test
    cur = conn.cursor()
    cur.execute("DELETE FROM gap_analyses")
    conn.commit()

    # Run for top 10 students by skill count, top 3 job matches each
    results = run_gap_analysis(conn, limit=10, verbose=True)

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    print(f"\nTotal gap analyses generated: {len(results)}")
    if results:
        scores = [r["gap_score"] for r in results]
        print(f"Gap score range: {min(scores):.1f} - {max(scores):.1f}")
        print(f"Average gap score: {sum(scores)/len(scores):.1f}")
        print(f"\nBy student (top match only):")
        seen = set()
        for r in results:
            if r["student"] not in seen:
                seen.add(r["student"])
                print(f"  {r['student']:<25} -> {r['job'][:35]:<35} "
                      f"Gap: {r['gap_score']:>5.1f} "
                      f"({r['matched']}/{r['total']} skills)")

    conn.close()


if __name__ == "__main__":
    main()
