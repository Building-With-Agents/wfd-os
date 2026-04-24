"""
JSearch BD Pipeline — Ingestion Script

Calls JSearch API for configured search queries against a target region,
writes raw responses to jobs_raw, deduplicates on job_id, and increments
repost_count on jobs_enriched if a duplicate is detected.

Usage:
    python ingest.py
    python ingest.py --deployment cfa-seattle-bd --region "Greater Seattle"
"""
import os
import sys
import json
import argparse
import requests
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
import psycopg2
from pgconfig import PG_CONFIG
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"), override=True)

BASE_URL = "https://jsearch.p.rapidapi.com/search"

# Default queries — override via --queries flag
# National mid-market targeted queries
DEFAULT_QUERIES = [
    "data analyst workforce development",
    "analytics manager community health center",
    "data manager legal services",
    "operations analyst nonprofit",
    "HR data manager mid-size company",
    "IT director workforce board",
    "data coordinator human services",
    "reporting analyst federally qualified health center",
    "business intelligence analyst regional healthcare",
    "grants data manager workforce",
    "operations data manager professional services",
    # Seattle-specific queries
    "AI engineer Seattle",
    "data engineer Seattle",
    "workforce analytics Seattle",
]


def fetch_jsearch(query, api_key, api_host, num_pages=1, date_posted="month"):
    """Fetch jobs from JSearch API for a single query."""
    headers = {
        "X-RapidAPI-Host": api_host,
        "X-RapidAPI-Key": api_key,
    }
    all_jobs = []
    for page in range(1, num_pages + 1):
        params = {
            "query": query,
            "page": str(page),
            "num_pages": "1",
            "date_posted": date_posted,
        }
        resp = requests.get(BASE_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        jobs = data.get("data", [])
        all_jobs.extend(jobs)
        print(f"  [{query}] page {page}: {len(jobs)} jobs")
        if not jobs:
            break
    return all_jobs


def ingest(deployment_id, region, queries, num_pages=1, date_posted="month"):
    """Run ingestion: fetch from JSearch, write to jobs_raw, handle dedup."""
    api_key = os.getenv("RAPIDAPI_KEY")
    api_host = os.getenv("RAPIDAPI_HOST", "jsearch.p.rapidapi.com")
    if not api_key:
        print("ERROR: RAPIDAPI_KEY not set")
        return {"fetched": 0, "inserted": 0, "duplicates": 0, "errors": 0}

    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False

    total_fetched = 0
    total_inserted = 0
    total_dupes = 0
    total_errors = 0

    for query in queries:
        print(f"\n--- Query: {query} ---")
        try:
            raw_jobs = fetch_jsearch(query, api_key, api_host, num_pages, date_posted)
        except Exception as e:
            print(f"  API error: {e}")
            total_errors += 1
            continue

        total_fetched += len(raw_jobs)

        for job in raw_jobs:
            job_id = job.get("job_id")
            if not job_id:
                total_errors += 1
                continue

            cur = conn.cursor()
            try:
                # Check if job_id already exists in jobs_raw
                cur.execute("SELECT 1 FROM jobs_raw WHERE job_id = %s", (job_id,))
                if cur.fetchone():
                    # Duplicate — increment repost_count in jobs_enriched
                    cur.execute(
                        "UPDATE jobs_enriched SET repost_count = repost_count + 1 WHERE job_id = %s",
                        (job_id,),
                    )
                    conn.commit()
                    total_dupes += 1
                    continue

                # Insert into jobs_raw
                cur.execute(
                    """INSERT INTO jobs_raw (deployment_id, region, source, job_id, raw_data)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (deployment_id, region, "jsearch", job_id, json.dumps(job)),
                )
                conn.commit()
                total_inserted += 1

            except psycopg2.IntegrityError:
                conn.rollback()
                total_dupes += 1
            except Exception as e:
                conn.rollback()
                total_errors += 1
                print(f"  Insert error for {job_id}: {e}")

    conn.close()

    stats = {
        "fetched": total_fetched,
        "inserted": total_inserted,
        "duplicates": total_dupes,
        "errors": total_errors,
    }
    print(f"\n{'='*50}")
    print(f"Ingestion complete: {deployment_id} / {region}")
    print(f"  Fetched:    {stats['fetched']}")
    print(f"  Inserted:   {stats['inserted']}")
    print(f"  Duplicates: {stats['duplicates']}")
    print(f"  Errors:     {stats['errors']}")
    return stats


def main():
    parser = argparse.ArgumentParser(description="JSearch BD Ingestion")
    parser.add_argument("--deployment", default="cfa-seattle-bd")
    parser.add_argument("--region", default="Greater Seattle")
    parser.add_argument("--queries", nargs="+", default=None,
                        help="Override default search queries")
    parser.add_argument("--num-pages", type=int, default=1)
    parser.add_argument("--date-posted", default="month",
                        choices=["today", "3days", "week", "month", "all"])
    args = parser.parse_args()

    queries = args.queries or DEFAULT_QUERIES
    print(f"JSearch BD Ingestion — {datetime.now(timezone.utc).isoformat()}")
    print(f"Deployment: {args.deployment} | Region: {args.region}")
    print(f"Queries: {len(queries)}")

    ingest(args.deployment, args.region, queries, args.num_pages, args.date_posted)


if __name__ == "__main__":
    main()
