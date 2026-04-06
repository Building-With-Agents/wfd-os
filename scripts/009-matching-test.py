"""
Matching quality check: 10 students x 10 jobs using pgvector cosine similarity.

Strategy:
- Student embedding = average of their skill embeddings from skills table
- Job embedding = average of skill embeddings matched from job title + description keywords
- For Lightcast jobs: use cfa_skills field directly
- For Arbeitnow jobs: use title + tags as skill proxy
- Cosine similarity via pgvector
"""
import sys, os, json, psycopg2
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from pgconfig import PG_CONFIG


def get_skill_embedding_map(conn):
    """Load all skill embeddings as numpy arrays, keyed by lowercase name."""
    cur = conn.cursor()
    cur.execute("""
        SELECT skill_name, embedding_vector::text
        FROM skills
        WHERE embedding_vector IS NOT NULL
    """)
    result = {}
    for name, vec_str in cur.fetchall():
        # Parse "[0.1,0.2,...]" format
        vals = [float(x) for x in vec_str.strip("[]").split(",")]
        result[name.lower()] = np.array(vals)
    return result


def compute_student_embedding(conn, student_id, skill_map):
    """Average embedding of student's skills."""
    cur = conn.cursor()
    cur.execute("""
        SELECT DISTINCT sk.skill_name
        FROM student_skills ss
        JOIN skills sk ON sk.skill_id = ss.skill_id
        WHERE ss.student_id = %s
    """, (student_id,))

    vectors = []
    skill_names = []
    for (name,) in cur.fetchall():
        vec = skill_map.get(name.lower())
        if vec is not None:
            vectors.append(vec)
            skill_names.append(name)

    if not vectors:
        return None, []

    avg = np.mean(vectors, axis=0)
    # Normalize
    norm = np.linalg.norm(avg)
    if norm > 0:
        avg = avg / norm
    return avg, skill_names


def compute_job_embedding(conn, job_id, skill_map):
    """Average embedding of skills mentioned in job listing."""
    cur = conn.cursor()
    cur.execute("""
        SELECT title, description,
               legacy_data->>'cfa_skills' as lightcast_skills,
               legacy_data->>'tags' as tags
        FROM job_listings WHERE id = %s
    """, (job_id,))
    row = cur.fetchone()
    if not row:
        return None, []

    title, desc, lc_skills, tags = row

    # Collect candidate skill names from the job
    candidate_skills = set()

    # From Lightcast cfa_skills field
    if lc_skills:
        for s in lc_skills.split(","):
            candidate_skills.add(s.strip().lower())

    # From tags
    if tags:
        try:
            tag_list = json.loads(tags) if isinstance(tags, str) else tags
            for t in tag_list:
                candidate_skills.add(t.lower())
        except:
            pass

    # From title keywords
    if title:
        for word in title.lower().replace("-", " ").replace("/", " ").split():
            if len(word) > 2:
                candidate_skills.add(word)

    # Match against skill taxonomy
    vectors = []
    matched_skills = []
    for cs in candidate_skills:
        vec = skill_map.get(cs)
        if vec is not None:
            vectors.append(vec)
            matched_skills.append(cs)

    if not vectors:
        # Fallback: use title embedding directly if no skill matches
        # Try matching title as a phrase
        title_lower = title.lower() if title else ""
        for skill_name, vec in skill_map.items():
            if skill_name in title_lower or title_lower in skill_name:
                vectors.append(vec)
                matched_skills.append(skill_name)
                if len(vectors) >= 5:
                    break

    if not vectors:
        return None, []

    avg = np.mean(vectors, axis=0)
    norm = np.linalg.norm(avg)
    if norm > 0:
        avg = avg / norm
    return avg, matched_skills


def cosine_sim(a, b):
    """Cosine similarity between two vectors."""
    return float(np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b)))


