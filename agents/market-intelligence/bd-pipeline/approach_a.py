"""
Agent 12 — Approach A: Scripted 5-Dimension Scoring

Scores each non-suppressed company across five weighted dimensions
and assigns Hot/Warm/Monitor tier. Writes to company_scores_a.

Usage:
    python approach_a.py
    python approach_a.py --deployment cfa-seattle-bd --region "Greater Seattle"
"""
import os
import sys
import json
import argparse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
import psycopg2
from pgconfig import PG_CONFIG

# ============================================================
# CONFIG — all weights and thresholds here, never in logic
# ============================================================

WEIGHTS = {
    "ai_signal": 0.30,
    "urgency": 0.25,
    "icp_fit": 0.20,
    "tech_signals": 0.15,
    "engagement": 0.10,
}

TIERS = {
    "Hot": 11,
    "Warm": 6,
    "Monitor": 1,
}

TIER_EXPIRY_DAYS = 7

# ICP fit keywords (for inferring from job posting content)
ICP_PRIMARY = [
    "workforce board", "workforce development", "healthcare", "health clinic",
    "legal", "law firm", "professional services", "consulting",
    "staffing", "recruitment agency",
]
ICP_ADJACENT = [
    "education", "university", "college", "nonprofit", "non-profit",
    "government", "public sector", "school district",
]

# Tech pain signals in job descriptions
TECH_PAIN_SIGNALS = [
    "fragmented systems", "legacy", "manual processes", "spreadsheets",
    "excel-based", "siloed data", "data silos", "outdated", "technical debt",
    "disparate systems", "manual reporting", "no automation",
]
MATURE_TECH_SIGNALS = [
    "data lake", "data warehouse", "snowflake", "databricks", "airflow",
    "dbt", "kafka", "terraform", "kubernetes", "cicd", "ci/cd",
    "microservices", "data mesh", "mlops",
]


def _score_ai_signal(jobs):
    """Dimension 1: AI Role Signal Strength (max 3 points)."""
    ai_count = sum(1 for j in jobs if j.get("is_ai_role"))
    if ai_count >= 3:
        return 3, f"{ai_count} AI roles posted"
    elif ai_count >= 1:
        return 2, f"{ai_count} AI role(s) posted"
    data_count = sum(1 for j in jobs if j.get("is_data_role"))
    if data_count > 0:
        return 1, f"{data_count} data/analytics role(s) only"
    return 0, "No AI or data roles"


def _score_urgency(jobs):
    """Dimension 2: Hiring Urgency (max 3 points)."""
    max_repost = max((j.get("repost_count", 0) for j in jobs), default=0)
    if max_repost >= 2:
        return 3, f"Repost count {max_repost} — high urgency"

    now = datetime.now(timezone.utc)
    oldest_days = 0
    for j in jobs:
        posted = j.get("posted_at")
        if posted:
            if isinstance(posted, str):
                try:
                    posted = datetime.fromisoformat(posted)
                except Exception:
                    continue
            if posted.tzinfo is None:
                posted = posted.replace(tzinfo=timezone.utc)
            days = (now - posted).days
            oldest_days = max(oldest_days, days)

    if oldest_days >= 30:
        return 2, f"Role open {oldest_days} days"
    return 1, "New posting, no reposts"


def _score_icp_fit(jobs, company_domain):
    """Dimension 3: ICP Fit (max 3 points)."""
    combined_text = " ".join(
        f"{j.get('title', '')} {j.get('job_description', '')}" for j in jobs
    ).lower()

    for kw in ICP_PRIMARY:
        if kw in combined_text:
            return 3, f"ICP primary match: '{kw}'"

    for kw in ICP_ADJACENT:
        if kw in combined_text:
            return 2, f"ICP adjacent: '{kw}'"

    return 1, "No strong ICP signal from postings"


def _score_tech_signals(jobs):
    """Dimension 4: Technology Signals (max 3 points)."""
    combined_text = " ".join(
        j.get("job_description", "") for j in jobs
    ).lower()

    pain_hits = [s for s in TECH_PAIN_SIGNALS if s in combined_text]
    mature_hits = [s for s in MATURE_TECH_SIGNALS if s in combined_text]

    if pain_hits and not mature_hits:
        return 3, f"Tech pain: {', '.join(pain_hits[:3])}"
    if pain_hits and mature_hits:
        return 2, f"Mixed signals — pain: {', '.join(pain_hits[:2])}, mature: {', '.join(mature_hits[:2])}"
    if mature_hits:
        return 1, f"Mature data infra: {', '.join(mature_hits[:3])}"
    return 2, "No explicit tech signals — default mixed"


