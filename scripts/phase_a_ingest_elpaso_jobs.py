"""Phase A — Task 3: Ingest El Paso tech jobs via JSearch into jobs_enriched
(WSB tenant).

Reuses agents/market-intelligence/ingest/jsearch.py's `fetch_jobs()` to hit
the JSearch API, then does tenant-aware INSERTs into jobs_raw + jobs_enriched.

Design notes:
- The existing runner.py inserts into `job_listings` (Vegas-era table). We
  can't reuse it — Ritu's spec says jobs_enriched. We call jsearch.fetch_jobs()
  directly and do our own inserts.
- `jobs_raw` gets the raw JSearch payload (preserves it for future
  re-enrichment). `jobs_enriched` gets the structured columns matching the
  post-013 schema (city/state/country/is_remote/lat/lng/employment_type).
- Dedup: (deployment_id, job_id) natural key for exact JSearch matches;
  normalized title+company+location hash for cross-query dedup within a run.
- Filters: skip senior 10+ yr roles, security-clearance roles, non-El-Paso
  locations.

CLAUDE.md rules: READ from JSearch API + local env, WRITE only to
wfd_os Postgres (jobs_raw + jobs_enriched with tenant_id=WSB).
No modifications to legacy systems.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import psycopg2
import requests
from dotenv import load_dotenv


WORKTREE = Path(r"C:\Users\ritub\Projects\wfd-os\.claude\worktrees\stupefied-tharp-41af25")
ENV_PATH = Path(r"C:\Users\ritub\Projects\wfd-os\.env")
load_dotenv(ENV_PATH, override=True)

# We deliberately do NOT import jsearch.fetch_jobs — it drops the raw payload
# we need for (a) jobs_raw inserts and (b) highlights-based filtering. We do
# our own raw fetch + normalization here, matching jsearch.py's shape.

PG_CONFIG = {
    "host": "127.0.0.1",
    "database": "wfd_os",
    "user": "postgres",
    "password": "wfdos2026",
    "port": 5432,
}

DEPLOYMENT_ID = "wsb-elpaso-cohort1"
REGION = "El Paso, TX"
LOCATION = "El Paso, TX"
NUM_PAGES_PER_QUERY = 1  # JSearch free tier: 50 req/month; 6 queries × 1 page = 6 requests

QUERIES = [
    "software developer",
    "data analyst",
    "IT support",
    "AI engineer",
    "web developer",
    "information technology",
]

# Raw-payload cache (avoids re-hitting JSearch on filter adjustments)
CACHE_DIR = WORKTREE / "data" / "cohort1_jobs_raw_cache"

# Filter thresholds
SENIOR_YEARS_CAP_MONTHS = 120  # 10 years
CLEARANCE_PATTERNS = [
    r"\bactive\s+(security\s+)?clearance\b",
    r"\b(top\s+secret|ts/sci|ts\s+sci)\b",
    r"\bsecret\s+clearance\b",
    r"\bdo[dD]\s+clearance\b",
    r"\bmust\s+have\s+(an\s+)?active\s+clearance\b",
    r"\bsecurity\s+clearance\s+(required|needed)\b",
]
CLEARANCE_RE = re.compile("|".join(CLEARANCE_PATTERNS), re.IGNORECASE)
YEARS_PATTERNS = [
    r"\b(\d{2,3})\+?\s*(?:to\s*\d{1,3}\s*)?years?\s+of\s+(?:relevant\s+|progressive\s+)?experience\b",
    r"\bminimum\s+of\s+(\d{2,3})\+?\s*years?\b",
    r"\b(\d{2,3})\+?\s*years?\s+(?:of\s+)?(?:professional|industry|relevant)?\s*experience\b",
]
YEARS_RE = re.compile("|".join(YEARS_PATTERNS), re.IGNORECASE)

EL_PASO_RE = re.compile(r"\bel\s*paso\b", re.IGNORECASE)

# Borderplex metro — El Paso County TX + Doña Ana County NM (commutable to El Paso)
BORDERPLEX_CITIES_TX = {
    "el paso", "anthony", "canutillo", "clint", "fabens",
    "horizon city", "san elizario", "socorro", "tornillo", "vinton",
    "westway", "montana vista", "fort bliss",
}
BORDERPLEX_CITIES_NM = {
    "las cruces", "anthony", "chaparral", "chamberino",
    "dona ana", "doña ana", "hatch", "mesilla", "mesquite",
    "la mesa", "organ", "radium springs", "santa teresa",
    "sunland park", "vado",
}

# Senior leadership titles — above apprentice fit
SENIOR_TITLE_RE = re.compile(
    r"(^|\b)(head\s+of|director\s+of|vp\s+|chief\s+|principal\s+)",
    re.IGNORECASE,
)


def wsb_tenant_id(conn) -> str:
    cur = conn.cursor()
    cur.execute("SELECT id FROM tenants WHERE code = 'WSB'")
    row = cur.fetchone()
    if not row:
        raise RuntimeError("WSB tenant not seeded — migration 014 must be applied")
    return str(row[0])


def normalize_text(text: str | None) -> str:
    if not text:
        return ""
    t = text.lower().strip()
    t = re.sub(r"[^\w\s]", "", t)
    t = re.sub(r"\s+", " ", t)
    return t


def dedup_hash(title: str, company: str, location: str) -> str:
    combined = "|".join([normalize_text(title), normalize_text(company), normalize_text(location)])
    return hashlib.sha256(combined.encode()).hexdigest()[:32]


def parse_posted(date_str: str | None):
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except Exception:
        return None


def _is_borderplex(city: str | None, state: str | None) -> bool:
    """True if (city, state) is within El Paso County TX or Doña Ana County NM."""
    c = (city or "").strip().lower()
    s = (state or "").strip().lower()
    if s in ("tx", "texas") and c in BORDERPLEX_CITIES_TX:
        return True
    if s in ("nm", "new mexico") and c in BORDERPLEX_CITIES_NM:
        return True
    return False


def filter_reason(job: dict, raw: dict) -> str | None:
    """Return filter reason string if job should be SKIPPED, None if keep."""
    # Senior leadership title exclusion (above apprentice fit)
    title = job.get("title") or ""
    if SENIOR_TITLE_RE.search(title):
        return f"senior leadership title ('{title[:60]}')"

    # Location check — must be El Paso area or broader Borderplex metro
    city = job.get("city") or ""
    state = job.get("state") or ""
    raw_city = raw.get("job_city") or ""
    raw_state = raw.get("job_state") or ""
    raw_country = raw.get("job_country") or ""
    combined_location = f"{city} {state} {raw_city} {raw_state} {raw_country}"

    is_el_paso = bool(EL_PASO_RE.search(combined_location))
    is_borderplex = _is_borderplex(city, state) or _is_borderplex(raw_city, raw_state)
    is_remote_el_paso = (
        job.get("remote_option") == "fully_remote"
        and EL_PASO_RE.search(job.get("description") or "")
    )
    if not (is_el_paso or is_borderplex or is_remote_el_paso):
        return f"non-Borderplex location ({city or '?'}, {state or '?'})"

    description = (job.get("description") or "")[:8000]  # scan up to 8K chars
    legacy = job.get("legacy_data") or {}
    highlights = legacy.get("job_highlights") or {}
    # JSearch returns highlights as {Qualifications: [...], Responsibilities: [...]}
    hl_text = ""
    if isinstance(highlights, dict):
        for v in highlights.values():
            if isinstance(v, list):
                hl_text += " " + " ".join(str(x) for x in v)
    scan_text = description + " " + hl_text

    # Clearance check
    if CLEARANCE_RE.search(scan_text):
        return "requires active security clearance"

    # Years-of-experience check: structured field first
    req_exp = legacy.get("job_required_experience") or {}
    if isinstance(req_exp, dict):
        months = req_exp.get("required_experience_in_months")
        if isinstance(months, int) and months >= SENIOR_YEARS_CAP_MONTHS:
            return f"requires {months // 12}+ yrs experience (senior)"

    # Pattern scan for "10+ years of experience" etc.
    for m in YEARS_RE.finditer(scan_text):
        for g in m.groups():
            if g:
                try:
                    yrs = int(g)
                    if yrs >= 10:
                        return f"requires {yrs}+ yrs experience (senior, pattern match)"
                except ValueError:
                    pass

    return None


def insert_jobs_raw(conn, job_id: str, raw: dict):
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO jobs_raw (deployment_id, region, source, job_id, raw_data, ingested_at)
        VALUES (%s, %s, %s, %s, %s::jsonb, NOW())
        """,
        (DEPLOYMENT_ID, REGION, "jsearch", job_id, json.dumps(raw)),
    )


