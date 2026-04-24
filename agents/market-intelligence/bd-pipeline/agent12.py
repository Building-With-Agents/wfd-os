"""
Agent 12 — Lead Intelligence Agent (Runtime Harness)

Gemini does the reasoning. This file:
1. Reads ICP definition from icp_definitions table
2. Reads scoring_feedback for unprocessed records
3. For each non-suppressed company in prospect_companies:
   - Pulls job posting data from jobs_enriched
   - Pulls prior score from company_scores if exists
   - Calls Gemini with web search grounding
   - Validates response
   - Writes to company_scores
   - Writes Apollo tier tag
   - Logs token usage
4. Sends escalation alerts for tier changes

Usage:
    python agent12.py
    python agent12.py --deployment waifinder-national --limit 3
"""
import os
import sys
import json
import time
import argparse
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../apollo"))
import psycopg2
from pgconfig import PG_CONFIG
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"), override=True)

import google.generativeai as genai

genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

# ============================================================
# CONFIG
# ============================================================

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
TIER_EXPIRY_DAYS = 7
VALID_TIERS = {"Hot", "Warm", "Monitor", "Suppressed"}
VALID_CONFIDENCE = {"High", "Medium", "Low"}

MAX_RETRIES = 3
BASE_DELAY = 3
INTER_CALL_DELAY = 2

SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "agent12_system.txt")


def _read_system_prompt():
    """Read Agent 12 system prompt from file."""
    with open(SYSTEM_PROMPT_PATH, "r") as f:
        return f.read()


def _read_icp_definition(cur, deployment_id):
    """Read current ICP definition from database."""
    cur.execute(
        """SELECT definition FROM icp_definitions
           WHERE deployment_id = %s
           ORDER BY updated_at DESC LIMIT 1""",
        (deployment_id,),
    )
    row = cur.fetchone()
    if not row:
        raise ValueError(f"No ICP definition found for deployment {deployment_id}")
    return row[0]


def _read_unprocessed_feedback(cur):
    """Read unprocessed scoring feedback."""
    cur.execute(
        """SELECT company_domain, engagement_type, tier_at_engagement,
                  converted_to_conversation, engaged_at
           FROM scoring_feedback
           WHERE feedback_processed = FALSE
           ORDER BY created_at DESC
           LIMIT 100"""
    )
    rows = cur.fetchall()
    feedback = []
    for domain, eng_type, tier, converted, engaged_at in rows:
        feedback.append({
            "company_domain": domain,
            "engagement_type": eng_type,
            "tier_at_engagement": tier,
            "converted": converted,
            "engaged_at": str(engaged_at) if engaged_at else None,
        })
    return feedback


def _get_company_jobs(cur, domain):
    """Get job posting data for a company from jobs_enriched."""
    cur.execute(
        """SELECT job_id, title, company, company_domain, posted_at,
                  repost_count, is_ai_role, is_data_role, is_workforce_role,
                  seniority, job_description, job_highlights, location
           FROM jobs_enriched
           WHERE company_domain = %s
             AND is_suppressed = FALSE
           ORDER BY posted_at DESC
           LIMIT 20""",
        (domain,),
    )
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def _get_prior_score(cur, domain):
    """Get most recent prior score for a company."""
    cur.execute(
        """SELECT tier, confidence, scoring_rationale, key_signals,
                  tier_assigned_at
           FROM company_scores
           WHERE company_domain = %s
           ORDER BY tier_assigned_at DESC LIMIT 1""",
        (domain,),
    )
    row = cur.fetchone()
    if row:
        return {
            "tier": row[0],
            "confidence": row[1],
            "rationale": row[2],
            "signals": row[3],
            "scored_at": str(row[4]) if row[4] else None,
        }
    return None


def _get_domain_feedback(cur, domain):
    """Get engagement feedback for a specific domain."""
    cur.execute(
        """SELECT engagement_type, tier_at_engagement, converted_to_conversation,
                  engaged_at
           FROM scoring_feedback
           WHERE company_domain = %s
           ORDER BY created_at DESC LIMIT 10""",
        (domain,),
    )
    return [
        {
            "type": row[0],
            "tier": row[1],
            "converted": row[2],
            "date": str(row[3]) if row[3] else None,
        }
        for row in cur.fetchall()
    ]


