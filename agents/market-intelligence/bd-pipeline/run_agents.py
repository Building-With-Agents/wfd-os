"""
Master Orchestration Script — Waifinder BD Pipeline

Runs the full pipeline in order:
0. agent15.py — market discovery (find new companies)
1. ingest.py — pull new job postings
2. enrich.py — classify and enrich
3. suppression.py — apply suppression list
4. populate_prospects.py — update prospect_companies
5. agent12.py — score all companies
6. notify.py escalations — send tier alerts
7. agent13.py distribution — process pending content
8. agent13.py signals — poll engagement

Usage:
    python run_agents.py
    python run_agents.py --deployment waifinder-national --region "Greater Seattle"
    python run_agents.py --skip-ingest --limit 5
"""
import os
import sys
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
sys.path.insert(0, os.path.dirname(__file__))

import psycopg2
from pgconfig import PG_CONFIG

from agent15 import run_discovery
from ingest import ingest, DEFAULT_QUERIES
from enrich import enrich
from suppression import run_suppression
from populate_prospects import populate
from agent12 import score_companies
from agent14 import run_agent14
from agent13 import distribute_content, process_sequence_touches, poll_for_replies
from notify import send_escalation_alerts


def run_migration():
    """Run table migrations."""
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    sql_dir = os.path.dirname(__file__)
    for sql_file in sorted(
        f for f in os.listdir(sql_dir) if f.endswith(".sql")
    ):
        path = os.path.join(sql_dir, sql_file)
        with open(path) as f:
            cur.execute(f.read())
        print(f"  Executed: {sql_file}")

    conn.close()


def main():
    parser = argparse.ArgumentParser(description="Waifinder BD Pipeline — Master Orchestration")
    parser.add_argument("--deployment", default="waifinder-national")
    parser.add_argument("--region", default="Greater Seattle")
    parser.add_argument("--skip-discovery", action="store_true")
    parser.add_argument("--skip-ingest", action="store_true")
    parser.add_argument("--skip-scoring", action="store_true")
    parser.add_argument("--skip-distribution", action="store_true")
    parser.add_argument("--skip-signals", action="store_true")
    parser.add_argument("--discovery-limit", type=int, default=None,
                        help="Limit discovery search queries (for testing)")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit companies scored (for testing)")
    args = parser.parse_args()

    print(f"{'='*60}")
    print(f"Waifinder BD Pipeline — {datetime.now(timezone.utc).isoformat()}")
    print(f"Deployment: {args.deployment} | Region: {args.region}")
    print(f"{'='*60}")

    # Step 0a: Migrations
    print(f"\n--- MIGRATIONS ---")
    run_migration()

    # Step 0b: Market Discovery (Agent 15)
    if not args.skip_discovery:
        print(f"\n--- AGENT 15 MARKET DISCOVERY ---")
        run_discovery(args.deployment, args.discovery_limit)
    else:
        print(f"\n--- AGENT 15 MARKET DISCOVERY (skipped) ---")

    # Step 1: Ingestion
    if not args.skip_ingest:
        print(f"\n--- INGESTION ---")
        ingest(args.deployment, args.region, DEFAULT_QUERIES)
    else:
        print(f"\n--- INGESTION (skipped) ---")

    # Step 2: Enrichment
    if not args.skip_ingest:
        print(f"\n--- ENRICHMENT ---")
        enrich(args.deployment)
    else:
        print(f"\n--- ENRICHMENT (skipped) ---")

    # Step 3: Suppression
    print(f"\n--- SUPPRESSION ---")
    run_suppression(args.deployment)

    # Step 4: Populate prospects
    print(f"\n--- POPULATE PROSPECTS ---")
    populate(args.deployment, args.region)

    # Step 5: Agent 12 scoring
    if not args.skip_scoring:
        print(f"\n--- AGENT 12 SCORING ---")
        score_companies(args.deployment, args.region, args.limit)
    else:
        print(f"\n--- AGENT 12 SCORING (skipped) ---")

    # Step 6: Escalation alerts
    if not args.skip_scoring:
        print(f"\n--- ESCALATION ALERTS ---")
        send_escalation_alerts(args.deployment)

    # Step 6b: Agent 14 contact discovery (non-fatal)
    print(f"\n--- AGENT 14 CONTACT DISCOVERY ---")
    try:
        run_agent14(args.deployment, hot_warm_only=True, verbose=False)
    except Exception as e:
        print(f"Agent 14 error (non-fatal): {e}")

    # Step 7: Agent 13 distribution
    if not args.skip_distribution:
        print(f"\n--- AGENT 13 DISTRIBUTION ---")
        distribute_content(args.deployment, args.region)
    else:
        print(f"\n--- AGENT 13 DISTRIBUTION (skipped) ---")

    # Step 8: Agent 13 touch processing + reply polling
    if not args.skip_signals:
        print(f"\n--- AGENT 13 TOUCH PROCESSING ---")
        process_sequence_touches(args.deployment)
        print(f"\n--- AGENT 13 REPLY POLLING ---")
        poll_for_replies(args.deployment)
    else:
        print(f"\n--- AGENT 13 TOUCHES + REPLIES (skipped) ---")

    # Summary
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    tables = ["jobs_raw", "jobs_enriched", "prospect_companies", "company_scores",
              "scoring_feedback", "content_submissions", "distribution_log", "warm_signals"]
    print(f"\n{'='*60}")
    print(f"PIPELINE SUMMARY")
    print(f"{'='*60}")
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  {table}: {count}")
        except Exception:
            conn.rollback()
            print(f"  {table}: (not found)")
    conn.close()


if __name__ == "__main__":
    main()