def insert_jobs_enriched(conn, tenant_uuid: str, job: dict, raw: dict) -> int:
    """Insert a single row into jobs_enriched with tenant_id=WSB. Returns new id."""
    legacy = job.get("legacy_data") or {}
    company_domain = None
    emp_website = legacy.get("employer_website") or ""
    if emp_website:
        m = re.match(r"https?://(?:www\.)?([^/]+)", emp_website)
        if m:
            company_domain = m.group(1)

    posted = parse_posted(job.get("posted_date"))
    is_remote = raw.get("job_is_remote", False)
    latitude = raw.get("job_latitude")
    longitude = raw.get("job_longitude")
    emp_type = raw.get("job_employment_type") or ""
    emp_type_display = {
        "FULLTIME": "Full-time",
        "PARTTIME": "Part-time",
        "CONTRACTOR": "Contractor",
        "INTERN": "Internship",
    }.get(emp_type, emp_type.capitalize() if emp_type else None)

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO jobs_enriched (
            deployment_id, region, job_id, title, company, company_domain,
            location, posted_at, repost_count,
            is_ai_role, is_data_role, is_workforce_role,
            skills_required, seniority,
            job_description, job_highlights,
            enriched_at, is_suppressed,
            city, state, country, is_remote, latitude, longitude, employment_type,
            tenant_id
        ) VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s::jsonb,
            NOW(), FALSE,
            %s, %s, %s, %s, %s, %s, %s,
            %s
        )
        RETURNING id
        """,
        (
            DEPLOYMENT_ID,
            REGION,
            job.get("source_id") or "",
            (job.get("title") or "")[:512],
            (job.get("company") or "")[:512],
            company_domain,
            (f"{job.get('city') or ''}, {job.get('state') or ''}").strip(", ")[:256] or None,
            posted,
            0,  # repost_count unknown from JSearch
            None, None, None,  # is_ai/data/workforce_role — leave to later enrichment
            None,  # skills_required — not in JSearch payload directly
            None,  # seniority — could infer later
            job.get("description"),
            json.dumps(legacy.get("job_highlights")) if legacy.get("job_highlights") else None,
            job.get("city"),
            job.get("state"),
            raw.get("job_country") or "US",
            bool(is_remote),
            latitude,
            longitude,
            emp_type_display,
            tenant_uuid,
        ),
    )
    return cur.fetchone()[0]


def reconcile_delete_failing(conn, tenant_uuid: str) -> list[dict]:
    """Scan existing WSB jobs_enriched rows against current filter rules;
    DELETE rows that no longer pass (title now matches senior-title regex,
    etc.). Also deletes matching jobs_raw rows for consistency.
    Returns a list of deleted rows with reasons.
    """
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, job_id, title, company, city, state
        FROM jobs_enriched
        WHERE tenant_id = %s AND deployment_id = %s
        """,
        (tenant_uuid, DEPLOYMENT_ID),
    )
    rows = cur.fetchall()
    to_delete = []
    for (jid_pk, job_id, title, company, city, state) in rows:
        reasons = []
        if title and SENIOR_TITLE_RE.search(title):
            reasons.append(f"senior leadership title ('{title[:60]}')")
        # Note: we don't re-check location here because existing rows
        # passed the previous (narrower) filter; the new filter is strictly
        # broader on location. Title-based exclusion is the only delta
        # that can cause an existing row to now fail.
        if reasons:
            to_delete.append({
                "id": jid_pk,
                "job_id": job_id,
                "title": title,
                "company": company,
                "city": city,
                "state": state,
                "reasons": reasons,
            })
    if to_delete:
        ids = tuple(x["id"] for x in to_delete)
        jids = tuple(x["job_id"] for x in to_delete if x["job_id"])
        cur.execute("DELETE FROM jobs_enriched WHERE id = ANY(%s)", (list(ids),))
        if jids:
            cur.execute(
                "DELETE FROM jobs_raw WHERE deployment_id = %s AND job_id = ANY(%s)",
                (DEPLOYMENT_ID, list(jids)),
            )
        conn.commit()
    return to_delete


