"""
Semantic skill search — find related skills using vector embeddings.
Uses the 5,061 skills with 1536-dim embeddings in the local wfd_os database.
"""
import json
import math
import psycopg2
from functools import lru_cache

from wfdos_common.config import ConfigurationError, settings

_conn = None


def _get_conn():
    """Open (or reuse) a connection to the local semantic-search PG instance.

    This function historically hardcoded credentials and a database name in
    source; both now flow through wfdos_common.config (#18) with a safer
    default that fails loudly when PG_PASSWORD is missing rather than
    using the compromised literal.

    TODO(#22): replaced by wfdos_common.db.engine.get_engine() once the
    shared engine factory lands; the per-service connection globals go away.
    """
    global _conn
    if _conn and not _conn.closed:
        return _conn
    if not settings.pg.password:
        raise ConfigurationError(
            "PG_PASSWORD is required for semantic_skills._get_conn(). "
            "Set it in your .env / environment. The previous hardcoded default "
            "was rotated and removed as part of #19."
        )
    _conn = psycopg2.connect(
        host=settings.pg.host,
        user=settings.pg.user,
        password=settings.pg.password,
        port=settings.pg.port,
        dbname=settings.pg.database,
    )
    return _conn


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def _parse_embedding(emb_str: str) -> list[float]:
    """Parse embedding string '[1.23e-002,4.56e-003,...]' into float list."""
    if not emb_str or not emb_str.startswith("["):
        return []
    try:
        return [float(x) for x in emb_str.strip("[]").split(",")]
    except (ValueError, TypeError):
        return []


@lru_cache(maxsize=1)
def _load_all_skills() -> list[dict]:
    """Load all skills with parsed embeddings (cached after first call)."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute("SELECT skill_name, embedding FROM skills WHERE embedding IS NOT NULL")
    rows = cur.fetchall()
    cur.close()

    results = []
    for name, emb_str in rows:
        emb = _parse_embedding(emb_str)
        if emb and len(emb) == 1536:
            results.append({"name": name, "embedding": emb})
    return results


def _get_embedding_for_skill(skill_name: str) -> list[float]:
    """Look up the embedding for a specific skill by name (case-insensitive)."""
    conn = _get_conn()
    cur = conn.cursor()
    cur.execute(
        "SELECT embedding FROM skills WHERE LOWER(skill_name) = LOWER(%s) LIMIT 1",
        (skill_name,),
    )
    row = cur.fetchone()
    cur.close()
    if row and row[0]:
        return _parse_embedding(row[0])
    return []


def _get_embedding_from_openai(text: str) -> list[float]:
    """Generate an embedding for arbitrary text using Azure OpenAI."""
    import requests

    endpoint = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
    key = os.getenv("AZURE_OPENAI_KEY")
    if not endpoint or not key:
        return []

    resp = requests.post(
        f"{endpoint}/openai/deployments/embeddings-te3small/embeddings?api-version=2024-02-01",
        headers={"api-key": key, "Content-Type": "application/json"},
        json={"input": text},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json()["data"][0]["embedding"]


def find_related_skills(
    skill: str,
    limit: int = 15,
) -> dict:
    """
    Find skills semantically related to the input skill.
    First tries to match by name in the database; if not found,
    generates a new embedding via Azure OpenAI.
    Returns ranked list with similarity scores.
    """
    # Get query embedding
    query_emb = _get_embedding_for_skill(skill)
    source = "database"

    if not query_emb:
        # Try generating via OpenAI
        try:
            query_emb = _get_embedding_from_openai(skill)
            source = "openai"
        except Exception:
            # Fall back to substring search
            conn = _get_conn()
            cur = conn.cursor()
            cur.execute(
                "SELECT skill_name FROM skills WHERE LOWER(skill_name) LIKE %s LIMIT %s",
                (f"%{skill.lower()}%", limit),
            )
            matches = [row[0] for row in cur.fetchall()]
            cur.close()
            return {
                "query": skill,
                "method": "substring_fallback",
                "related_skills": [{"skill": m, "similarity": None} for m in matches],
                "total_results": len(matches),
            }

    if not query_emb:
        return {"query": skill, "error": "Could not generate embedding", "related_skills": []}

    # Compute cosine similarity against all skills
    all_skills = _load_all_skills()
    scored = []
    for s in all_skills:
        if s["name"].lower() == skill.lower():
            continue  # skip exact match
        sim = _cosine_similarity(query_emb, s["embedding"])
        scored.append({"skill": s["name"], "similarity": round(sim, 4)})

    scored.sort(key=lambda x: x["similarity"], reverse=True)

    return {
        "query": skill,
        "method": f"cosine_similarity (embedding from {source})",
        "embedding_dimensions": 1536,
        "total_skills_compared": len(all_skills),
        "related_skills": scored[:limit],
    }


def find_skills_for_concept(
    concept: str,
    limit: int = 15,
) -> dict:
    """
    Find skills related to an arbitrary concept (e.g. 'cloud computing',
    'healthcare data', 'entry-level web development').
    Always uses OpenAI to generate the concept embedding.
    """
    try:
        query_emb = _get_embedding_from_openai(concept)
    except Exception as e:
        return {"query": concept, "error": f"Could not generate embedding: {e}", "related_skills": []}

    all_skills = _load_all_skills()
    scored = []
    for s in all_skills:
        sim = _cosine_similarity(query_emb, s["embedding"])
        scored.append({"skill": s["name"], "similarity": round(sim, 4)})

    scored.sort(key=lambda x: x["similarity"], reverse=True)

    return {
        "query": concept,
        "method": "cosine_similarity (concept embedding via OpenAI)",
        "embedding_dimensions": 1536,
        "total_skills_compared": len(all_skills),
        "related_skills": scored[:limit],
    }


if __name__ == "__main__":
    # Quick test
    print("=== Testing semantic skill search ===\n")

    print("Related to 'Python':")
    result = find_related_skills("Python")
    for s in result["related_skills"][:10]:
        print(f"  {s['similarity']:.4f}  {s['skill']}")

    print(f"\nMethod: {result['method']}")
    print(f"Skills compared: {result['total_skills_compared']}")
