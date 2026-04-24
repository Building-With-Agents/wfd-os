"""
JSearch BD Pipeline — Enrichment Script

Reads unprocessed records from jobs_raw, classifies roles, extracts
company_domain, determines seniority, and writes to jobs_enriched.

Usage:
    python enrich.py
    python enrich.py --deployment cfa-seattle-bd
"""
import os
import sys
import re
import json
import argparse
from datetime import datetime, timezone
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
import psycopg2
from pgconfig import PG_CONFIG

# --- Classification patterns ---

AI_PATTERNS = re.compile(
    r"\b(AI|artificial\s+intelligence|machine\s+learning|deep\s+learning|"
    r"LLM|large\s+language\s+model|agentic|neural\s+net|GPT|Claude|Gemini|"
    r"NLP|natural\s+language\s+processing|computer\s+vision|reinforcement\s+learning)\b",
    re.IGNORECASE,
)

DATA_PATTERNS = re.compile(
    r"\b(data\s+engineer|data\s+pipeline|ETL|data\s+warehouse|"
    r"analytics\s+engineer|dbt|Spark|Airflow|data\s+infrastructure|"
    r"data\s+platform|Snowflake|BigQuery|Redshift|Databricks)\b",
    re.IGNORECASE,
)

WORKFORCE_PATTERNS = re.compile(
    r"\b(workforce\s+analytics|people\s+analytics|HR\s+data|"
    r"talent\s+analytics|labor\s+market|workforce\s+development|"
    r"workforce\s+intelligence|people\s+data|HRIS\s+analyst)\b",
    re.IGNORECASE,
)

SENIOR_PATTERNS = re.compile(
    r"\b(Director|VP|Vice\s+President|Chief|Head\s+of|SVP|EVP|CTO|CIO|CDO)\b",
    re.IGNORECASE,
)
MID_PATTERNS = re.compile(
    r"\b(Manager|Lead|Principal|Staff|Senior\s+Manager|Team\s+Lead)\b",
    re.IGNORECASE,
)


def classify_role(title, description):
    """Return (is_ai, is_data, is_workforce) booleans."""
    text = f"{title} {description}"
    return (
        bool(AI_PATTERNS.search(text)),
        bool(DATA_PATTERNS.search(text)),
        bool(WORKFORCE_PATTERNS.search(text)),
    )


def extract_domain(employer_website):
    """Extract clean domain from employer_website URL."""
    if not employer_website:
        return None
    url = employer_website.strip()
    if not url.startswith("http"):
        url = "https://" + url
    try:
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = domain.lower()
        domain = re.sub(r"^www\.", "", domain)
        domain = domain.rstrip("/")
        return domain if domain else None
    except Exception:
        return None


def determine_seniority(title):
    """Classify seniority from job title."""
    if not title:
        return "individual_contributor"
    if SENIOR_PATTERNS.search(title):
        return "senior"
    if MID_PATTERNS.search(title):
        return "mid"
    return "individual_contributor"


def enrich(deployment_id=None):
    """Enrich all unprocessed jobs_raw records into jobs_enriched."""
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = False
    cur = conn.cursor()

    # Find raw records not yet in jobs_enriched
    query = """
        SELECT r.id, r.deployment_id, r.region, r.job_id, r.raw_data
        FROM jobs_raw r
        LEFT JOIN jobs_enriched e ON r.job_id = e.job_id
        WHERE e.id IS NULL
    """
    params = []
    if deployment_id:
        query += " AND r.deployment_id = %s"
        params.append(deployment_id)

    cur.execute(query, params)
    rows = cur.fetchall()
    print(f"Found {len(rows)} unprocessed records to enrich")

    enriched = 0
    errors = 0

    for raw_id, dep_id, region, job_id, raw_data in rows:
        try:
            data = raw_data if isinstance(raw_data, dict) else json.loads(raw_data)

            title = data.get("job_title", "")
            company = data.get("employer_name", "")
            description = data.get("job_description", "")
            employer_website = data.get("employer_website", "")
            highlights = data.get("job_highlights")
            employment_type = data.get("job_employment_type", "")
            city = data.get("job_city", "")
            state = data.get("job_state", "")

            # Posted date
            posted_at = None
            posted_str = data.get("job_posted_at_datetime_utc")
            if posted_str:
                try:
                    posted_at = datetime.fromisoformat(posted_str.replace("Z", "+00:00"))
                except Exception:
                    pass

            # Location string
            location_parts = [p for p in [city, state] if p]
            location = ", ".join(location_parts) if location_parts else None

            # Classifications
            is_ai, is_data, is_workforce = classify_role(title, description)
            domain = extract_domain(employer_website)
            seniority = determine_seniority(title)

            # Extract skills from highlights
            skills = []
            if highlights and isinstance(highlights, dict):
                for section in highlights.values():
                    if isinstance(section, list):
                        skills.extend(section[:20])

            cur.execute(
                """INSERT INTO jobs_enriched
                   (deployment_id, region, job_id, title, company, company_domain,
                    location, posted_at, is_ai_role, is_data_role, is_workforce_role,
                    skills_required, seniority, job_description, job_highlights)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   ON CONFLICT (job_id) DO NOTHING""",
                (
                    dep_id, region, job_id, title[:255], company[:255], domain,
                    location, posted_at, is_ai, is_data, is_workforce,
                    skills[:50] if skills else None,
                    seniority, description, json.dumps(highlights) if highlights else None,
                ),
            )
            conn.commit()
            enriched += 1

        except Exception as e:
            conn.rollback()
            errors += 1
            if errors <= 5:
                print(f"  Error enriching {job_id}: {e}")

    conn.close()
    print(f"\nEnrichment complete:")
    print(f"  Enriched: {enriched}")
    print(f"  Errors:   {errors}")
    return {"enriched": enriched, "errors": errors}


def main():
    parser = argparse.ArgumentParser(description="JSearch BD Enrichment")
    parser.add_argument("--deployment", default=None,
                        help="Filter by deployment_id (default: all)")
    args = parser.parse_args()

    print(f"JSearch BD Enrichment — {datetime.now(timezone.utc).isoformat()}")
    enrich(args.deployment)


if __name__ == "__main__":
    main()