def _build_scoring_prompt(company_name, domain, jobs, prior_score, feedback, icp_definition):
    """Build the prompt for Gemini scoring."""
    # Job summaries
    job_summaries = []
    for j in jobs:
        desc = (j.get("job_description") or "")[:600]
        job_summaries.append(
            f"- Title: {j.get('title')}\n"
            f"  Location: {j.get('location')}\n"
            f"  Posted: {j.get('posted_at')}\n"
            f"  Repost count: {j.get('repost_count', 0)}\n"
            f"  AI role: {j.get('is_ai_role')}, Data role: {j.get('is_data_role')}, "
            f"Workforce role: {j.get('is_workforce_role')}\n"
            f"  Seniority: {j.get('seniority')}\n"
            f"  Description: {desc}"
        )
    jobs_text = "\n\n".join(job_summaries) if job_summaries else "No job postings found in our database."

    # Prior score context
    prior_text = "No prior score."
    if prior_score:
        prior_text = (
            f"Prior tier: {prior_score['tier']} ({prior_score['confidence']})\n"
            f"Scored at: {prior_score['scored_at']}\n"
            f"Rationale: {prior_score['rationale']}"
        )

    # Engagement feedback
    feedback_text = "No engagement history."
    if feedback:
        lines = [
            f"- {f['type']} (tier: {f['tier']}, converted: {f['converted']}, date: {f['date']})"
            for f in feedback
        ]
        feedback_text = "\n".join(lines)

    return f"""Score this company as a Waifinder consulting prospect.

ICP DEFINITION (read carefully — this is your scoring rubric):
{icp_definition}

COMPANY TO SCORE:
Company: {company_name}
Domain: {domain}

JOB POSTINGS FROM OUR DATABASE:
{jobs_text}

PRIOR SCORE:
{prior_text}

ENGAGEMENT HISTORY:
{feedback_text}

INSTRUCTIONS:
1. Use web search to research this company thoroughly following the research process in the ICP definition.
2. Look for the specific signals described in the ICP definition.
3. Check for disqualifying signals.
4. Return your assessment as JSON matching the output format in the ICP definition.
5. Your scoring_rationale must cite specific evidence from your research. Name sources.
6. Include sources_consulted listing what you actually searched.
7. Include research_gaps listing what you could not find.

Return ONLY valid JSON. No markdown fences."""


