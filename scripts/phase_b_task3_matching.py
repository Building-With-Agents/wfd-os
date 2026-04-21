"""Phase B Task 3 — run tenant-scoped matching for 9 WSB Cohort 1 apprentices
against the 40-job WSB El Paso pool; persist to the `cohort_matches` table
(migration 016).

Adapts agents/job_board/data_source.py::PostgresDataSource.student_matches()
with tenancy filtering inside the query (Ritu's call: option (a),
post-filtering after a global top-N is unreliable).

Shape of each match row matches student_matches() output:
    {job_id, title, company, city, state, is_remote, cosine,
     existing_application}

Persistence: cohort_matches table. Upserts by (student_id, job_id, tenant_id)
— safe to re-run. Writes:
    student_id, job_id, tenant_id (WSB UUID),
    cosine_similarity, match_rank (1..TOP_N, ordered by descending cosine),
    generated_at=NOW(), model_name='text-embedding-3-small',
    template_version='student_v2/job_v1'.

TECH DEBT NOTE (multi-tenancy hardening):
  student_matches() in agents/job_board/data_source.py should become
  tenant-aware. Today it queries `v_jobs_active` which does not expose
  `tenant_id`, and the JOIN to embeddings has no tenant filter. The Phase B
  adapted query below JOINs directly to `jobs_enriched` (not the view) so
  it can filter on `tenant_id`. Phase B duplicates this logic rather than
  refactor existing code.
"""
from __future__ import annotations

import sys
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras


SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
from pgconfig import PG_CONFIG  # noqa: E402


WORKTREE = SCRIPTS_DIR.parent
WSB_CODE = "WSB"
TOP_N = 10  # matches the default in student_matches()

# Provenance tags recorded on every cohort_matches row so future analyses
# can tell which model + templates produced a given match.
EMBEDDING_MODEL = "text-embedding-3-small"
STUDENT_TEMPLATE = "student_v2"
JOB_TEMPLATE = "job_v1"
COMPOSITE_TEMPLATE = f"{STUDENT_TEMPLATE}/{JOB_TEMPLATE}"

# WSB-scoped adaptation of student_matches():
#   - JOINs to jobs_enriched directly (v_jobs_active doesn't expose tenant_id)
#   - Filters on j.tenant_id = WSB so only WSB jobs are in the cosine pool
#   - Bound params: (student_uuid, student_uuid, wsb_tenant_uuid, top_n)
MATCH_SQL = """
    SELECT
      j.id AS job_id,
      j.title,
      j.company,
      j.city,
      j.state,
      j.is_remote,
      1 - (e_j.embedding <=> e_s.embedding) AS cosine,
      EXISTS (
        SELECT 1 FROM applications a
        WHERE a.student_id = %s::uuid AND a.job_id = j.id
      ) AS existing_application
    FROM embeddings e_j
    JOIN jobs_enriched j
      ON j.id::text = e_j.entity_id
     AND j.tenant_id = %s::uuid         -- tenant scope on jobs
    CROSS JOIN (
      SELECT e.embedding
      FROM embeddings e
      JOIN students s ON s.id::text = e.entity_id
      WHERE e.entity_type = 'student'
        AND e.entity_id = %s
        AND s.tenant_id = %s::uuid       -- tenant scope on student too
    ) e_s
    WHERE e_j.entity_type = 'jobs_enriched'
    ORDER BY e_j.embedding <=> e_s.embedding
    LIMIT %s
"""


