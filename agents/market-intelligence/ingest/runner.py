"""
Market Intelligence Agent -- Ingestion Pipeline Runner

Orchestrates: fetch -> dedup -> digital filter -> insert into PostgreSQL

Usage:
    python runner.py --source usajobs --location "El Paso, Texas" --limit 50
    python runner.py --source arbeitnow --limit 50
    python runner.py --source jsearch --location "El Paso, TX" --limit 50
    python runner.py --source all --location "El Paso, TX" --limit 50
"""
import sys
import os
import json
import argparse
from datetime import datetime, timezone

# Add paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
import psycopg2
from pgconfig import PG_CONFIG

# Load env
from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"), override=True)

from dedup import compute_job_hash, is_duplicate, check_source_id_exists
from digital_filter import filter_digital_role
from usajobs import fetch_jobs as fetch_usajobs
from arbeitnow import fetch_jobs as fetch_arbeitnow
from jsearch import fetch_jobs as fetch_jsearch


def insert_job(conn, job, filter_result, job_hash):
    """Insert a single job into job_listings table."""
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO job_listings (
            source, source_id, title, description,
            city, state, zipcode,
            remote_option, employment_type,
            salary_min, salary_max, salary_period,
            soc_code, posted_date, expires_date,
            status, job_hash, is_digital, digital_filter_layer,
            legacy_data, created_at
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s
        )
        RETURNING id
    """, (
        job["source"],
        job.get("source_id"),
        job["title"][:500],
        job.get("description"),
        job.get("city", "")[:100] if job.get("city") else None,
        job.get("state", "")[:50] if job.get("state") else None,
        job.get("zipcode"),
        job.get("remote_option"),
        job.get("employment_type"),
        job.get("salary_min"),
        job.get("salary_max"),
        job.get("salary_period"),
        job.get("soc_code"),
        job.get("posted_date"),
        job.get("expires_date"),
        "active",
        job_hash,
        filter_result["is_digital"],
        filter_result["filter_layer"],
        json.dumps(job.get("legacy_data")) if job.get("legacy_data") else None,
        datetime.now(timezone.utc),
    ))
    return cur.fetchone()[0]


def run_ingestion(source, location, limit, keyword=None):
    """Run the full ingestion pipeline for a given source."""
    print(f"\n{'='*60}")
    print(f"Ingesting from: {source}")
    print(f"Location: {location}")
    print(f"Limit: {limit}")
    print(f"{'='*60}\n")

    # Fetch jobs from source
    jobs = []
    if source == "usajobs":
        api_key = os.getenv("USAJOBS_API_KEY")
        if not api_key:
            print("  Skipping USAJobs -- USAJOBS_API_KEY not set in .env")
            print("  Get a free key at: https://developer.usajobs.gov/APIRequest/Index")
            return None
        try:
            fetched, total = fetch_usajobs(
                keyword=keyword,
                location_name=location,
                results_per_page=min(limit, 500),
            )
            jobs = fetched[:limit]
        except Exception as e:
            print(f"  USAJobs API error: {e}")
            return None

    elif source == "arbeitnow":
        page = 1
        while len(jobs) < limit:
            fetched, total = fetch_arbeitnow(page=page, us_only=True)
            if not fetched:
                break
            jobs.extend(fetched)
            page += 1
            if page > 10:  # Safety limit
                break
        jobs = jobs[:limit]

    elif source == "jsearch":
        num_pages = max(1, limit // 10)
        fetched, total = fetch_jsearch(
            query=keyword or "tech jobs",
            location=location,
            num_pages=num_pages,
        )
        jobs = fetched[:limit]

    else:
        print(f"Unknown source: {source}")
        return

    if not jobs:
        print(f"  No jobs fetched from {source}")
        return

    print(f"\nProcessing {len(jobs)} jobs through pipeline...\n")

    # Connect to PostgreSQL
    conn = psycopg2.connect(**PG_CONFIG)

    inserted = 0
    duplicates = 0
    filtered_out = 0
    ambiguous = 0
    errors = 0

    for i, job in enumerate(jobs):
        try:
            # Step 1: Dedup
            location_str = f"{job.get('city', '')}, {job.get('state', '')}"
            job_hash = compute_job_hash(job["title"], job.get("company", ""), location_str)

            if is_duplicate(conn, job_hash):
                duplicates += 1
                continue

            if check_source_id_exists(conn, job["source"], job.get("source_id")):
                duplicates += 1
                continue

            # Step 2: Digital role filter
            filter_result = filter_digital_role(
                job["title"],
                job.get("description", "")
            )

            if filter_result["is_digital"] is False:
                filtered_out += 1
                continue

            if filter_result["is_digital"] is None:
                ambiguous += 1
                # Still insert ambiguous jobs, marked for review

            # Step 3: Insert
            job_id = insert_job(conn, job, filter_result, job_hash)
            conn.commit()
            inserted += 1

            # Progress
            if (i + 1) % 10 == 0 or i == len(jobs) - 1:
                print(f"  [{i+1}/{len(jobs)}] Inserted: {inserted}, "
                      f"Dupes: {duplicates}, Filtered: {filtered_out}, "
                      f"Ambiguous: {ambiguous}")

        except Exception as e:
            errors += 1
            conn.rollback()
            if errors <= 3:
                print(f"  Error on job '{job.get('title', '?')[:50]}': {e}")

    conn.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"Ingestion Complete: {source}")
    print(f"{'='*60}")
    print(f"  Fetched:      {len(jobs)}")
    print(f"  Inserted:     {inserted}")
    print(f"  Duplicates:   {duplicates}")
    print(f"  Filtered out: {filtered_out} (non-digital)")
    print(f"  Ambiguous:    {ambiguous} (needs LLM review)")
    print(f"  Errors:       {errors}")

    return {
        "source": source,
        "fetched": len(jobs),
        "inserted": inserted,
        "duplicates": duplicates,
        "filtered_out": filtered_out,
        "ambiguous": ambiguous,
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(description="Market Intelligence Job Ingestion")
    parser.add_argument("--source", required=True,
                       choices=["usajobs", "arbeitnow", "jsearch", "all"],
                       help="Job source to ingest from")
    parser.add_argument("--location", default="El Paso, Texas",
                       help="Location filter (default: El Paso, Texas)")
    parser.add_argument("--limit", type=int, default=50,
                       help="Max jobs to fetch per source (default: 50)")
    parser.add_argument("--keyword", default=None,
                       help="Keyword/title search (default: broad search)")

    args = parser.parse_args()

    print("=" * 60)
    print("Market Intelligence Agent -- Job Ingestion Pipeline")
    print(f"Time: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    results = []

    if args.source == "all":
        for src in ["usajobs", "arbeitnow"]:
            r = run_ingestion(src, args.location, args.limit, args.keyword)
            if r:
                results.append(r)
        # JSearch only if key available
        if os.getenv("RAPIDAPI_KEY"):
            r = run_ingestion("jsearch", args.location, args.limit, args.keyword)
            if r:
                results.append(r)
        else:
            print("\n  Skipping JSearch -- RAPIDAPI_KEY not set")
    else:
        r = run_ingestion(args.source, args.location, args.limit, args.keyword)
        if r:
            results.append(r)

    # Final summary
    if results:
        print(f"\n{'='*60}")
        print("OVERALL SUMMARY")
        print(f"{'='*60}")
        total_inserted = sum(r["inserted"] for r in results)
        total_fetched = sum(r["fetched"] for r in results)
        print(f"  Total fetched:  {total_fetched}")
        print(f"  Total inserted: {total_inserted}")

        # Show DB totals
        try:
            conn = psycopg2.connect(**PG_CONFIG)
            cur = conn.cursor()
            cur.execute("""
                SELECT source, count(*),
                       count(*) FILTER (WHERE is_digital = TRUE) as digital,
                       count(*) FILTER (WHERE is_digital IS NULL) as ambiguous
                FROM job_listings
                GROUP BY source
                ORDER BY count(*) DESC
            """)
            print(f"\n  Job listings by source (all time):")
            for source, total, digital, ambig in cur.fetchall():
                print(f"    {source}: {total} total, {digital} digital, {ambig} ambiguous")
            conn.close()
        except:
            pass


if __name__ == "__main__":
    main()