def _call_gemini(system_prompt, user_prompt, retries=MAX_RETRIES):
    """Call Gemini via REST API with Google Search grounding and exponential backoff."""
    import requests as http_req

    api_key = os.getenv("GEMINI_API_KEY")
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={api_key}"

    payload = {
        "system_instruction": {
            "parts": [{"text": system_prompt}]
        },
        "contents": [
            {"role": "user", "parts": [{"text": user_prompt}]}
        ],
        "tools": [{"google_search": {}}],
        "generationConfig": {
            "temperature": 0.2,
        },
    }

    for attempt in range(retries):
        try:
            resp = http_req.post(url, json=payload, timeout=120)

            if resp.status_code == 429:
                delay = BASE_DELAY * (2 ** (attempt + 1))
                print(f"    Rate limited (attempt {attempt + 1}), waiting {delay}s")
                time.sleep(delay)
                continue

            if resp.status_code != 200:
                print(f"    API error (attempt {attempt + 1}): {resp.status_code} {resp.text[:200]}")
                if attempt < retries - 1:
                    time.sleep(BASE_DELAY)
                continue

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                print(f"    No candidates (attempt {attempt + 1})")
                continue

            text = ""
            for part in candidates[0].get("content", {}).get("parts", []):
                if "text" in part:
                    text += part["text"]

            text = text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])

            result = json.loads(text)

            # Token usage
            usage = data.get("usageMetadata", {})
            tokens = usage.get("totalTokenCount", 0)

            return result, tokens

        except json.JSONDecodeError as e:
            print(f"    JSON parse error (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                time.sleep(BASE_DELAY * (2 ** attempt))
        except Exception as e:
            print(f"    Error (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                time.sleep(BASE_DELAY)

    return None, 0


def _write_apollo_tier_tag(domain, tier):
    """Write tier tag to Apollo account record."""
    try:
        import requests
        api_key = os.getenv("APOLLO_API_KEY", "")
        if not api_key:
            return

        headers = {
            "X-Api-Key": api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

        # Search for account by domain
        resp = requests.post(
            "https://api.apollo.io/v1/accounts/search",
            headers=headers,
            json={"q_organization_domains": domain, "per_page": 1},
            timeout=15,
        )
        if resp.status_code == 200:
            accounts = resp.json().get("accounts", [])
            if accounts:
                account_id = accounts[0].get("id")
                # Update account with tier label
                update_resp = requests.put(
                    f"https://api.apollo.io/v1/accounts/{account_id}",
                    headers=headers,
                    json={"label_names": [f"Waifinder-{tier}"]},
                    timeout=15,
                )
                if update_resp.status_code == 200:
                    print(f"    Apollo: tagged {domain} as Waifinder-{tier}")
                    return account_id
                else:
                    print(f"    Apollo: tag update failed ({update_resp.status_code})")
            else:
                print(f"    Apollo: no account found for {domain}")
        else:
            print(f"    Apollo: search failed ({resp.status_code})")
    except Exception as e:
        print(f"    Apollo: error — {e}")
    return None


def score_companies(deployment_id, region, limit=None):
    """Score all non-suppressed companies via Agent 12."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Step 1: Read ICP definition
    print("Reading ICP definition from database...")
    icp_definition = _read_icp_definition(cur, deployment_id)
    print(f"  ICP definition: {len(icp_definition)} chars")

    # Step 2: Read system prompt
    system_prompt = _read_system_prompt()
    print(f"  System prompt: {len(system_prompt)} chars")

    # Step 3: Read unprocessed feedback
    feedback = _read_unprocessed_feedback(cur)
    print(f"  Unprocessed feedback records: {len(feedback)}")

    # Step 4: Get companies to score (skip already-scored in this run)
    cur.execute(
        """SELECT pc.company_domain, pc.company_name
           FROM prospect_companies pc
           WHERE pc.is_suppressed = FALSE
             AND pc.deployment_id = %s
             AND pc.company_domain NOT IN (
                 SELECT company_domain FROM company_scores
                 WHERE tier_assigned_at > NOW() - INTERVAL '7 days'
             )
           ORDER BY pc.entry_date DESC""",
        (deployment_id,),
    )
    companies = cur.fetchall()
    if limit:
        companies = companies[:limit]
    print(f"\nScoring {len(companies)} companies via Agent 12 (Gemini + web search)")

    scored = 0
    flagged = 0
    escalated = 0
    total_tokens = 0

    for i, (domain, company_name) in enumerate(companies):
        print(f"\n  [{i + 1}/{len(companies)}] {company_name} ({domain})")

        # Get job data
        jobs = _get_company_jobs(cur, domain)
        prior_score = _get_prior_score(cur, domain)
        domain_feedback = _get_domain_feedback(cur, domain)

        # Build prompt
        user_prompt = _build_scoring_prompt(
            company_name, domain, jobs, prior_score, domain_feedback, icp_definition
        )

        # Call Gemini
        result, tokens = _call_gemini(system_prompt, user_prompt)
        total_tokens += tokens

        if result is None:
            print(f"    FLAGGED: no valid response from Gemini")
            flagged += 1
            continue

        # Validate tier
        tier = result.get("tier", "")
        if tier not in VALID_TIERS:
            print(f"    FLAGGED: invalid tier '{tier}'")
            flagged += 1
            continue

        confidence = result.get("confidence", "Low")
        if confidence not in VALID_CONFIDENCE:
            confidence = "Low"

        # Check for tier change
        previous_tier = prior_score["tier"] if prior_score else None
        tier_changed = previous_tier is not None and previous_tier != tier

        now = datetime.now(timezone.utc)
        expires = now + timedelta(days=TIER_EXPIRY_DAYS)

        # Write to company_scores
        apollo_account_id = None
        cur.execute(
            """INSERT INTO company_scores
               (company_name, company_domain, apollo_account_id,
                tier, confidence, confidence_rationale, scoring_rationale,
                key_signals, disqualifying_signals,
                recommended_buyer, recommended_content,
                sources_consulted, research_gaps,
                fragmented_data_evidence, technology_ambition_evidence,
                execution_gap_evidence,
                tier_assigned_at, tier_expires_at,
                previous_tier, tier_changed, gemini_tokens_used,
                deployment_id, region)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (
                company_name, domain, apollo_account_id,
                tier, confidence,
                result.get("confidence_rationale", ""),
                result.get("scoring_rationale", ""),
                result.get("key_signals", []),
                result.get("disqualifying_signals", []),
                result.get("recommended_buyer", ""),
                result.get("recommended_content", ""),
                result.get("sources_consulted", []),
                result.get("research_gaps", ""),
                result.get("fragmented_data_evidence"),
                result.get("technology_ambition_evidence"),
                result.get("execution_gap_evidence"),
                now, expires,
                previous_tier, tier_changed, tokens,
                deployment_id, region,
            ),
        )
        conn.commit()
        scored += 1

        if tier_changed:
            escalated += 1

        print(f"    -> {tier} ({confidence}) | tokens: {tokens}")
        if result.get("scoring_rationale"):
            rationale_preview = result["scoring_rationale"][:150]
            print(f"    Rationale: {rationale_preview}...")
        if result.get("key_signals"):
            print(f"    Signals: {result['key_signals'][:3]}")
        if result.get("fragmented_data_evidence"):
            print(f"    Fragmented Data: {result['fragmented_data_evidence'][:120]}")
        if result.get("technology_ambition_evidence"):
            print(f"    Tech Ambition: {result['technology_ambition_evidence'][:120]}")
        if result.get("execution_gap_evidence"):
            print(f"    Execution Gap: {result['execution_gap_evidence'][:120]}")
        if result.get("sources_consulted"):
            print(f"    Sources: {result['sources_consulted']}")

        # Write Apollo tier tag
        apollo_id = _write_apollo_tier_tag(domain, tier)
        if apollo_id:
            cur.execute(
                "UPDATE company_scores SET apollo_account_id = %s WHERE company_domain = %s AND tier_assigned_at = %s",
                (apollo_id, domain, now),
            )
            conn.commit()

        # Rate limit
        if i < len(companies) - 1:
            time.sleep(INTER_CALL_DELAY)

    # Mark feedback as processed
    if feedback:
        cur.execute("UPDATE scoring_feedback SET feedback_processed = TRUE WHERE feedback_processed = FALSE")
        conn.commit()
        print(f"\nMarked {len(feedback)} feedback records as processed")

    conn.close()

    print(f"\n{'='*50}")
    print(f"Agent 12 Scoring Complete")
    print(f"  Scored:    {scored}")
    print(f"  Flagged:   {flagged}")
    print(f"  Escalated: {escalated}")
    print(f"  Tokens:    {total_tokens:,}")
    print(f"{'='*50}")

    return {
        "scored": scored,
        "flagged": flagged,
        "escalated": escalated,
        "total_tokens": total_tokens,
    }


def main():
    parser = argparse.ArgumentParser(description="Agent 12 — Lead Intelligence Agent")
    parser.add_argument("--deployment", default="waifinder-national")
    parser.add_argument("--region", default="Greater Seattle")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of companies to score (for testing)")
    args = parser.parse_args()

    print(f"Agent 12 — {datetime.now(timezone.utc).isoformat()}")
    print(f"Deployment: {args.deployment} | Region: {args.region}")
    if args.limit:
        print(f"Limit: {args.limit} companies")
    score_companies(args.deployment, args.region, args.limit)


if __name__ == "__main__":
    main()