def _score_engagement(company_domain, deployment_id, cur):
    """Dimension 5: Engagement History (max 3 points)."""
    cur.execute(
        "SELECT COUNT(*) FROM scoring_feedback WHERE company_domain = %s",
        (company_domain,),
    )
    count = cur.fetchone()[0]
    if count > 0:
        return 3, f"{count} prior engagement(s)"
    return 1, "No prior engagement"


def _assign_tier(total_score):
    """Assign tier based on weighted total score."""
    if total_score >= TIERS["Hot"]:
        return "Hot"
    elif total_score >= TIERS["Warm"]:
        return "Warm"
    return "Monitor"


def score_companies(deployment_id, region):
    """Score all non-suppressed companies via Approach A."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Get distinct non-suppressed company domains with their jobs
    cur.execute(
        """SELECT DISTINCT company_domain
           FROM jobs_enriched
           WHERE deployment_id = %s
             AND is_suppressed = FALSE
             AND company_domain IS NOT NULL
             AND posted_at >= NOW() - INTERVAL '30 days'""",
        (deployment_id,),
    )
    domains = [row[0] for row in cur.fetchall()]
    print(f"Scoring {len(domains)} companies via Approach A")

    scored = 0
    for domain in domains:
        # Get all jobs for this company in last 30 days
        cur.execute(
            """SELECT job_id, title, company, company_domain, posted_at,
                      repost_count, is_ai_role, is_data_role, is_workforce_role,
                      skills_required, seniority, job_description, job_highlights
               FROM jobs_enriched
               WHERE company_domain = %s
                 AND deployment_id = %s
                 AND is_suppressed = FALSE
                 AND posted_at >= NOW() - INTERVAL '30 days'""",
            (domain, deployment_id),
        )
        columns = [desc[0] for desc in cur.description]
        jobs = [dict(zip(columns, row)) for row in cur.fetchall()]

        if not jobs:
            continue

        company_name = jobs[0].get("company", domain)

        # Score each dimension
        d1, d1_reason = _score_ai_signal(jobs)
        d2, d2_reason = _score_urgency(jobs)
        d3, d3_reason = _score_icp_fit(jobs, domain)
        d4, d4_reason = _score_tech_signals(jobs)
        d5, d5_reason = _score_engagement(domain, deployment_id, cur)

        # Weighted total (scale to 0-15 range for tier thresholds)
        raw_weighted = (
            d1 * WEIGHTS["ai_signal"]
            + d2 * WEIGHTS["urgency"]
            + d3 * WEIGHTS["icp_fit"]
            + d4 * WEIGHTS["tech_signals"]
            + d5 * WEIGHTS["engagement"]
        )
        # Scale: max raw = 3.0, scale to 15
        total_score = round(raw_weighted * 5)

        tier = _assign_tier(total_score)

        rationale = (
            f"D1 AI Signal ({d1}/3): {d1_reason}. "
            f"D2 Urgency ({d2}/3): {d2_reason}. "
            f"D3 ICP Fit ({d3}/3): {d3_reason}. "
            f"D4 Tech ({d4}/3): {d4_reason}. "
            f"D5 Engagement ({d5}/3): {d5_reason}. "
            f"Weighted total: {total_score}/15 -> {tier}"
        )

        signals = [d1_reason, d2_reason, d3_reason, d4_reason, d5_reason]

        # Check previous tier
        cur.execute(
            "SELECT tier FROM company_scores_a WHERE company_domain = %s ORDER BY tier_assigned_at DESC LIMIT 1",
            (domain,),
        )
        prev = cur.fetchone()
        previous_tier = prev[0] if prev else None
        tier_changed = previous_tier is not None and previous_tier != tier

        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=TIER_EXPIRY_DAYS)

        cur.execute(
            """INSERT INTO company_scores_a
               (company_name, company_domain, dimension_1_score, dimension_2_score,
                dimension_3_score, dimension_4_score, dimension_5_score,
                total_score, tier, scoring_rationale, key_signals,
                tier_assigned_at, tier_expires_at, previous_tier, tier_changed,
                deployment_id, region)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                company_name, domain, d1, d2, d3, d4, d5,
                total_score, tier, rationale, signals,
                now, expires, previous_tier, tier_changed,
                deployment_id, region,
            ),
        )
        conn.commit()
        scored += 1

    conn.close()
    print(f"Approach A: scored {scored} companies")
    return scored


def main():
    parser = argparse.ArgumentParser(description="Agent 12 — Approach A Scoring")
    parser.add_argument("--deployment", default="cfa-seattle-bd")
    parser.add_argument("--region", default="Greater Seattle")
    args = parser.parse_args()

    print(f"Approach A Scoring — {datetime.now(timezone.utc).isoformat()}")
    print(f"Deployment: {args.deployment} | Region: {args.region}")
    score_companies(args.deployment, args.region)


if __name__ == "__main__":
    main()
