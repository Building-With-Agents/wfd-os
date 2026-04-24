"""
Agent 12: Suppression Logic

Adds is_suppressed column to jobs_enriched and marks non-prospect domains.
Suppressed companies are never scored.

Usage:
    python suppression.py
    python suppression.py --deployment cfa-seattle-bd
"""
import os
import sys
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
import psycopg2
from pgconfig import PG_CONFIG

# --- Suppression lists (configurable) ---

SUPPRESSED_JOB_BOARDS = {
    "virtualvocations.com",
    "indeed.com",
    "linkedin.com",
    "glassdoor.com",
    "ziprecruiter.com",
    "dice.com",
    "monster.com",
    "careerbuilder.com",
}

SUPPRESSED_ENTERPRISE = {
    "apple.com",
    "amazon.com",
    "microsoft.com",
    "google.com",
    "meta.com",
    "accenture.com",
    "deloitte.com",
    "ibm.com",
    "oracle.com",
    "salesforce.com",
}

ALL_SUPPRESSED = SUPPRESSED_JOB_BOARDS | SUPPRESSED_ENTERPRISE


def run_suppression(deployment_id=None):
    """Add is_suppressed column and mark suppressed domains."""
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    # Add column if not exists
    cur.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name = 'jobs_enriched' AND column_name = 'is_suppressed'
            ) THEN
                ALTER TABLE jobs_enriched ADD COLUMN is_suppressed BOOLEAN DEFAULT FALSE;
            END IF;
        END $$;
    """)

    # Reset all to FALSE first
    if deployment_id:
        cur.execute(
            "UPDATE jobs_enriched SET is_suppressed = FALSE WHERE deployment_id = %s",
            (deployment_id,),
        )
    else:
        cur.execute("UPDATE jobs_enriched SET is_suppressed = FALSE")

    # Mark suppressed domains
    suppressed_list = list(ALL_SUPPRESSED)
    if deployment_id:
        cur.execute(
            """UPDATE jobs_enriched
               SET is_suppressed = TRUE
               WHERE company_domain = ANY(%s) AND deployment_id = %s""",
            (suppressed_list, deployment_id),
        )
    else:
        cur.execute(
            "UPDATE jobs_enriched SET is_suppressed = TRUE WHERE company_domain = ANY(%s)",
            (suppressed_list,),
        )

    # Also suppress records with NULL company_domain (can't score without it)
    if deployment_id:
        cur.execute(
            """UPDATE jobs_enriched
               SET is_suppressed = TRUE
               WHERE company_domain IS NULL AND deployment_id = %s""",
            (deployment_id,),
        )
    else:
        cur.execute(
            "UPDATE jobs_enriched SET is_suppressed = TRUE WHERE company_domain IS NULL"
        )

    # Report
    cur.execute(
        "SELECT COUNT(*) FROM jobs_enriched WHERE is_suppressed = TRUE"
        + (" AND deployment_id = %s" if deployment_id else ""),
        (deployment_id,) if deployment_id else None,
    )
    suppressed_count = cur.fetchone()[0]

    cur.execute(
        "SELECT COUNT(*) FROM jobs_enriched WHERE is_suppressed = FALSE"
        + (" AND deployment_id = %s" if deployment_id else ""),
        (deployment_id,) if deployment_id else None,
    )
    active_count = cur.fetchone()[0]

    # Show suppressed domains
    cur.execute(
        """SELECT company_domain, COUNT(*) as cnt
           FROM jobs_enriched
           WHERE is_suppressed = TRUE"""
        + (" AND deployment_id = %s" if deployment_id else "")
        + " GROUP BY company_domain ORDER BY cnt DESC",
        (deployment_id,) if deployment_id else None,
    )
    suppressed_details = cur.fetchall()

    conn.close()

    print(f"\nSuppression complete:")
    print(f"  Suppressed: {suppressed_count} records")
    print(f"  Active:     {active_count} records")
    print(f"\n  Suppressed domains:")
    for domain, cnt in suppressed_details:
        print(f"    {domain or '(NULL)'}: {cnt}")

    return {"suppressed": suppressed_count, "active": active_count}


def main():
    parser = argparse.ArgumentParser(description="Run suppression on jobs_enriched")
    parser.add_argument("--deployment", default=None)
    args = parser.parse_args()
    print(f"Suppression — {datetime.now(timezone.utc).isoformat()}")
    run_suppression(args.deployment)


if __name__ == "__main__":
    main()