def run(reconcile: bool = False, refresh_cache: bool = False):
    print("=" * 70)
    print("Phase A Task 3 — Ingest El Paso tech jobs via JSearch (tenant=WSB)")
    if reconcile:
        print("  mode: --reconcile  (will DELETE existing rows that fail current filter)")
    if refresh_cache:
        print("  mode: --refresh-cache  (will re-hit API even if cache exists)")
    print("=" * 70)

    if not os.getenv("RAPIDAPI_KEY"):
        print("ERROR: RAPIDAPI_KEY missing from .env")
        return 2

    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False
    tenant_uuid = wsb_tenant_id(conn)
    print(f"WSB tenant_id: {tenant_uuid}")
    print(f"deployment_id: {DEPLOYMENT_ID}")
    print(f"region:        {REGION}")
    print(f"location:      {LOCATION}")
    print(f"queries ({len(QUERIES)}):  {QUERIES}")
    print(f"pages/query:   {NUM_PAGES_PER_QUERY}")
    print()

    deleted_rows: list[dict] = []
    if reconcile:
        deleted_rows = reconcile_delete_failing(conn, tenant_uuid)
        print(f"[reconcile] DELETEd {len(deleted_rows)} existing WSB rows that fail current filter:")
        for d in deleted_rows:
            reasons = "; ".join(d["reasons"])
            print(f"  - #{d['id']} {d['title'][:60]} @ {(d['company'] or '')[:30]}  — {reasons}")
        print()

    per_query_stats: list[dict] = []
    all_jobs = []  # list of (source_job, raw_item)
    seen_jsearch_ids: set[str] = set()
    seen_hashes: set[str] = set()

    # --- Fetch all queries (cache-first), with in-memory dedup across queries ---
    for q in QUERIES:
        print(f"\n>>> Query: '{q}' in {LOCATION}")
        try:
            raw_items = _fetch_raw(q, LOCATION, NUM_PAGES_PER_QUERY, use_cache=not refresh_cache)
        except Exception as e:
            print(f"  ERROR fetching '{q}': {e}")
            per_query_stats.append({"query": q, "fetched": 0, "new": 0, "dup": 0, "error": str(e)})
            continue

        new_for_query = 0
        dup_for_query = 0
        for raw in raw_items:
            job = _normalize_jsearch(raw)
            jid = job.get("source_id")
            if jid and jid in seen_jsearch_ids:
                dup_for_query += 1
                continue
            h = dedup_hash(
                job.get("title") or "",
                job.get("company") or "",
                f"{job.get('city') or ''}, {job.get('state') or ''}",
            )
            if h in seen_hashes:
                dup_for_query += 1
                continue
            seen_jsearch_ids.add(jid or "")
            seen_hashes.add(h)
            all_jobs.append((job, raw, q))
            new_for_query += 1
        per_query_stats.append({"query": q, "fetched": len(raw_items), "new": new_for_query, "dup": dup_for_query})
        print(f"  ... fetched {len(raw_items)}, kept {new_for_query} new, {dup_for_query} dup within run")
        # Be polite to the API
        time.sleep(1)

    print()
    print("=" * 70)
    print(f"Total raw candidates after in-run dedup: {len(all_jobs)}")
    print("=" * 70)

    # --- Filter + dedup against existing DB (deployment_id, job_id) ---
    cur = conn.cursor()
    cur.execute(
        "SELECT job_id FROM jobs_enriched WHERE deployment_id = %s",
        (DEPLOYMENT_ID,),
    )
    existing_ids = set(r[0] for r in cur.fetchall())
    print(f"Existing jobs_enriched rows for deployment '{DEPLOYMENT_ID}': {len(existing_ids)}")

    kept = []
    filter_log: list[tuple[str, str, str]] = []
    for job, raw, q in all_jobs:
        jid = job.get("source_id") or ""
        if jid in existing_ids:
            filter_log.append((job.get("title", ""), job.get("company", ""), "already in DB"))
            continue
        reason = filter_reason(job, raw)
        if reason:
            filter_log.append((job.get("title", ""), job.get("company", ""), reason))
            continue
        kept.append((job, raw, q))

    # Helper used for all terminal output — strips emoji/non-ASCII so
    # Windows cp1252 consoles don't crash mid-run. (Bytes in DB/digest are fine.)
    def _ascii(s: str) -> str:
        return (s or "").encode("ascii", "replace").decode("ascii")

    print(f"After filtering: {len(kept)} kept, {len(filter_log)} rejected")
    print()
    if filter_log:
        print("Rejected jobs (title | company | reason):")
        for t, c, r in filter_log[:30]:
            print(f"  - {_ascii(t)[:60]:<62} {_ascii(c)[:30]:<32} {r}")
        if len(filter_log) > 30:
            print(f"  ... and {len(filter_log) - 30} more")
        print()

    # --- Insert ---
    inserted = 0
    errors = 0
    insert_log: list[dict] = []
    for job, raw, q in kept:
        try:
            jid = job.get("source_id") or ""
            if raw:
                insert_jobs_raw(conn, jid, raw)
            new_id = insert_jobs_enriched(conn, tenant_uuid, job, raw)
            conn.commit()
            inserted += 1
            insert_log.append({
                "id": new_id,
                "job_id": jid,
                "title": job.get("title"),
                "company": job.get("company"),
                "city": job.get("city"),
                "state": job.get("state"),
                "is_remote": bool(raw.get("job_is_remote", False)) if raw else False,
                "posted_date": job.get("posted_date"),
                "employment_type": job.get("employment_type"),
                "query": q,
            })
        except Exception as e:
            conn.rollback()
            errors += 1
            print(f"  ERROR inserting {_ascii(job.get('title') or '')[:40]}: {e}")

    conn.close()

    # --- Report ---
    print()
    print("=" * 70)
    print(f"Inserted: {inserted}  Errors: {errors}")
    print("=" * 70)
    print()
    print("Per-query breakdown:")
    for s in per_query_stats:
        line = f"  {s['query']:<25} fetched={s.get('fetched',0):<3} new={s.get('new',0):<3} dup_in_run={s.get('dup',0)}"
        if s.get("error"):
            line += f"  ERROR={s['error']}"
        print(line)

    print()
    print("Sample of ingested jobs (up to 10):")
    for r in insert_log[:10]:
        remote = " [REMOTE]" if r["is_remote"] else ""
        title = _ascii(r["title"])[:55]
        company = _ascii(r["company"])[:25]
        print(f"  #{r['id']:<4} {title:<57} @ {company:<27} {r['city'] or '?'}, {r['state'] or '?'}{remote}")

    # Digest for summary doc
    digest_path = WORKTREE / "data" / "cohort1_jobs_ingestion_digest.json"
    digest_path.parent.mkdir(parents=True, exist_ok=True)
    digest_path.write_text(json.dumps({
        "inserted_this_run": inserted,
        "errors": errors,
        "candidates_raw": len(all_jobs),
        "rejected": len(filter_log),
        "reconciled_deletes": deleted_rows,
        "per_query": per_query_stats,
        "inserted_jobs": insert_log,
        "rejected_jobs": [{"title": t, "company": c, "reason": r} for t, c, r in filter_log],
    }, indent=2, default=str), encoding="utf-8")
    print()
    print(f"Digest written: {digest_path}")

    return 0 if errors == 0 else 1


