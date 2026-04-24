"""
Populate prospect_companies from jobs_enriched and Apollo contacts.

Usage:
    python populate_prospects.py
    python populate_prospects.py --deployment waifinder-national
"""
import os
import sys
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../apollo"))
import psycopg2
from pgconfig import PG_CONFIG
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"), override=True)

from suppression import ALL_SUPPRESSED


def populate(deployment_id, region):
    """Populate prospect_companies from jobs_enriched and Apollo."""
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    # Step 1: Pull unique non-suppressed domains from jobs_enriched
    cur.execute(
        """SELECT DISTINCT company_domain,
                  (array_agg(company ORDER BY enriched_at DESC))[1] as company_name,
                  (array_agg(region ORDER BY enriched_at DESC))[1] as region
           FROM jobs_enriched
           WHERE company_domain IS NOT NULL
             AND is_suppressed = FALSE
           GROUP BY company_domain""",
    )
    jsearch_companies = cur.fetchall()
    print(f"Found {len(jsearch_companies)} unique non-suppressed domains in jobs_enriched")

    inserted_jsearch = 0
    skipped = 0
    for domain, company_name, job_region in jsearch_companies:
        try:
            cur.execute(
                """INSERT INTO prospect_companies
                   (company_name, company_domain, entry_source, deployment_id, region)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (company_domain) DO NOTHING""",
                (company_name, domain, "jsearch", deployment_id, job_region or region),
            )
            if cur.rowcount > 0:
                inserted_jsearch += 1
            else:
                skipped += 1
        except Exception as e:
            print(f"  Error inserting {domain}: {e}")

    print(f"  JSearch: inserted {inserted_jsearch}, skipped {skipped} (already exist)")

    # Step 2: Pull company domains from Apollo contacts
    inserted_apollo = 0
    try:
        import requests
        api_key = os.getenv("APOLLO_API_KEY", "")
        if api_key:
            headers = {
                "X-Api-Key": api_key,
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            # Search for contacts with organization data
            resp = requests.post(
                "https://api.apollo.io/v1/contacts/search",
                headers=headers,
                json={"per_page": 100, "page": 1},
                timeout=15,
            )
            if resp.status_code == 200:
                contacts = resp.json().get("contacts", [])
                apollo_domains = set()
                for c in contacts:
                    org = c.get("organization", {}) or {}
                    domain = org.get("primary_domain") or org.get("website_url")
                    org_name = c.get("organization_name") or org.get("name")
                    if domain and org_name:
                        # Clean domain
                        domain = domain.lower().replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
                        if domain not in ALL_SUPPRESSED and domain not in apollo_domains:
                            apollo_domains.add(domain)
                            try:
                                cur.execute(
                                    """INSERT INTO prospect_companies
                                       (company_name, company_domain, entry_source, deployment_id, region)
                                       VALUES (%s, %s, %s, %s, %s)
                                       ON CONFLICT (company_domain) DO NOTHING""",
                                    (org_name, domain, "apollo", deployment_id, region),
                                )
                                if cur.rowcount > 0:
                                    inserted_apollo += 1
                            except Exception as e:
                                pass

                print(f"  Apollo: found {len(contacts)} contacts, {len(apollo_domains)} unique domains, inserted {inserted_apollo} new")
            else:
                print(f"  Apollo: API returned {resp.status_code}")
        else:
            print("  Apollo: APOLLO_API_KEY not set, skipping")
    except ImportError:
        print("  Apollo: requests not available, skipping")
    except Exception as e:
        print(f"  Apollo: error — {e}")

    # Step 3: Apply suppression to prospect_companies
    suppressed_list = list(ALL_SUPPRESSED)
    cur.execute(
        """UPDATE prospect_companies
           SET is_suppressed = TRUE, suppression_reason = 'suppression_list'
           WHERE company_domain = ANY(%s) AND is_suppressed = FALSE""",
        (suppressed_list,),
    )
    newly_suppressed = cur.rowcount
    print(f"  Suppressed: {newly_suppressed} additional companies")

    # Step 4: Summary
    cur.execute("SELECT COUNT(*) FROM prospect_companies WHERE is_suppressed = FALSE")
    active = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM prospect_companies WHERE is_suppressed = TRUE")
    suppressed = cur.fetchone()[0]
    cur.execute("SELECT COUNT(*) FROM prospect_companies")
    total = cur.fetchone()[0]

    cur.execute(
        """SELECT entry_source, COUNT(*) FROM prospect_companies
           WHERE is_suppressed = FALSE GROUP BY entry_source"""
    )
    by_source = cur.fetchall()

    conn.close()

    print(f"\nProspect Companies Summary:")
    print(f"  Total:      {total}")
    print(f"  Active:     {active}")
    print(f"  Suppressed: {suppressed}")
    print(f"  By source:")
    for source, cnt in by_source:
        print(f"    {source}: {cnt}")

    return {"total": total, "active": active, "suppressed": suppressed}


def main():
    parser = argparse.ArgumentParser(description="Populate prospect_companies")
    parser.add_argument("--deployment", default="waifinder-national")
    parser.add_argument("--region", default="Greater Seattle")
    args = parser.parse_args()
    print(f"Populating prospects — {datetime.now(timezone.utc).isoformat()}")
    populate(args.deployment, args.region)


if __name__ == "__main__":
    main()