def main():
    print("=" * 70)
    print("MATCHING QUALITY CHECK")
    print("10 Students x 10 Jobs — pgvector cosine similarity")
    print("=" * 70)

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Load skill embeddings
    print("\nLoading skill embeddings...")
    skill_map = get_skill_embedding_map(conn)
    print(f"  Loaded {len(skill_map)} skill embeddings")

    # Top 10 students by distinct skill count
    cur.execute("""
        SELECT s.id, s.full_name
        FROM students s
        JOIN student_skills ss ON ss.student_id = s.id
        GROUP BY s.id, s.full_name
        ORDER BY count(DISTINCT ss.skill_id) DESC
        LIMIT 10
    """)
    students = cur.fetchall()

    # Pick 10 jobs: 5 Lightcast digital + 5 Arbeitnow digital (for variety)
    cur.execute("""
        (SELECT id, title FROM job_listings
         WHERE source = 'lightcast' AND is_digital = TRUE
         AND legacy_data->>'cfa_skills' IS NOT NULL
         ORDER BY random() LIMIT 5)
        UNION ALL
        (SELECT id, title FROM job_listings
         WHERE source = 'arbeitnow' AND is_digital = TRUE
         ORDER BY random() LIMIT 5)
    """)
    jobs = cur.fetchall()

    # Compute embeddings
    print("\nComputing student embeddings...")
    student_data = []
    for sid, name in students:
        emb, skills = compute_student_embedding(conn, sid, skill_map)
        if emb is not None:
            student_data.append((sid, name, emb, skills))
            print(f"  {name}: {len(skills)} skills matched")

    print("\nComputing job embeddings...")
    job_data = []
    for jid, title in jobs:
        emb, skills = compute_job_embedding(conn, jid, skill_map)
        if emb is not None:
            job_data.append((jid, title[:45], emb, skills))
            print(f"  {title[:50]}: {len(skills)} skills matched")
        else:
            print(f"  {title[:50]}: NO SKILLS MATCHED (skipping)")

    if not student_data or not job_data:
        print("\nInsufficient data for matching!")
        conn.close()
        return

    # Compute similarity matrix
    print(f"\n{'='*70}")
    print(f"SIMILARITY MATRIX ({len(student_data)} students x {len(job_data)} jobs)")
    print(f"{'='*70}\n")

    # Header row
    header = f"{'Student':<22} |"
    for _, title, _, _ in job_data:
        header += f" {title[:12]:>12}"
    print(header)
    print("-" * len(header))

    all_matches = []
    for sid, sname, semb, sskills in student_data:
        row = f"{sname:<22} |"
        for jid, jtitle, jemb, jskills in job_data:
            sim = cosine_sim(semb, jemb)
            all_matches.append({
                "student": sname,
                "job": jtitle,
                "score": sim,
                "student_skills": sskills,
                "job_skills": jskills,
            })
            # Color coding
            if sim >= 0.7:
                marker = f" {sim:>11.3f}*"
            elif sim >= 0.5:
                marker = f" {sim:>12.3f}"
            else:
                marker = f" {sim:>12.3f}"
            row += marker
        print(row)

    # Sort all matches
    all_matches.sort(key=lambda x: -x["score"])

    # Top 3 matches
    print(f"\n{'='*70}")
    print("TOP 3 MATCHES")
    print(f"{'='*70}")
    for m in all_matches[:3]:
        print(f"\n  Score: {m['score']:.3f}")
        print(f"  Student: {m['student']}")
        print(f"  Job: {m['job']}")
        s_set = set(s.lower() for s in m["student_skills"])
        j_set = set(s.lower() for s in m["job_skills"])
        overlap = s_set & j_set
        print(f"  Student skills ({len(m['student_skills'])}): {', '.join(m['student_skills'][:10])}")
        print(f"  Job skills ({len(m['job_skills'])}): {', '.join(m['job_skills'][:10])}")
        if overlap:
            print(f"  OVERLAPPING: {', '.join(overlap)}")
        else:
            print(f"  No exact overlap (similarity is semantic, not keyword)")

    # Bottom 3 matches
    print(f"\n{'='*70}")
    print("BOTTOM 3 MATCHES")
    print(f"{'='*70}")
    for m in all_matches[-3:]:
        print(f"\n  Score: {m['score']:.3f}")
        print(f"  Student: {m['student']}")
        print(f"  Job: {m['job']}")
        print(f"  Student skills: {', '.join(m['student_skills'][:8])}")
        print(f"  Job skills: {', '.join(m['job_skills'][:8])}")

    # Score distribution
    scores = [m["score"] for m in all_matches]
    print(f"\n{'='*70}")
    print("SCORE DISTRIBUTION")
    print(f"{'='*70}")
    print(f"  Min:    {min(scores):.3f}")
    print(f"  Max:    {max(scores):.3f}")
    print(f"  Mean:   {sum(scores)/len(scores):.3f}")
    print(f"  Median: {sorted(scores)[len(scores)//2]:.3f}")
    print(f"  >= 0.7: {sum(1 for s in scores if s >= 0.7)}")
    print(f"  >= 0.5: {sum(1 for s in scores if s >= 0.5)}")
    print(f"  < 0.3:  {sum(1 for s in scores if s < 0.3)}")

    conn.close()
    print(f"\n{'='*70}")
    print("Quality check complete. Review results above.")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()