# --- helpers for raw payload access ---
# jsearch.fetch_jobs() returns normalized dicts, losing the raw JSearch
# payload needed for jobs_raw + clearance/years scanning. We re-request
# the raw JSON for each query from JSearch, which costs the same quota
# (per call). To stay within the 50 req/month free tier we do NOT double
# the request count: we do ONE direct raw fetch per query and parse from
# that, then the fetch_jobs() call above is also one per query — total is
# 2 per query.
# Wait — that doubles cost. Better: replace fetch_jobs() with a single
# direct fetch that returns both normalized + raw. See _fetch_raw below.

def _cache_path(query: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "_", query.lower()).strip("_")
    return CACHE_DIR / f"{slug}.json"


def _fetch_raw(query: str, location: str, num_pages: int, use_cache: bool = True) -> list[dict]:
    """Direct JSearch call returning the raw payload. Caches to
    data/cohort1_jobs_raw_cache/<slug>.json so filter adjustments don't
    need to re-hit the API. Pass use_cache=False to force a fresh fetch.
    """
    cache = _cache_path(query)
    if use_cache and cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
        if isinstance(data, list) and data:
            print(f"  (cache hit: {cache.name})")
            return data

    api_key = os.getenv("RAPIDAPI_KEY")
    headers = {
        "X-RapidAPI-Host": "jsearch.p.rapidapi.com",
        "X-RapidAPI-Key": api_key,
    }
    out = []
    for p in range(1, num_pages + 1):
        params = {
            "query": f"{query} in {location}",
            "page": str(p),
            "num_pages": "1",
            "date_posted": "month",
        }
        r = requests.get("https://jsearch.p.rapidapi.com/search", headers=headers, params=params, timeout=30)
        r.raise_for_status()
        out.extend(r.json().get("data", []))
    cache.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"  (fresh fetch, cached to {cache.name})")
    return out


