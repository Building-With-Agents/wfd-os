"""Phase B Task 1 — generate embeddings for the 9 WSB Cohort 1 apprentices.

Reuses the primitives in scripts/backfill_embeddings.py (render_student,
embed_text, upsert_embedding, content_hash, STUDENT_TEMPLATE_VERSION,
MODEL_NAME) without modifying that module. We supply our own pool SQL
scoped to `tenant_id = WSB UUID` so CFA's existing 146 student embeddings
are untouched.

Embedding model: text-embedding-3-small via Azure OpenAI deployment
`embeddings-te3small` (1536 dims, matches the existing `embeddings` table).
"""
from __future__ import annotations

import sys
from pathlib import Path

import psycopg2
import psycopg2.extras


SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
import backfill_embeddings as bf  # noqa: E402 — existing module, unchanged

from pgconfig import PG_CONFIG  # noqa: E402


WSB_CODE = "WSB"


# Same columns as bf.STUDENT_SQL, scoped to WSB tenant.
WSB_STUDENT_SQL = """
SELECT s.id::text AS id, s.full_name, s.institution, s.degree,
       s.field_of_study, s.graduation_year, s.city, s.state,
       s.legacy_data->>'career_objective' AS career_objective,
       array_agg(DISTINCT sk.skill_name ORDER BY sk.skill_name) AS skills
FROM students s
JOIN student_skills ss ON ss.student_id = s.id
JOIN skills sk ON sk.skill_id = ss.skill_id
WHERE s.tenant_id = %s
  AND s.institution IS NOT NULL
  AND s.resume_parsed = TRUE
GROUP BY s.id
ORDER BY s.id
"""


def fetch_wsb_apprentices(conn, wsb_uuid: str) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(WSB_STUDENT_SQL, (wsb_uuid,))
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    return rows


def lookup_tenant_uuid(conn, code: str) -> str:
    cur = conn.cursor()
    cur.execute("SELECT id FROM tenants WHERE code = %s", (code,))
    row = cur.fetchone()
    if not row:
        raise RuntimeError(f"tenant code {code!r} not seeded")
    return str(row[0])


def main() -> int:
    print("=" * 70)
    print("Phase B Task 1 — Embeddings for WSB Cohort 1 apprentices")
    print("=" * 70)

    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    wsb = lookup_tenant_uuid(conn, WSB_CODE)
    cfa = lookup_tenant_uuid(conn, "CFA")
    print(f"WSB tenant_id: {wsb}")
    print(f"template:      {bf.STUDENT_TEMPLATE_VERSION}")
    print(f"model:         {bf.MODEL_NAME}")
    print(f"deployment:    {bf.DEPLOYMENT}")
    print()

    # Baseline: existing embeddings counts so we can verify no CFA drift.
    cur.execute(
        """
        SELECT COUNT(*) FROM embeddings e
        JOIN students s ON s.id::text = e.entity_id
        WHERE e.entity_type = 'student' AND s.tenant_id = %s
        """,
        (cfa,),
    )
    cfa_before = cur.fetchone()[0]
    cur.execute(
        """
        SELECT COUNT(*) FROM embeddings e
        JOIN students s ON s.id::text = e.entity_id
        WHERE e.entity_type = 'student' AND s.tenant_id = %s
        """,
        (wsb,),
    )
    wsb_before = cur.fetchone()[0]
    print(f"Student embeddings before: CFA={cfa_before}  WSB={wsb_before}")
    print()

    rows = fetch_wsb_apprentices(conn, wsb)
    print(f"WSB apprentices in pool: {len(rows)}")
    for r in rows:
        print(f"  - {r['full_name']}  inst={r['institution']}  skills={len(r['skills'] or [])}")
    print()

    if not rows:
        print("No WSB apprentices matched the Tier A pool filter. Aborting.")
        conn.close()
        return 3

    created = 0
    updated = 0
    skipped = 0
    failed = []

    for row in rows:
        name = row.get("full_name") or row["id"]
        try:
            text, fields_present = bf.render_student(row)
            if not text.strip():
                print(f"  SKIP {name}: empty rendered template")
                skipped += 1
                continue

            ch = bf.content_hash(text, bf.STUDENT_TEMPLATE_VERSION)
            existing = bf.existing_hash(cur, "student", row["id"])
            if existing and existing == (ch, bf.STUDENT_TEMPLATE_VERSION):
                print(f"  SKIP {name}: unchanged (content_hash match)")
                skipped += 1
                continue

            # Embed
            vec = bf.embed_text(text)
            # Upsert — backfill_embeddings.upsert_embedding uses
            # ON CONFLICT (entity_type, entity_id, model_name) DO UPDATE.
            is_new = existing is None
            bf.upsert_embedding(
                cur,
                entity_type="student",
                entity_id=row["id"],
                vec=vec,
                chash=ch,
                template_version=bf.STUDENT_TEMPLATE_VERSION,
                source_fields=fields_present,
            )
            conn.commit()
            if is_new:
                created += 1
                tag = "NEW"
            else:
                updated += 1
                tag = "UPDATE"
            print(f"  {tag:<6} {name}  (fields: {len(fields_present)})")
        except Exception as e:
            conn.rollback()
            failed.append({"name": name, "id": row.get("id"), "error": str(e)[:200]})
            print(f"  FAIL   {name}: {str(e)[:200]}")

    # Verification
    cur.execute(
        """
        SELECT COUNT(*) FROM embeddings e
        JOIN students s ON s.id::text = e.entity_id
        WHERE e.entity_type = 'student' AND s.tenant_id = %s
        """,
        (cfa,),
    )
    cfa_after = cur.fetchone()[0]
    cur.execute(
        """
        SELECT COUNT(*) FROM embeddings e
        JOIN students s ON s.id::text = e.entity_id
        WHERE e.entity_type = 'student' AND s.tenant_id = %s
        """,
        (wsb,),
    )
    wsb_after = cur.fetchone()[0]

    print()
    print("=" * 70)
    print(f"Summary: NEW={created}  UPDATE={updated}  SKIP={skipped}  FAIL={len(failed)}")
    print(f"Student embeddings after:  CFA={cfa_after}  WSB={wsb_after}")
    cfa_ok = cfa_after == cfa_before
    wsb_ok = wsb_after == len(rows)  # should be exactly 9
    print(f"  CFA drift: {'NONE' if cfa_ok else 'CHANGED'} (expected {cfa_before}, got {cfa_after})")
    print(f"  WSB count: {'OK' if wsb_ok else 'MISMATCH'} (expected {len(rows)}, got {wsb_after})")

    if failed:
        print()
        print("Failures:")
        for f in failed:
            print(f"  - {f['name']}: {f['error']}")

    conn.close()
    return 0 if (not failed and cfa_ok and wsb_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
