"""Phase B Task 2 — generate embeddings for the 40 WSB El Paso jobs.

Reuses the primitives in scripts/backfill_embeddings.py (render_job,
extract_job_description, embed_text, upsert_embedding, content_hash,
existing_hash, JOB_TEMPLATE_VERSION, MODEL_NAME) without modifying that
module. We supply our own pool SQL scoped to `tenant_id = WSB UUID` so
CFA's existing 103 job embeddings are untouched.

Embedding model: text-embedding-3-small via Azure OpenAI deployment
`embeddings-te3small` (1536 dims). Job descriptions are LLM-cleaned via
`chat-gpt41mini` before rendering; falls back to raw truncation if the
extraction call fails.

Tenancy: embeddings table has no tenant_id column. We scope via JOIN
through `jobs_enriched.tenant_id` (per Ritu's guidance, reinforced after
Task 1).
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import psycopg2
import psycopg2.extras


SCRIPTS_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS_DIR))
import backfill_embeddings as bf  # noqa: E402 — existing module, unchanged

from pgconfig import PG_CONFIG  # noqa: E402


WSB_CODE = "WSB"


# Same columns as bf.JOB_SQL, scoped to WSB tenant.
WSB_JOB_SQL = """
SELECT id::text AS id, title, company, location, city, state,
       seniority, employment_type, is_remote, skills_required,
       job_description
FROM jobs_enriched
WHERE tenant_id = %s
ORDER BY id
"""


def fetch_wsb_jobs(conn, wsb_uuid: str) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(WSB_JOB_SQL, (wsb_uuid,))
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


def count_job_embeddings_for_tenant(cur, tenant_uuid: str) -> int:
    # Tenancy via JOIN through jobs_enriched — embeddings table has no tenant_id.
    cur.execute(
        """
        SELECT COUNT(*) FROM embeddings e
        JOIN jobs_enriched j ON j.id::text = e.entity_id
        WHERE e.entity_type = 'jobs_enriched' AND j.tenant_id = %s
        """,
        (tenant_uuid,),
    )
    return cur.fetchone()[0]


def main() -> int:
    print("=" * 70)
    print("Phase B Task 2 — Embeddings for 40 WSB El Paso jobs")
    print("=" * 70)

    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    wsb = lookup_tenant_uuid(conn, WSB_CODE)
    cfa = lookup_tenant_uuid(conn, "CFA")
    print(f"WSB tenant_id: {wsb}")
    print(f"template:      {bf.JOB_TEMPLATE_VERSION}")
    print(f"model:         {bf.MODEL_NAME}")
    print(f"embed deploy:  {bf.DEPLOYMENT}")
    print(f"chat  deploy:  {bf.CHAT_DEPLOYMENT}")
    print()

    cfa_before = count_job_embeddings_for_tenant(cur, cfa)
    wsb_before = count_job_embeddings_for_tenant(cur, wsb)
    print(f"Job embeddings before: CFA={cfa_before}  WSB={wsb_before}")
    print()

    rows = fetch_wsb_jobs(conn, wsb)
    print(f"WSB jobs in pool: {len(rows)}")
    if not rows:
        print("No WSB jobs. Aborting.")
        conn.close()
        return 3

    new_count = 0
    updated_count = 0
    skipped_count = 0
    extraction_fallback = 0
    failed: list[dict] = []

    for row in rows:
        entity_id = row["id"]
        title = row.get("title") or f"(job {entity_id})"
        try:
            # --- Step 1: prepare job_description (LLM clean or raw truncate) ---
            raw_desc = row.get("job_description")
            desc_marker: str | None = None
            if raw_desc and str(raw_desc).strip():
                extracted, fail_reason = bf.extract_job_description(raw_desc)
                if extracted is not None:
                    row["job_description"] = extracted
                    desc_marker = "job_description_extracted"
                else:
                    truncated = str(raw_desc).strip()
                    if len(truncated) > bf.JOB_DESC_MAX_CHARS:
                        truncated = truncated[: bf.JOB_DESC_MAX_CHARS].rstrip() + "..."
                    row["job_description"] = truncated
                    desc_marker = "job_description_raw"
                    extraction_fallback += 1
                    print(f"    (extraction fallback for #{entity_id}: {fail_reason})")

            # --- Step 2: render template ---
            text, present = bf.render_job(row)
            if desc_marker is not None:
                present.append(desc_marker)
            if not text.strip():
                failed.append({"id": entity_id, "title": title, "error": "empty rendered text"})
                print(f"  FAIL   #{entity_id:<4} {title[:55]}: empty rendered text")
                continue

            # --- Step 3: check hash for idempotency ---
            chash = bf.content_hash(text, bf.JOB_TEMPLATE_VERSION)
            existing = bf.existing_hash(cur, "jobs_enriched", entity_id)
            if existing and existing == (chash, bf.JOB_TEMPLATE_VERSION):
                skipped_count += 1
                print(f"  SKIP   #{entity_id:<4} {title[:55]}: unchanged")
                continue

            # --- Step 4: embed + upsert ---
            is_new = existing is None
            vec = bf.embed_text(text)
            bf.upsert_embedding(
                cur,
                entity_type="jobs_enriched",
                entity_id=entity_id,
                vec=vec,
                chash=chash,
                template_version=bf.JOB_TEMPLATE_VERSION,
                source_fields=present,
            )
            conn.commit()
            if is_new:
                new_count += 1
                tag = "NEW"
            else:
                updated_count += 1
                tag = "UPDATE"
            # ASCII-safe print — job titles can contain emojis.
            safe_title = (title or "").encode("ascii", "replace").decode("ascii")[:55]
            print(f"  {tag:<6} #{entity_id:<4} {safe_title}  (fields: {len(present)})")

            time.sleep(bf.RATE_SLEEP_S)
        except Exception as e:
            conn.rollback()
            failed.append({"id": entity_id, "title": title, "error": str(e)[:200]})
            print(f"  FAIL   #{entity_id}: {str(e)[:200]}")

    # --- Verification ---
    cfa_after = count_job_embeddings_for_tenant(cur, cfa)
    wsb_after = count_job_embeddings_for_tenant(cur, wsb)

    print()
    print("=" * 70)
    print(f"Summary: NEW={new_count}  UPDATE={updated_count}  SKIP={skipped_count}  "
          f"FAIL={len(failed)}  extraction_fallback={extraction_fallback}")
    print(f"Job embeddings after:  CFA={cfa_after}  WSB={wsb_after}")
    cfa_ok = cfa_after == cfa_before
    wsb_ok = wsb_after == len(rows)
    print(f"  CFA drift: {'NONE' if cfa_ok else 'CHANGED'} (expected {cfa_before}, got {cfa_after})")
    print(f"  WSB count: {'OK' if wsb_ok else 'MISMATCH'} (expected {len(rows)}, got {wsb_after})")

    if failed:
        print()
        print("Failures:")
        for f in failed:
            print(f"  - #{f['id']} {f['title'][:50]}: {f['error']}")

    conn.close()
    return 0 if (not failed and cfa_ok and wsb_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
