"""
College Pipeline Agent -- Map Programs to Skills Taxonomy

Uses pgvector similarity to match college/career program names
against the 5,061 skills in the taxonomy. Populates program_skills
table with the top matching skills per program.

Strategy:
- Generate an embedding for each program name
- Compare against all skill embeddings via cosine similarity
- Store top 10 matching skills per program in program_skills
- Uses Azure OpenAI text-embedding-3-small (same model as skills)
"""
import sys, os, json, psycopg2, time
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts"))
from pgconfig import PG_CONFIG
from dotenv import load_dotenv
import requests

load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"), override=True)

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_KEY = os.getenv("AZURE_OPENAI_KEY")
EMBEDDING_DEPLOYMENT = "embeddings-te3small"
SKILLS_PER_PROGRAM = 10
SIMILARITY_THRESHOLD = 0.35  # Minimum similarity to link


def get_embedding(text):
    """Generate embedding via Azure OpenAI text-embedding-3-small."""
    url = f"{AZURE_OPENAI_ENDPOINT}openai/deployments/{EMBEDDING_DEPLOYMENT}/embeddings?api-version=2024-02-01"
    headers = {"api-key": AZURE_OPENAI_KEY, "Content-Type": "application/json"}
    body = {"input": text}
    r = requests.post(url, headers=headers, json=body, timeout=30)
    r.raise_for_status()
    return np.array(r.json()["data"][0]["embedding"])


def load_all_skill_embeddings(conn):
    """Load all skill embeddings from PostgreSQL."""
    cur = conn.cursor()
    cur.execute("""
        SELECT skill_id, skill_name, embedding_vector::text
        FROM skills WHERE embedding_vector IS NOT NULL
    """)
    skills = []
    for sid, name, vec_str in cur.fetchall():
        vals = [float(x) for x in vec_str.strip("[]").split(",")]
        skills.append((sid, name, np.array(vals)))
    print(f"  Loaded {len(skills)} skill embeddings")
    return skills


def find_matching_skills(program_embedding, all_skills, top_n=SKILLS_PER_PROGRAM):
    """Find top N skills matching a program embedding via cosine similarity."""
    scored = []
    prog_norm = np.linalg.norm(program_embedding)
    if prog_norm == 0:
        return []

    for sid, name, vec in all_skills:
        sim = float(np.dot(program_embedding, vec) / (prog_norm * np.linalg.norm(vec)))
        if sim >= SIMILARITY_THRESHOLD:
            scored.append((sid, name, sim))

    scored.sort(key=lambda x: -x[2])
    return scored[:top_n]


def map_programs_batch(conn, all_skills, source=None, limit=None, use_api=True):
    """
    Map programs to skills. If use_api=False, uses a simple keyword
    matching approach instead of Azure OpenAI embeddings.
    """
    cur = conn.cursor()

    query = "SELECT id, name FROM college_programs"
    params = []
    if source:
        query += " WHERE source = %s"
        params.append(source)
    if limit:
        query += " LIMIT %s"
        params.append(limit)

    cur.execute(query, params)
    programs = cur.fetchall()
    print(f"\n  Mapping {len(programs)} programs to skills...")

    total_linked = 0
    total_programs_mapped = 0
    api_calls = 0

    for i, (prog_id, prog_name) in enumerate(programs):
        if not prog_name or len(prog_name) < 3:
            continue

        if use_api:
            try:
                prog_embedding = get_embedding(prog_name)
                api_calls += 1
            except Exception as e:
                print(f"  API error for '{prog_name[:40]}': {e}")
                # Fallback to keyword matching
                prog_embedding = None
        else:
            prog_embedding = None

        if prog_embedding is not None:
            matches = find_matching_skills(prog_embedding, all_skills)
        else:
            # Keyword fallback: find skills whose names appear in program name
            prog_lower = prog_name.lower()
            matches = []
            for sid, sname, vec in all_skills:
                sname_lower = sname.lower()
                if (sname_lower in prog_lower or
                    prog_lower in sname_lower or
                    any(w in prog_lower for w in sname_lower.split() if len(w) > 3)):
                    matches.append((sid, sname, 0.5))
            matches = matches[:SKILLS_PER_PROGRAM]

        if matches:
            for sid, sname, sim in matches:
                try:
                    cur.execute("""
                        INSERT INTO program_skills (program_id, skill_id, source)
                        VALUES (%s, %s, %s)
                    """, (prog_id, sid, "embedding_match" if prog_embedding is not None else "keyword_match"))
                    total_linked += 1
                except:
                    conn.rollback()
                    continue
            total_programs_mapped += 1

        if (i + 1) % 50 == 0:
            conn.commit()
            print(f"  [{i+1}/{len(programs)}] Mapped: {total_programs_mapped}, "
                  f"Skills linked: {total_linked}, API calls: {api_calls}")

        # Rate limit for API calls
        if use_api and api_calls % 50 == 0 and api_calls > 0:
            time.sleep(2)

    conn.commit()
    return total_programs_mapped, total_linked, api_calls


def main():
    print("=" * 60)
    print("College Pipeline Agent -- Map Programs to Skills")
    print("=" * 60)

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Clear previous mappings
    cur.execute("DELETE FROM program_skills")
    conn.commit()

    # Load skill embeddings
    print("\nLoading skill embeddings...")
    all_skills = load_all_skill_embeddings(conn)

    # Check if Azure OpenAI is available
    use_api = bool(AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY)
    if use_api:
        print("Azure OpenAI available -- using embedding-based matching")
        # Test with one call
        try:
            test_emb = get_embedding("Computer Science")
            print(f"  Test embedding OK (dim={len(test_emb)})")
        except Exception as e:
            print(f"  Azure OpenAI test failed: {e}")
            print("  Falling back to keyword matching")
            use_api = False
    else:
        print("Azure OpenAI not available -- using keyword matching")

    # Map CFA college programs first (729, higher quality)
    print("\n--- CFA College Programs (729) ---")
    mapped_cfa, linked_cfa, api_cfa = map_programs_batch(
        conn, all_skills, source="cfa_college", use_api=use_api
    )

    # Map Career Bridge programs (3,940)
    print("\n--- Career Bridge Programs (3,940) ---")
    mapped_cb, linked_cb, api_cb = map_programs_batch(
        conn, all_skills, source="career_bridge", use_api=use_api
    )

    # Summary
    print(f"\n{'='*60}")
    print("MAPPING COMPLETE")
    print(f"{'='*60}")
    print(f"  CFA College: {mapped_cfa} programs -> {linked_cfa} skill links")
    print(f"  Career Bridge: {mapped_cb} programs -> {linked_cb} skill links")
    print(f"  Total: {mapped_cfa + mapped_cb} programs -> {linked_cfa + linked_cb} skill links")
    print(f"  API calls: {api_cfa + api_cb}")

    # Show sample mappings
    print(f"\nSample program-to-skill mappings:")
    cur.execute("""
        SELECT cp.name, sk.skill_name, ps.source
        FROM program_skills ps
        JOIN college_programs cp ON cp.id = ps.program_id
        JOIN skills sk ON sk.skill_id = ps.skill_id
        WHERE cp.source = 'cfa_college'
        ORDER BY cp.name, sk.skill_name
        LIMIT 30
    """)
    current_prog = None
    for prog_name, skill_name, src in cur.fetchall():
        if prog_name != current_prog:
            print(f"\n  {prog_name}:")
            current_prog = prog_name
        print(f"    - {skill_name} ({src})")

    conn.close()


if __name__ == "__main__":
    main()
