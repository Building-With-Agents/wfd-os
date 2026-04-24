"""
JSearch BD Pipeline — Test Script

Runs one ingestion + enrichment cycle against Seattle, then prints:
- Total jobs found
- AI role count
- Top 5 company domains
- Confirms records in both tables
"""
import os
import sys
import json

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
sys.path.insert(0, os.path.dirname(__file__))

import psycopg2
from pgconfig import PG_CONFIG
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"), override=True)

from ingest import ingest, DEFAULT_QUERIES
from enrich import enrich


def create_tables():
    """Run the SQL migration to create tables if they don't exist."""
    sql_path = os.path.join(os.path.dirname(__file__), "001_create_tables.sql")
    with open(sql_path, "r") as f:
        sql = f.read()
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()
    cur.execute(sql)
    conn.close()
    print("Tables created/verified.\n")


def print_results(deployment_id):
    """Print summary from the database."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Count raw records
    cur.execute(
        "SELECT COUNT(*) FROM jobs_raw WHERE deployment_id = %s",
        (deployment_id,),
    )
    raw_count = cur.fetchone()[0]

    # Count enriched records
    cur.execute(
        "SELECT COUNT(*) FROM jobs_enriched WHERE deployment_id = %s",
        (deployment_id,),
    )
    enriched_count = cur.fetchone()[0]

    # AI roles
    cur.execute(
        "SELECT COUNT(*) FROM jobs_enriched WHERE deployment_id = %s AND is_ai_role = TRUE",
        (deployment_id,),
    )
    ai_count = cur.fetchone()[0]

    # Data roles
    cur.execute(
        "SELECT COUNT(*) FROM jobs_enriched WHERE deployment_id = %s AND is_data_role = TRUE",
        (deployment_id,),
    )
    data_count = cur.fetchone()[0]

    # Workforce roles
    cur.execute(
        "SELECT COUNT(*) FROM jobs_enriched WHERE deployment_id = %s AND is_workforce_role = TRUE",
        (deployment_id,),
    )
    workforce_count = cur.fetchone()[0]

    # Top 5 company domains
    cur.execute(
        """SELECT company_domain, COUNT(*) as cnt
           FROM jobs_enriched
           WHERE deployment_id = %s AND company_domain IS NOT NULL
           GROUP BY company_domain
           ORDER BY cnt DESC
           LIMIT 5""",
        (deployment_id,),
    )
    top_domains = cur.fetchall()

    # Seniority breakdown
    cur.execute(
        """SELECT seniority, COUNT(*) as cnt
           FROM jobs_enriched
           WHERE deployment_id = %s
           GROUP BY seniority
           ORDER BY cnt DESC""",
        (deployment_id,),
    )
    seniority_breakdown = cur.fetchall()

    # Sample titles
    cur.execute(
        """SELECT title, company, company_domain, is_ai_role, is_data_role
           FROM jobs_enriched
           WHERE deployment_id = %s
           ORDER BY enriched_at DESC
           LIMIT 5""",
        (deployment_id,),
    )
    samples = cur.fetchall()

    conn.close()

    # Print report
    print(f"\n{'='*60}")
    print(f"TEST RESULTS — {deployment_id}")
    print(f"{'='*60}")
    print(f"\n  jobs_raw records:     {raw_count}")
    print(f"  jobs_enriched records: {enriched_count}")
    print(f"\n  Role Classification:")
    print(f"    AI roles:         {ai_count}")
    print(f"    Data roles:       {data_count}")
    print(f"    Workforce roles:  {workforce_count}")
    print(f"\n  Seniority Breakdown:")
    for seniority, cnt in seniority_breakdown:
        print(f"    {seniority}: {cnt}")
    print(f"\n  Top 5 Company Domains:")
    for domain, cnt in top_domains:
        print(f"    {domain}: {cnt} jobs")
    print(f"\n  Sample Records:")
    for title, company, domain, is_ai, is_data in samples:
        flags = []
        if is_ai:
            flags.append("AI")
        if is_data:
            flags.append("DATA")
        flag_str = f" [{', '.join(flags)}]" if flags else ""
        print(f"    {title} @ {company} ({domain}){flag_str}")

    # Confirm both tables have data
    print(f"\n  Verification:")
    if raw_count > 0:
        print(f"    jobs_raw:     PASS ({raw_count} records)")
    else:
        print(f"    jobs_raw:     FAIL (0 records)")
    if enriched_count > 0:
        print(f"    jobs_enriched: PASS ({enriched_count} records)")
    else:
        print(f"    jobs_enriched: FAIL (0 records)")
    print()


def main():
    deployment_id = "cfa-seattle-bd"
    region = "Greater Seattle"

    print(f"JSearch BD Pipeline — Test Run")
    print(f"Deployment: {deployment_id} | Region: {region}")
    print(f"Queries: {len(DEFAULT_QUERIES)}\n")

    # Step 1: Create tables
    create_tables()

    # Step 2: Run ingestion
    print("--- INGESTION ---")
    ingest_stats = ingest(deployment_id, region, DEFAULT_QUERIES)

    # Step 3: Run enrichment
    print("\n--- ENRICHMENT ---")
    enrich_stats = enrich(deployment_id)

    # Step 4: Print results
    print_results(deployment_id)


if __name__ == "__main__":
    main()