def lookup_tenant_uuid(conn, code: str) -> str:
    cur = conn.cursor()
    cur.execute("SELECT id FROM tenants WHERE code = %s", (code,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"tenant code {code!r} not seeded")
    return str(row[0])


def fetch_wsb_apprentices(conn, wsb_uuid: str) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT id::text AS id, full_name, cohort_id
        FROM students
        WHERE tenant_id = %s::uuid AND cohort_id = 'cohort-1-feb-2026'
        ORDER BY full_name
        """,
        (wsb_uuid,),
    )
    return [dict(r) for r in cur.fetchall()]


def jsonable(v):
    if isinstance(v, Decimal):
        return float(v)
    return v


def dictify(cur, rows):
    cols = [d[0] for d in cur.description]
    return [{c: jsonable(val) for c, val in zip(cols, r)} for r in rows]


def run() -> int:
    print("=" * 70)
    print(f"Phase B Task 3 — Matching (top-{TOP_N} jobs per WSB apprentice)")
    print("=" * 70)

    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False

    wsb = lookup_tenant_uuid(conn, WSB_CODE)
    cfa = lookup_tenant_uuid(conn, "CFA")
    print(f"WSB tenant_id: {wsb}")
    print(f"pool job count (WSB only): ", end="")
    cur = conn.cursor()
    cur.execute(
        """
        SELECT COUNT(*) FROM embeddings e
        JOIN jobs_enriched j ON j.id::text = e.entity_id
        WHERE e.entity_type = 'jobs_enriched' AND j.tenant_id = %s::uuid
        """,
        (wsb,),
    )
    wsb_job_emb = cur.fetchone()[0]
    print(wsb_job_emb)

    apprentices = fetch_wsb_apprentices(conn, wsb)
    print(f"WSB apprentices: {len(apprentices)}")
    print()

    if not apprentices:
        print("No Cohort 1 apprentices found. Aborting.")
        conn.close()
        return 3
    if wsb_job_emb == 0:
        print("No WSB job embeddings. Run Task 2 first.")
        conn.close()
        return 4

    # Transaction boundary: compute all matches for all apprentices, then
    # persist in one commit at the end. Upsert so re-runs are idempotent.
    upsert_cur = conn.cursor()

    # Clear only THIS tenant's prior matches so rank recompute is clean.
    # (UPSERT would work too but wouldn't remove rows that fell out of
    # top-N between runs — DELETE-then-INSERT is simpler.)
    upsert_cur.execute(
        "DELETE FROM cohort_matches WHERE tenant_id = %s::uuid",
        (wsb,),
    )
    deleted_prior = upsert_cur.rowcount

    per_apprentice: list[dict] = []
    total_matches = 0
    match_cur = conn.cursor()
    for a in apprentices:
        match_cur.execute(MATCH_SQL, (a["id"], wsb, a["id"], wsb, TOP_N))
        rows = dictify(match_cur, match_cur.fetchall())
        total_matches += len(rows)
        top1 = rows[0]["cosine"] if rows else None
        top5 = [r["cosine"] for r in rows[:5]] if rows else []
        per_apprentice.append({
            "student_id": a["id"],
            "full_name": a["full_name"],
            "cohort_id": a["cohort_id"],
            "matches": rows,
            "top1_cosine": top1,
            "top5_range": (min(top5), max(top5)) if top5 else None,
        })
        top1_display = f"{top1:.4f}" if top1 is not None else "—"
        top5_display = (
            f"[{top5[0]:.4f} .. {top5[-1]:.4f}]"
            if len(top5) >= 2
            else (f"[{top5[0]:.4f}]" if top5 else "—")
        )
        print(f"  {a['full_name']:<30} matches={len(rows):<3} top1={top1_display}  top5 range={top5_display}")

        # Persist this apprentice's top-N to cohort_matches.
        # Rows come back ordered by descending cosine so match_rank is 1..N.
        for rank, m in enumerate(rows, start=1):
            upsert_cur.execute(
                """
                INSERT INTO cohort_matches (
                    tenant_id, student_id, job_id,
                    cosine_similarity, match_rank,
                    model_name, template_version
                ) VALUES (%s::uuid, %s::uuid, %s, %s, %s, %s, %s)
                """,
                (
                    wsb,
                    a["id"],
                    m["job_id"],
                    float(m["cosine"]),
                    rank,
                    EMBEDDING_MODEL,
                    COMPOSITE_TEMPLATE,
                ),
            )

    conn.commit()
    print()
    print(f"cohort_matches: DELETE prior WSB rows={deleted_prior}, INSERT new rows={total_matches}")

    conn.close()

    # Diversity signal: are most apprentices matching to similar jobs?
    job_id_counts: dict[int, int] = {}
    top3_job_id_counts: dict[int, int] = {}
    for entry in per_apprentice:
        for i, m in enumerate(entry["matches"]):
            jid = m["job_id"]
            job_id_counts[jid] = job_id_counts.get(jid, 0) + 1
            if i < 3:
                top3_job_id_counts[jid] = top3_job_id_counts.get(jid, 0) + 1

    # Hot jobs = those appearing in many apprentices' top-10s
    hot_jobs = sorted(job_id_counts.items(), key=lambda kv: -kv[1])[:10]
    hot_top3 = sorted(top3_job_id_counts.items(), key=lambda kv: -kv[1])[:10]

    # Attach job titles for readability
    c = psycopg2.connect(**PG_CONFIG)
    cur = c.cursor()
    ids_for_lookup = list({jid for jid, _ in hot_jobs} | {jid for jid, _ in hot_top3})
    cur.execute(
        "SELECT id, title, company FROM jobs_enriched WHERE id = ANY(%s) AND tenant_id = %s::uuid",
        (ids_for_lookup, wsb),
    )
    title_map = {r[0]: (r[1], r[2]) for r in cur.fetchall()}
    c.close()

    print()
    print("Most-matched jobs (appearing in many apprentices' top-10):")
    for jid, cnt in hot_jobs[:8]:
        title, company = title_map.get(jid, ("?", "?"))
        safe_title = (title or "").encode("ascii", "replace").decode("ascii")[:55]
        print(f"  #{jid:<4} x{cnt:<2}  {safe_title} @ {company[:28]}")
    print()
    print("Most-matched jobs in top-3 only (higher signal of convergence):")
    for jid, cnt in hot_top3[:8]:
        title, company = title_map.get(jid, ("?", "?"))
        safe_title = (title or "").encode("ascii", "replace").decode("ascii")[:55]
        print(f"  #{jid:<4} x{cnt:<2}  {safe_title} @ {company[:28]}")

    # DB verification — cohort_matches is authoritative. No JSON digest.
    vc = psycopg2.connect(**PG_CONFIG)
    vcur = vc.cursor()
    vcur.execute(
        "SELECT COUNT(*) FROM cohort_matches WHERE tenant_id = %s::uuid",
        (wsb,),
    )
    wsb_rows = vcur.fetchone()[0]
    vcur.execute(
        "SELECT COUNT(*) FROM cohort_matches WHERE tenant_id = %s::uuid",
        (cfa,),
    )
    cfa_rows = vcur.fetchone()[0]

    # Rank integrity per apprentice: ranks should be 1..TOP_N, no gaps/dupes.
    vcur.execute(
        """
        SELECT student_id, COUNT(*) AS n,
               MIN(match_rank) AS min_rank,
               MAX(match_rank) AS max_rank,
               COUNT(DISTINCT match_rank) AS distinct_ranks
        FROM cohort_matches
        WHERE tenant_id = %s::uuid
        GROUP BY student_id
        """,
        (wsb,),
    )
    rank_rows = vcur.fetchall()
    rank_ok = all(
        n == distinct == TOP_N and min_r == 1 and max_r == TOP_N
        for _, n, min_r, max_r, distinct in rank_rows
    )

    # Cross-tenant leak check: every persisted match should have student +
    # job both in the SAME tenant as the match row.
    vcur.execute(
        """
        SELECT COUNT(*) FROM cohort_matches cm
        JOIN students s      ON s.id = cm.student_id
        JOIN jobs_enriched j ON j.id = cm.job_id
        WHERE cm.tenant_id = %s::uuid
          AND (s.tenant_id != cm.tenant_id OR j.tenant_id != cm.tenant_id)
        """,
        (wsb,),
    )
    cross_tenant = vcur.fetchone()[0]
    vc.close()

    print()
    print("=" * 70)
    print(f"cohort_matches counts:  WSB={wsb_rows}  CFA={cfa_rows}")
    expected_wsb = len(apprentices) * TOP_N
    print(f"  WSB expected: {expected_wsb}  actual: {wsb_rows}  "
          f"{'OK' if wsb_rows == expected_wsb else 'MISMATCH'}")
    print(f"  CFA expected: 0  actual: {cfa_rows}  "
          f"{'OK' if cfa_rows == 0 else 'MISMATCH'}")
    print(f"rank integrity (1..{TOP_N}, no gaps/dupes): "
          f"{'OK' if rank_ok else 'FAIL'}")
    for sid, n, mn, mx, dc in rank_rows:
        tag = "OK" if (n == dc == TOP_N and mn == 1 and mx == TOP_N) else "FAIL"
        print(f"  {str(sid)[:8]}...  n={n}  rank[{mn}..{mx}]  distinct={dc}  {tag}")
    print(f"cross-tenant leak rows (should be 0): {cross_tenant}  "
          f"{'OK' if cross_tenant == 0 else 'FAIL'}")

    ok = (
        wsb_rows == expected_wsb
        and cfa_rows == 0
        and rank_ok
        and cross_tenant == 0
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(run())