def _normalize_jsearch(raw: dict) -> dict:
    """Normalize a single JSearch raw item into the shape our filter + insert expect.

    Mirrors agents/market-intelligence/ingest/jsearch.py::fetch_jobs() so existing
    code paths remain comparable. NOT imported from there because we also need
    the raw payload for jobs_raw + highlights-based filtering.
    """
    remote = raw.get("job_is_remote", False)
    emp_type = raw.get("job_employment_type", "") or ""
    emp_map = {
        "FULLTIME": "full_time",
        "PARTTIME": "part_time",
        "CONTRACTOR": "contract",
        "INTERN": "internship",
    }
    employment_type = emp_map.get(emp_type, emp_type.lower() if emp_type else "full_time")
    posted_date = None
    posted_ts = raw.get("job_posted_at_datetime_utc")
    if posted_ts:
        try:
            posted_date = datetime.fromisoformat(posted_ts.replace("Z", "+00:00")).strftime("%Y-%m-%d")
        except Exception:
            pass
    return {
        "source": "jsearch",
        "source_id": raw.get("job_id"),
        "title": raw.get("job_title", "Untitled"),
        "description": raw.get("job_description", "") or "",
        "company": raw.get("employer_name", ""),
        "city": raw.get("job_city"),
        "state": raw.get("job_state"),
        "zipcode": None,
        "remote_option": "fully_remote" if remote else None,
        "employment_type": employment_type,
        "salary_min": raw.get("job_min_salary"),
        "salary_max": raw.get("job_max_salary"),
        "salary_period": (raw.get("job_salary_period") or "").lower() or None,
        "soc_code": raw.get("job_onet_soc"),
        "posted_date": posted_date,
        "expires_date": None,
        "url": raw.get("job_apply_link"),
        "legacy_data": {
            "employer_logo": raw.get("employer_logo"),
            "employer_website": raw.get("employer_website"),
            "job_publisher": raw.get("job_publisher"),
            "job_highlights": raw.get("job_highlights"),
            "job_required_experience": raw.get("job_required_experience"),
            "job_required_education": raw.get("job_required_education"),
        },
    }


if __name__ == "__main__":
    reconcile = "--reconcile" in sys.argv
    refresh_cache = "--refresh-cache" in sys.argv
    sys.exit(run(reconcile=reconcile, refresh_cache=refresh_cache))
