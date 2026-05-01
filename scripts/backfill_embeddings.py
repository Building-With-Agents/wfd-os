"""
Phase 2D — embeddings backfill (students + jobs).

Populates the `embeddings` table with 1536-dim vectors from
Azure OpenAI's `embeddings-te3small` deployment so the existing
job->student cosine query in agents/job_board/data_source.py
lights up.

Pools (agreed with Ritu on 2026-04-18):
  students  — Tier A only: institution NOT NULL AND resume_parsed=TRUE
              AND has >=1 skill. ~146 rows.
  jobs      — every row in jobs_enriched (103 rows). Forces a re-embed
              of the legacy 29 with the new template so the whole
              corpus is homogeneous.

Templates (versioned — stored in text_template_version):
  student_v1, job_v1 — see render_student / render_job below.

CLI:
  python scripts/backfill_embeddings.py --entity {students,jobs,both}
                                        [--limit N]
                                        [--force]

Idempotency: skips rows where (entity_type, entity_id, model_name)
already exists with a matching content_hash and template_version,
unless --force is passed.

Rate limiting: 10 rps (0.1s gap between API calls). Well under
Azure's typical limit; adjust RATE_SLEEP_S if needed.

Failure handling: per-row exceptions are logged and the run
continues. A summary + failure list prints at the end.

Does NOT modify any other tables. Does NOT touch existing rows'
created_at (ON CONFLICT DO UPDATE preserves it). Does NOT re-run
matching.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Any

import psycopg2
import psycopg2.extras
import requests
from dotenv import load_dotenv
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from pgconfig import PG_CONFIG  # noqa: E402

# .env lives at the wfd-os project root, not in worktree subfolders.
load_dotenv("C:/Users/ritub/Projects/wfd-os/.env", override=True)

AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "").rstrip("/")
AZURE_KEY = os.getenv("AZURE_OPENAI_KEY", "")
DEPLOYMENT = "embeddings-te3small"
CHAT_DEPLOYMENT = "chat-gpt41mini"  # gpt-4.1-mini — cheap extraction model
API_VERSION = "2024-02-01"
MODEL_NAME = "text-embedding-3-small"
EMBED_DIM = 1536
RATE_SLEEP_S = 0.1  # 10 requests/sec cap

STUDENT_TEMPLATE_VERSION = "student_v2"
JOB_TEMPLATE_VERSION = "job_v1"

JOB_DESC_MAX_CHARS = 1000
JOB_EXTRACT_MAX_CHARS = 800
JOB_EXTRACT_MIN_CHARS = 50

EXTRACTION_PROMPT = (
    "You are extracting the substantive content from a job posting for "
    "semantic matching purposes. Given the raw job description below, "
    "return only the content that describes what the person will actually "
    "do and what skills/qualifications are required. Exclude company "
    "mission statements, 'about us' language, recruiting boilerplate, "
    "application instructions, EEO statements, and generic marketing. "
    "Return the cleaned content as prose, no headers or bullets. "
    "Maximum 800 characters.\n\n"
    "Raw job description:\n{job_description}"
)

REFUSAL_PREFIXES = (
    "i cannot",
    "i can't",
    "i'm sorry",
    "i am sorry",
    "sorry, i",
    "i'm unable",
    "i am unable",
    "as an ai",
)


# ---------------------------------------------------------------------------
# Template rendering — null-safe line/phrase omission
# ---------------------------------------------------------------------------

def render_student(row: dict) -> tuple[str, list[str]]:
    """Render a student row into the student_v2 text template.

    Returns (rendered_text, source_fields_present). Phrases with all
    their inputs null are dropped; phrases with some-nulls get a
    best-effort partial render.

    Note: v2 drops the `"Workforce development candidate."` prefix v1
    used. v1 validation showed that prefix was biasing student→job
    matching toward workforce/analytics roles regardless of the
    student's actual skill set. v2 starts with the education clause
    directly, mirroring job_v1's content-first opener.
    """
    parts: list[str] = []
    present: list[str] = []

    # "<field_of_study> background at <institution>, <degree> expected <graduation_year>."
    fos = row.get("field_of_study")
    inst = row.get("institution")
    deg = row.get("degree")
    gy = row.get("graduation_year")
    if any([fos, inst, deg, gy]):
        seg = []
        if fos and inst:
            seg.append(f"{fos} background at {inst}")
            present.extend(["field_of_study", "institution"])
        elif fos:
            seg.append(f"{fos} background")
            present.append("field_of_study")
        elif inst:
            seg.append(f"Studied at {inst}")
            present.append("institution")
        if deg and gy:
            seg.append(f"{deg} expected {gy}")
            present.extend(["degree", "graduation_year"])
        elif deg:
            seg.append(f"{deg}")
            present.append("degree")
        elif gy:
            seg.append(f"expected {gy}")
            present.append("graduation_year")
        if seg:
            parts.append(", ".join(seg) + ".")

    # "Located in <city>, <state>."
    city = row.get("city")
    state = row.get("state")
    if city and state:
        parts.append(f"Located in {city}, {state}.")
        present.extend(["city", "state"])
    elif city:
        parts.append(f"Located in {city}.")
        present.append("city")
    elif state:
        parts.append(f"Located in {state}.")
        present.append("state")

    # "Technical skills: <skills>."
    skills = row.get("skills") or []
    if skills:
        parts.append(f"Technical skills: {', '.join(skills)}.")
        present.append("skills")

    # "Career objective: <career_objective>."
    co = row.get("career_objective")
    if co and isinstance(co, str) and co.strip():
        parts.append(f"Career objective: {co.strip()}.")
        present.append("career_objective")

    return " ".join(parts), present


def _humanize(s: str | None) -> str | None:
    if s is None:
        return None
    return s.replace("_", " ").strip()


def extract_job_description(raw: str) -> tuple[str | None, str | None]:
    """LLM-clean a raw job_description for matching purposes.

    Returns (cleaned_text, None) on success, or (None, failure_reason)
    on failure. Caller should fall back to the raw truncated prose.
    """
    if not raw or not raw.strip():
        return None, "empty input"
    try:
        url = (
            f"{AZURE_ENDPOINT}/openai/deployments/{CHAT_DEPLOYMENT}"
            f"/chat/completions?api-version={API_VERSION}"
        )
        prompt = EXTRACTION_PROMPT.format(job_description=raw)
        resp = requests.post(
            url,
            headers={"api-key": AZURE_KEY, "Content-Type": "application/json"},
            json={
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.0,
                "max_tokens": 400,  # ~800 chars is well under 400 tokens
            },
            timeout=30,
        )
        resp.raise_for_status()
        content = resp.json()["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return None, f"api error: {type(e).__name__}: {e}"

    if not content:
        return None, "empty response"
    if len(content) < JOB_EXTRACT_MIN_CHARS:
        return None, f"too short ({len(content)} chars)"
    low = content.lower().lstrip("\"'*- ")
    if any(low.startswith(p) for p in REFUSAL_PREFIXES):
        return None, "refusal pattern"

    # Trim to the 800-char cap even if the model exceeded it.
    if len(content) > JOB_EXTRACT_MAX_CHARS:
        content = content[:JOB_EXTRACT_MAX_CHARS].rstrip() + "..."
    return content, None


def render_job(row: dict) -> tuple[str, list[str]]:
    """Render a jobs_enriched row into the job_v1 text template.

    Expects the row to carry `job_description` already prepared by
    the caller — either the LLM-cleaned extraction or the raw
    truncation fallback. The source_fields marker
    (`job_description_extracted` vs `job_description_raw`) is added
    by the caller, not here, because only the caller knows which
    path was taken.
    """
    parts: list[str] = []
    present: list[str] = []

    # "<title> at <company>."
    title = row.get("title")
    company = row.get("company")
    if title and company:
        parts.append(f"{title} at {company}.")
        present.extend(["title", "company"])
    elif title:
        parts.append(f"{title}.")
        present.append("title")
    elif company:
        parts.append(f"Role at {company}.")
        present.append("company")

    # "<seniority_humanized> <employment_type> role in <location>[; remote-friendly]."
    sen = _humanize(row.get("seniority"))
    emp = row.get("employment_type")
    loc = row.get("location")
    if not loc:
        # fall back to city + state
        city = row.get("city")
        state = row.get("state")
        if city and state:
            loc = f"{city}, {state}"
        elif city:
            loc = city
        elif state:
            loc = state
    is_remote = row.get("is_remote")

    role_bits = []
    if sen:
        role_bits.append(sen)
        present.append("seniority")
    if emp:
        role_bits.append(emp)
        present.append("employment_type")
    role_prefix = " ".join(role_bits) if role_bits else "Role"
    if loc:
        suffix = "; remote-friendly" if is_remote else ""
        parts.append(f"{role_prefix} role in {loc}{suffix}.")
        present.append("location")
        if is_remote:
            present.append("is_remote")
    elif role_bits or is_remote:
        suffix = "; remote-friendly" if is_remote else ""
        parts.append(f"{role_prefix} role{suffix}.")
        if is_remote:
            present.append("is_remote")

    # NOTE: skills_required is deliberately NOT used in job_v1.
    # As of 2026-04-18 the column is 68% null and the populated 32% is
    # contaminated with pay ranges, schedules, and benefits instead of
    # actual skills (e.g. id=81 has 44 entries, all schedule info).
    # Including it added noise more than signal; the LLM-extracted
    # job_description already captures required-skill language
    # naturally. The column is preserved in the DB for other uses.

    # Job description (either LLM-cleaned or raw-truncated; caller has
    # already prepared row['job_description']). No label prefix — the
    # prose is obviously a description from context. Caller appends
    # the `job_description_extracted` / `job_description_raw` marker.
    desc = row.get("job_description")
    if desc and isinstance(desc, str) and desc.strip():
        parts.append(desc.strip())

    return " ".join(parts), present


# ---------------------------------------------------------------------------
# Azure OpenAI embedding call
# ---------------------------------------------------------------------------

def embed_text(text: str) -> list[float]:
    if not AZURE_ENDPOINT or not AZURE_KEY:
        raise RuntimeError("AZURE_OPENAI_ENDPOINT / AZURE_OPENAI_KEY not set")
    url = f"{AZURE_ENDPOINT}/openai/deployments/{DEPLOYMENT}/embeddings?api-version={API_VERSION}"
    resp = requests.post(
        url,
        headers={"api-key": AZURE_KEY, "Content-Type": "application/json"},
        json={"input": text},
        timeout=30,
    )
    resp.raise_for_status()
    vec = resp.json()["data"][0]["embedding"]
    if len(vec) != EMBED_DIM:
        raise RuntimeError(f"unexpected dim {len(vec)} != {EMBED_DIM}")
    return vec


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def content_hash(text: str, template_version: str) -> str:
    return hashlib.sha256(
        f"{template_version}\n{text}".encode("utf-8")
    ).hexdigest()


def existing_hash(cur, entity_type: str, entity_id: str) -> tuple[str, str] | None:
    cur.execute(
        "SELECT content_hash, text_template_version FROM embeddings "
        "WHERE entity_type=%s AND entity_id=%s AND model_name=%s",
        (entity_type, entity_id, MODEL_NAME),
    )
    r = cur.fetchone()
    return (r[0], r[1]) if r else None


def upsert_embedding(
    cur,
    entity_type: str,
    entity_id: str,
    vec: list[float],
    chash: str,
    template_version: str,
    source_fields: list[str],
) -> None:
    # pgvector accepts a text literal like '[1.23,4.56,...]'
    vec_literal = "[" + ",".join(repr(x) for x in vec) + "]"
    now = datetime.now(timezone.utc)
    cur.execute(
        """
        INSERT INTO embeddings (
            entity_type, entity_id, model_name, embedding,
            content_hash, text_template_version,
            embedding_generated_at, source_fields_present
        ) VALUES (%s, %s, %s, %s::vector, %s, %s, %s, %s::jsonb)
        ON CONFLICT (entity_type, entity_id, model_name) DO UPDATE SET
            embedding = EXCLUDED.embedding,
            content_hash = EXCLUDED.content_hash,
            text_template_version = EXCLUDED.text_template_version,
            embedding_generated_at = EXCLUDED.embedding_generated_at,
            source_fields_present = EXCLUDED.source_fields_present,
            updated_at = NOW()
        """,
        (
            entity_type,
            entity_id,
            MODEL_NAME,
            vec_literal,
            chash,
            template_version,
            now,
            json.dumps(source_fields),
        ),
    )


# ---------------------------------------------------------------------------
# Row pools
# ---------------------------------------------------------------------------

STUDENT_SQL = """
SELECT s.id::text AS id, s.full_name, s.institution, s.degree,
       s.field_of_study, s.graduation_year, s.city, s.state,
       s.legacy_data->>'career_objective' AS career_objective,
       array_agg(DISTINCT sk.skill_name ORDER BY sk.skill_name) AS skills
