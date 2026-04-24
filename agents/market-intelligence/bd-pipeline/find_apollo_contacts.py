"""
Utility: Find best Apollo contact for each Hot/Warm company.

For each company in company_scores where tier = 'Hot' or 'Warm':
- Search Apollo for contacts at that domain
- Filter by seniority: executive > director > manager
- Filter by title keywords matching ICP buyer profile
- Write best match to hot_warm_contacts table
- Flag companies with no contact found

Usage:
    python find_apollo_contacts.py
    python find_apollo_contacts.py --deployment waifinder-national
"""
import os
import sys
import time
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
import psycopg2
from pgconfig import PG_CONFIG
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"), override=True)

import requests as http_requests

APOLLO_BASE = "https://api.apollo.io/v1"

# Priority-ordered seniority levels
SENIORITY_PRIORITY = ["executive", "director", "manager", "senior", "entry"]

# Priority-ordered title keywords (ICP buyer profile)
TITLE_KEYWORDS = [
    "executive director",
    "coo", "chief operating",
    "cio", "chief information",
    "cdo", "chief data",
    "director of operations",
    "director of technology",
    "vp ", "vice president",
    "managing partner",
    "practice administrator",
    "deputy director",
    "director of planning",
    "cfo", "chief financial",
    "director",
    "manager",
]


def _apollo_headers():
    return {
        "X-Api-Key": os.getenv("APOLLO_API_KEY", ""),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _create_table():
    """Create hot_warm_contacts table if not exists."""
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = True
    conn.cursor().execute("""
        CREATE TABLE IF NOT EXISTS hot_warm_contacts (
            id SERIAL PRIMARY KEY,
            company_domain VARCHAR(255),
            company_name VARCHAR(255),
            company_tier VARCHAR(20),
            apollo_contact_id VARCHAR(100),
            contact_name VARCHAR(255),
            contact_title VARCHAR(255),
            contact_email VARCHAR(255),
            contact_linkedin VARCHAR(255),
            apollo_account_id VARCHAR(100),
            recommended_buyer VARCHAR(255),
            found_at TIMESTAMP DEFAULT NOW(),
            match_confidence VARCHAR(20)
        );
        CREATE INDEX IF NOT EXISTS idx_hwc_domain ON hot_warm_contacts(company_domain);
        CREATE INDEX IF NOT EXISTS idx_hwc_tier ON hot_warm_contacts(company_tier);
    """)
    conn.close()


def _title_match_score(title):
    """Score a contact title against ICP buyer keywords. Lower = better."""
    if not title:
        return 999
    title_lower = title.lower()
    for i, keyword in enumerate(TITLE_KEYWORDS):
        if keyword in title_lower:
            return i
    return 999


def _seniority_score(seniority):
    """Score seniority level. Lower = better."""
    if not seniority:
        return 999
    try:
        return SENIORITY_PRIORITY.index(seniority.lower())
    except ValueError:
        return 999


def _search_contacts(domain):
    """Search Apollo for contacts at a company domain."""
    try:
        resp = http_requests.post(
            f"{APOLLO_BASE}/contacts/search",
            headers=_apollo_headers(),
            json={
                "q_organization_domains": domain,
                "per_page": 25,
            },
            timeout=15,
        )
        if resp.status_code == 200:
            return resp.json().get("contacts", [])
        else:
            print(f"    Apollo search {resp.status_code} for {domain}")
            return []
    except Exception as e:
        print(f"    Apollo error for {domain}: {e}")
        return []


def _pick_best_contact(contacts, recommended_buyer):
    """Pick the best contact based on seniority and title match."""
    if not contacts:
        return None, "none"

    scored = []
    for c in contacts:
        title = c.get("title", "")
        seniority = c.get("seniority", "")

        # Primary: match recommended buyer if available
        buyer_match = 0
        if recommended_buyer and title:
            buyer_lower = recommended_buyer.lower()
            if any(word in title.lower() for word in buyer_lower.split() if len(word) > 3):
                buyer_match = -100  # Strong boost

        t_score = _title_match_score(title)
        s_score = _seniority_score(seniority)
        total = buyer_match + s_score * 10 + t_score

        scored.append((total, c))

    scored.sort(key=lambda x: x[0])
    best_score, best = scored[0]

    # Determine match confidence
    if best_score < -50:
        confidence = "High"
    elif best_score < 20:
        confidence = "Medium"
    else:
        confidence = "Low"

    return best, confidence


def find_contacts(deployment_id):
    """Find Apollo contacts for all Hot/Warm companies."""
    _create_table()

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Get latest Hot/Warm scores
    cur.execute(
        """SELECT DISTINCT ON (company_domain)
                  company_domain, company_name, tier, recommended_buyer
           FROM company_scores
           WHERE deployment_id = %s
             AND tier IN ('Hot', 'Warm')
           ORDER BY company_domain, tier_assigned_at DESC""",
        (deployment_id,),
    )
    companies = cur.fetchall()
    print(f"\nSearching Apollo contacts for {len(companies)} Hot/Warm companies\n")

    found = 0
    not_found = []

    for domain, company_name, tier, recommended_buyer in companies:
        contacts = _search_contacts(domain)
        time.sleep(0.5)  # Rate limit

        if not contacts:
            not_found.append((company_name, domain, tier))
            print(f"  {company_name} ({domain}) [{tier}] — NO CONTACTS FOUND")
            continue

        best, confidence = _pick_best_contact(contacts, recommended_buyer)
        if not best:
            not_found.append((company_name, domain, tier))
            print(f"  {company_name} ({domain}) [{tier}] — no suitable contact")
            continue

        contact_name = f"{best.get('first_name', '')} {best.get('last_name', '')}".strip()
        contact_title = best.get("title", "")
        contact_email = best.get("email", "")
        linkedin = best.get("linkedin_url", "")
        contact_id = best.get("id", "")
        account_id = best.get("account_id", "")

        # Upsert into hot_warm_contacts
        cur.execute(
            """INSERT INTO hot_warm_contacts
               (company_domain, company_name, company_tier,
                apollo_contact_id, contact_name, contact_title,
                contact_email, contact_linkedin, apollo_account_id,
                recommended_buyer, match_confidence)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               ON CONFLICT DO NOTHING""",
            (
                domain, company_name, tier,
                contact_id, contact_name, contact_title,
                contact_email, linkedin, account_id,
                recommended_buyer, confidence,
            ),
        )
        conn.commit()
        found += 1

        print(f"  {company_name} ({domain}) [{tier}] -> {contact_name}, {contact_title} [{confidence}]")

    conn.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"Apollo Contact Search Complete")
    print(f"{'='*60}")
    print(f"  Hot/Warm companies:  {len(companies)}")
    print(f"  Contacts found:      {found}")
    print(f"  No contact found:    {len(not_found)}")

    if not_found:
        print(f"\n  Companies needing manual Apollo research:")
        for name, domain, tier in not_found:
            print(f"    [{tier}] {name} ({domain})")

    return {"found": found, "not_found": len(not_found)}


def main():
    parser = argparse.ArgumentParser(description="Find Apollo contacts for Hot/Warm companies")
    parser.add_argument("--deployment", default="waifinder-national")
    args = parser.parse_args()
    print(f"Apollo Contact Search — {datetime.now(timezone.utc).isoformat()}")
    find_contacts(args.deployment)


if __name__ == "__main__":
    main()