FROM students s
JOIN student_skills ss ON ss.student_id = s.id
JOIN skills sk ON sk.skill_id = ss.skill_id
WHERE s.institution IS NOT NULL
  AND s.resume_parsed = TRUE
GROUP BY s.id
ORDER BY s.id
"""

JOB_SQL = """
SELECT id::text AS id, title, company, location, city, state,
       seniority, employment_type, is_remote, skills_required,
       job_description
FROM jobs_enriched
ORDER BY id
"""


def fetch_pool(conn, entity: str) -> list[dict]:
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(STUDENT_SQL if entity == "students" else JOB_SQL)
    rows = [dict(r) for r in cur.fetchall()]
    cur.close()
    return rows


# ---------------------------------------------------------------------------
# Backfill driver
# ---------------------------------------------------------------------------

def backfill(conn, entity: str, limit: int | None, force: bool) -> dict:
    renderer = render_student if entity == "students" else render_job
    template_version = (
        STUDENT_TEMPLATE_VERSION if entity == "students" else JOB_TEMPLATE_VERSION
    )
    entity_type = "student" if entity == "students" else "jobs_enriched"

    rows = fetch_pool(conn, entity)
    if limit is not None:
        rows = rows[:limit]

    stats = {"total": len(rows), "embedded": 0, "skipped": 0, "failed": 0}
    failures: list[tuple[str, str]] = []
    samples: list[dict] = []  # first few rows' rendered text + metadata

    cur = conn.cursor()
    for row in tqdm(rows, desc=f"embedding {entity}", unit="row"):
        entity_id = row["id"]
        try:
            # Jobs: pre-process job_description via LLM extraction before
            # template rendering. Students: no extraction.
            raw_desc = None
            desc_marker = None
            if entity == "jobs":
                raw_desc = row.get("job_description")
                if raw_desc and raw_desc.strip():
                    extracted, fail_reason = extract_job_description(raw_desc)
                    if extracted is not None:
                        row["job_description"] = extracted
                        desc_marker = "job_description_extracted"
                    else:
                        # Fallback: raw truncated to JOB_DESC_MAX_CHARS.
                        truncated = raw_desc.strip()
                        if len(truncated) > JOB_DESC_MAX_CHARS:
                            truncated = truncated[:JOB_DESC_MAX_CHARS].rstrip() + "..."
                        row["job_description"] = truncated
                        desc_marker = "job_description_raw"
                        failures.append(
                            (entity_id, f"extraction fallback: {fail_reason}")
                        )

            text, present = renderer(row)
            if desc_marker is not None:
                present.append(desc_marker)
            if not text.strip():
                failures.append((entity_id, "empty rendered text"))
                stats["failed"] += 1
                continue
            chash = content_hash(text, template_version)

            existing = existing_hash(cur, entity_type, entity_id)
            if existing and existing == (chash, template_version) and not force:
                stats["skipped"] += 1
                samples.append(
                    {
                        "entity_id": entity_id,
                        "text": text,
                        "chars": len(text),
                        "fields": present,
                        "action": "skipped (hash match)",
                        "raw_description": (raw_desc[:JOB_DESC_MAX_CHARS] if raw_desc else None),
                    }
                )
                continue

            vec = embed_text(text)
            upsert_embedding(
                cur, entity_type, entity_id, vec, chash, template_version, present
            )
            conn.commit()
            stats["embedded"] += 1
            samples.append(
                {
                    "entity_id": entity_id,
                    "text": text,
                    "chars": len(text),
                    "fields": present,
                    "action": "embedded",
                    "raw_description": (raw_desc[:JOB_DESC_MAX_CHARS] if raw_desc else None),
                }
            )
            time.sleep(RATE_SLEEP_S)
        except Exception as e:
            conn.rollback()
            stats["failed"] += 1
            failures.append((entity_id, f"{type(e).__name__}: {e}"))

    cur.close()
    return {"stats": stats, "failures": failures, "samples": samples}


def main() -> int:
    p = argparse.ArgumentParser(description="Backfill embeddings (students + jobs).")
    p.add_argument(
        "--entity",
        choices=["students", "jobs", "both"],
        required=True,
        help="Which entity pool to embed.",
    )
    p.add_argument("--limit", type=int, default=None, help="Cap rows per entity.")
    p.add_argument(
        "--force",
        action="store_true",
        help="Re-embed even if content_hash + template match.",
    )
    args = p.parse_args()

    if not AZURE_KEY:
        print("ERROR: AZURE_OPENAI_KEY not set in .env", file=sys.stderr)
        return 1

    conn = psycopg2.connect(**PG_CONFIG)
    try:
        results: dict[str, Any] = {}
        entities = (
            ("students", "jobs") if args.entity == "both" else (args.entity,)
        )
        for ent in entities:
            print(f"\n=== entity: {ent} ===")
            results[ent] = backfill(conn, ent, args.limit, args.force)
            s = results[ent]["stats"]
            print(
                f"  total={s['total']} embedded={s['embedded']} "
                f"skipped={s['skipped']} failed={s['failed']}"
            )
            for eid, err in results[ent]["failures"][:5]:
                print(f"  FAIL {eid}: {err}")

        # Emit the full sample set as JSON to stdout so the caller
        # can inspect texts + metadata without re-running.
        print("\n=== SAMPLES (JSON) ===")
        out = {ent: results[ent]["samples"] for ent in entities}
        print(json.dumps(out, indent=2, default=str))
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
