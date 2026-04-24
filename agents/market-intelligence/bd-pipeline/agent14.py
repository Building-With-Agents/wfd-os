"""
Agent 14 — Contact Discovery Agent (Runtime Harness)

Goal: Find the best contact at every Hot and Warm company —
the operational leader who would buy Waifinder's agentic data
engineering consulting services.

Never leave a Hot or Warm company without a contact attempt.
Always find something — a verified email, a name and title,
a LinkedIn URL — even if the full picture is not available.

Five-step discovery strategy:
1. Apollo domain search
2. Apollo organization name search
3. Web search for leadership (Gemini + Google Search)
4. Hunter.io email finder
5. LinkedIn URL construction

Usage:
    python agent14.py --deployment waifinder-national --hot-warm-only --verbose
    python agent14.py --deployment waifinder-national --domain example.org
"""
import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone
from urllib.parse import quote_plus

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../apollo"))
import psycopg2
from pgconfig import PG_CONFIG
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"), override=True)

import requests as http_requests
from client import search_contacts_by_domain, search_contacts_by_name
from hunter_client import find_email as hunter_find_email

# ============================================================
# CONFIG
# ============================================================

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

HUNTER_ENABLED = bool(os.getenv("HUNTER_API_KEY"))
if not HUNTER_ENABLED:
    print("[AGENT14] Hunter.io not configured — using web search for emails only")

MAX_RETRIES = 2
BASE_DELAY = 2
INTER_CALL_DELAY = 1.5

BUYER_TITLES = [
    "executive director",
    "chief executive officer",
    "CEO", "COO", "CIO",
    "director of operations",
    "director of technology",
    "VP of strategy",
    "managing partner",
    "president",
    "practice administrator",
    "deputy director",
    "chief operating officer",
    "chief information officer",
]

TITLE_PRIORITY = {
    "executive director": 1,
    "chief executive officer": 2, "ceo": 2,
    "chief operating officer": 3, "coo": 3,
    "chief information officer": 4, "cio": 4,
    "director of operations": 5,
    "director of technology": 6,
    "vp": 7, "vice president": 7,
    "managing partner": 8,
    "practice administrator": 9,
    "deputy director": 10,
    "president": 11,
    "commissioner": 12,
    "technology officer": 13,
    "director": 14,
    "manager": 15,
}


def _title_score(title):
    """Score a title against buyer profile. Lower = better match."""
    if not title:
        return 999
    t = title.lower()
    for keyword, score in TITLE_PRIORITY.items():
        if keyword in t:
            return score
    return 999


def _pick_best_contact(contacts, recommended_buyer):
    """Pick best contact from a list using title scoring."""
    if not contacts:
        return None

    # Boost contacts matching recommended_buyer
    scored = []
    for c in contacts:
        title = c.get("title") or ""
        base_score = _title_score(title)

        # Boost if matches recommended buyer
        if recommended_buyer:
            buyer_words = [w.lower() for w in recommended_buyer.split() if len(w) > 3]
            if any(w in title.lower() for w in buyer_words):
                base_score -= 50

        # Penalize if no email
        if not c.get("email"):
            base_score += 100

        scored.append((base_score, c))

    scored.sort(key=lambda x: x[0])
    return scored[0][1]


def _call_gemini(prompt, retries=MAX_RETRIES):
    """Call Gemini REST API with Google Search grounding."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1},
    }

    for attempt in range(retries):
        try:
            resp = http_requests.post(url, json=payload, timeout=120)

            if resp.status_code == 429:
                time.sleep(BASE_DELAY * (2 ** (attempt + 1)))
                continue

            if resp.status_code != 200:
                if attempt < retries - 1:
                    time.sleep(BASE_DELAY)
                continue

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return None, 0

            text = ""
            for part in candidates[0].get("content", {}).get("parts", []):
                if "text" in part:
                    text += part["text"]

            text = text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])

            tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)
            return json.loads(text), tokens

        except json.JSONDecodeError:
            if attempt < retries - 1:
                time.sleep(BASE_DELAY)
        except Exception as e:
            print(f"      Gemini error: {e}")
            if attempt < retries - 1:
                time.sleep(BASE_DELAY)

    return None, 0


def _construct_linkedin_url(first_name, last_name):
    """Construct likely LinkedIn URL from name."""
    if not first_name or not last_name:
        return None
    slug = f"{first_name.lower().strip()}-{last_name.lower().strip()}"
    slug = slug.replace(" ", "-")
    return f"https://linkedin.com/in/{slug}"


def _construct_linkedin_search_url(company_name, title):
    """Construct LinkedIn search URL for Jason to use."""
    keywords = quote_plus(company_name)
    title_param = quote_plus(title) if title else ""
    return f"https://linkedin.com/search/results/people/?keywords={keywords}&titleFreeText={title_param}"


# ============================================================
# Five-Step Discovery Strategy
# ============================================================

def web_search_leadership(company_name, domain, recommended_buyer, verbose=False):
    """Step 3: Use Gemini + web search to find leadership."""
    prompt = f"""Search the web for the leadership team at {company_name} ({domain}).

I need to find their {recommended_buyer or 'Executive Director or equivalent operational leader'}.

Search for:
1. "{company_name} leadership team"
2. "{company_name} executive director"
3. "{company_name} about us staff"
4. "site:linkedin.com {company_name} executive director"
5. "{company_name} contact email {recommended_buyer or 'executive director'}"

IMPORTANT: Many nonprofits, government agencies, and healthcare organizations publish contact emails on their About Us page, leadership page, staff directory, or in press releases. Look for published email addresses for the person you find.

Return the best match as JSON:
{{
  "found": true,
  "name": "full name",
  "first_name": "first name",
  "last_name": "last name",
  "title": "exact title from source",
  "email": "email address if publicly published, or null if not found",
  "source": "URL where found",
  "confidence": "High|Medium|Low"
}}

Only return someone with budget authority — not junior staff, board members, or volunteers.
If not found return {{"found": false}}
Return ONLY the JSON. No markdown fences."""

    result, tokens = _call_gemini(prompt)
    if verbose:
        print(f"      Web search tokens: {tokens}")

    if result is None:
        return None

    # Handle case where Gemini returns a list instead of dict
    if isinstance(result, list):
        result = result[0] if result else None
    if result and isinstance(result, dict) and result.get("found"):
        return result
    return None


def discover_contact(company, verbose=False):
    """Main five-step discovery strategy for a single company."""
    domain = company["company_domain"]
    name = company["company_name"]
    recommended_buyer = company.get("recommended_buyer") or "Executive Director"
    tier = company.get("tier", "")

    result = {
        "company_domain": domain,
        "company_name": name,
        "company_tier": tier,
        "recommended_buyer": recommended_buyer,
        "match_confidence": "Partial",
        "discovery_source": "manual_needed",
        "discovery_notes": "",
        "contact_name": None,
        "contact_title": None,
        "contact_email": None,
        "contact_linkedin": None,
        "apollo_contact_id": None,
        "apollo_account_id": None,
        "pipeline_stage": "Identified",
    }

    steps_tried = []

    # ---- Step 1: Apollo domain search ----
    if verbose:
        print(f"    Step 1: Apollo domain search ({domain})")
    apollo_result = search_contacts_by_domain(domain, BUYER_TITLES)
    steps_tried.append("apollo_domain")

    if apollo_result.get("ok") and apollo_result.get("contacts"):
        contacts = apollo_result["contacts"]
        if verbose:
            print(f"      Found {len(contacts)} contacts")
        best = _pick_best_contact(contacts, recommended_buyer)
        if best and best.get("email"):
            result.update({
                "contact_name": best["name"],
                "contact_title": best.get("title"),
                "contact_email": best["email"],
                "contact_linkedin": best.get("linkedin_url"),
                "apollo_contact_id": best.get("id"),
                "apollo_account_id": best.get("account_id"),
                "match_confidence": "High",
                "discovery_source": "apollo",
                "discovery_notes": f"Found via Apollo domain search: {best.get('title')}",
            })
            if verbose:
                print(f"      -> HIGH: {best['name']}, {best.get('title')}, {best['email']}")
            return result
        elif best:
            # Partial — name but no email, continue to try for email
            result.update({
                "contact_name": best["name"],
                "contact_title": best.get("title"),
                "contact_linkedin": best.get("linkedin_url"),
                "apollo_contact_id": best.get("id"),
                "apollo_account_id": best.get("account_id"),
            })
            if verbose:
                print(f"      Partial: {best['name']}, {best.get('title')} (no email)")
    elif verbose:
        print(f"      No results")

    time.sleep(0.5)

    # ---- Step 2: Apollo organization name search ----
    if verbose:
        print(f"    Step 2: Apollo name search ({name})")
    apollo_name_result = search_contacts_by_name(name, BUYER_TITLES)
    steps_tried.append("apollo_name")

    if apollo_name_result.get("ok") and apollo_name_result.get("contacts"):
        contacts = apollo_name_result["contacts"]
        if verbose:
            print(f"      Found {len(contacts)} contacts")
        best = _pick_best_contact(contacts, recommended_buyer)
        if best and best.get("email"):
            result.update({
                "contact_name": best["name"],
                "contact_title": best.get("title"),
                "contact_email": best["email"],
                "contact_linkedin": best.get("linkedin_url"),
                "apollo_contact_id": best.get("id"),
                "apollo_account_id": best.get("account_id"),
                "match_confidence": "High",
                "discovery_source": "apollo",
                "discovery_notes": f"Found via Apollo name search: {best.get('title')}",
            })
            if verbose:
                print(f"      -> HIGH: {best['name']}, {best.get('title')}, {best['email']}")
            return result
        elif best and not result.get("contact_name"):
            result.update({
                "contact_name": best["name"],
                "contact_title": best.get("title"),
                "contact_linkedin": best.get("linkedin_url"),
                "apollo_contact_id": best.get("id"),
            })
            if verbose:
                print(f"      Partial: {best['name']}, {best.get('title')} (no email)")
    elif verbose:
        print(f"      No results")

    time.sleep(0.5)

    # ---- Step 3: Web search for leadership ----
    if verbose:
        print(f"    Step 3: Web search for leadership")
    web_candidate = web_search_leadership(name, domain, recommended_buyer, verbose)
    steps_tried.append("web_search")

    if web_candidate:
        first_name = web_candidate.get("first_name", "")
        last_name = web_candidate.get("last_name", "")
        web_title = web_candidate.get("title", "")
        web_source = web_candidate.get("source", "")
        web_email = web_candidate.get("email")

        result.update({
            "contact_name": web_candidate.get("name"),
            "contact_title": web_title,
            "discovery_source": "web_research",
            "discovery_notes": f"Found via web: {web_title} (source: {web_source})",
        })

        if verbose:
            print(f"      Found: {web_candidate.get('name')}, {web_title}")
            if web_email:
                print(f"      Email from web: {web_email}")

        # If web search found a published email, use it
        if web_email:
            result.update({
                "contact_email": web_email,
                "match_confidence": "High",
                "discovery_source": "web_research",
                "discovery_notes": f"Name and email found via web search: {web_title}, {web_email} (source: {web_source})",
            })
            if verbose:
                print(f"      -> HIGH: {web_email} (from public web source)")
            return result

        # ---- Step 4: Hunter.io email search (only if HUNTER_ENABLED) ----
        if first_name and last_name and HUNTER_ENABLED:
            if verbose:
                print(f"    Step 4: Hunter.io email search ({first_name} {last_name} @ {domain})")
            steps_tried.append("hunter")

            hunter_result = hunter_find_email(domain, first_name, last_name)

            if hunter_result.get("ok") and hunter_result.get("email"):
                result.update({
                    "contact_email": hunter_result["email"],
                    "match_confidence": "High" if hunter_result.get("confidence", 0) >= 80 else "Medium",
                    "discovery_source": "hunter",
                    "discovery_notes": f"Name from web ({web_source}), email from Hunter.io (confidence: {hunter_result.get('confidence', 0)}%)",
                })
                if verbose:
                    print(f"      -> {result['match_confidence']}: {hunter_result['email']} (conf: {hunter_result.get('confidence')}%)")
                return result
            elif verbose:
                print(f"      No email found: {hunter_result.get('error', 'unknown')}")
        elif verbose and not HUNTER_ENABLED:
            print(f"    Step 4: Skipped (Hunter.io not configured)")

        # ---- Step 5: LinkedIn URL construction ----
        if verbose:
            print(f"    Step 5: LinkedIn URL construction")
        steps_tried.append("linkedin_construct")

        linkedin = _construct_linkedin_url(first_name, last_name) if first_name and last_name else None
        result.update({
            "contact_linkedin": linkedin or result.get("contact_linkedin"),
            "match_confidence": "Low",
            "discovery_notes": (
                f"Name found: {web_candidate.get('name')}, {web_title}. "
                f"No verified email. "
                f"LinkedIn URL constructed — needs verification. "
                f"Source: {web_source}"
            ),
        })
        if verbose:
            print(f"      -> LOW: {linkedin}")
        return result
    elif verbose:
        print(f"      No candidates found via web search")

    # ---- Fallback: Partial result ----
    steps_tried.append("fallback")
    search_url = _construct_linkedin_search_url(name, recommended_buyer)
    result["discovery_notes"] = (
        f"No contact found via {', '.join(steps_tried)}. "
        f"Recommend searching LinkedIn for: {recommended_buyer} at {name}. "
        f"LinkedIn search: {search_url}"
    )
    if verbose:
        print(f"    -> PARTIAL: {search_url}")

    return result


# ============================================================
# Database Operations
# ============================================================

def get_uncontacted_companies(cur, deployment_id, hot_warm_only=True):
    """Get Hot/Warm companies not yet in hot_warm_contacts."""
    tier_filter = "AND cs.tier IN ('Hot', 'Warm')" if hot_warm_only else ""
    cur.execute(
        f"""SELECT DISTINCT ON (cs.company_domain)
                   cs.company_domain, cs.company_name, cs.tier,
                   cs.recommended_buyer, cs.scoring_rationale
            FROM company_scores cs
            WHERE cs.deployment_id = %s
              {tier_filter}
              AND cs.company_domain NOT IN (
                  SELECT company_domain FROM hot_warm_contacts
                  WHERE company_domain IS NOT NULL
              )
            ORDER BY cs.company_domain, cs.tier_assigned_at DESC""",
        (deployment_id,),
    )
    columns = [desc[0] for desc in cur.description]
    return [dict(zip(columns, row)) for row in cur.fetchall()]


def write_contact(cur, conn, result):
    """Write contact discovery result to hot_warm_contacts."""
    cur.execute(
        """INSERT INTO hot_warm_contacts
           (company_domain, company_name, company_tier,
            apollo_contact_id, contact_name, contact_title,
            contact_email, contact_linkedin, apollo_account_id,
            recommended_buyer, match_confidence,
            discovery_source, discovery_notes, pipeline_stage)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            result["company_domain"], result["company_name"], result["company_tier"],
            result.get("apollo_contact_id"), result.get("contact_name"),
            result.get("contact_title"), result.get("contact_email"),
            result.get("contact_linkedin"), result.get("apollo_account_id"),
            result.get("recommended_buyer"), result["match_confidence"],
            result["discovery_source"], result["discovery_notes"],
            result.get("pipeline_stage", "Identified"),
        ),
    )
    conn.commit()


# ============================================================
# Main Runner
# ============================================================

def run_agent14(deployment_id, hot_warm_only=True, verbose=False, domain_filter=None):
    """Find contacts for all Hot/Warm companies not yet contacted."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    if domain_filter:
        # Score a specific domain
        cur.execute(
            """SELECT DISTINCT ON (company_domain)
                      company_domain, company_name, tier,
                      recommended_buyer, scoring_rationale
               FROM company_scores
               WHERE company_domain = %s
               ORDER BY company_domain, tier_assigned_at DESC""",
            (domain_filter,),
        )
        columns = [desc[0] for desc in cur.description]
        companies = [dict(zip(columns, row)) for row in cur.fetchall()]
    else:
        companies = get_uncontacted_companies(cur, deployment_id, hot_warm_only)

    print(f"\nAgent 14: Finding contacts for {len(companies)} companies")

    results = {"High": [], "Medium": [], "Low": [], "Partial": []}
    total_tokens = 0

    for i, company in enumerate(companies):
        print(f"\n  [{i + 1}/{len(companies)}] {company['company_name']} ({company['company_domain']}) [{company['tier']}]")

        contact = discover_contact(company, verbose)
        write_contact(cur, conn, contact)

        confidence = contact["match_confidence"]
        results[confidence].append({
            "company": contact["company_name"],
            "domain": contact["company_domain"],
            "tier": contact["company_tier"],
            "name": contact.get("contact_name"),
            "title": contact.get("contact_title"),
            "email": contact.get("contact_email"),
            "source": contact["discovery_source"],
            "notes": contact["discovery_notes"],
        })

        # Teams alert for High + Hot only
        if confidence == "High" and contact["company_tier"] == "Hot":
            _send_contact_alert(contact)

        time.sleep(INTER_CALL_DELAY)

    conn.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"Agent 14 Contact Discovery Complete")
    print(f"{'='*60}")
    print(f"  High confidence:   {len(results['High'])}")
    print(f"  Medium confidence: {len(results['Medium'])}")
    print(f"  Low confidence:    {len(results['Low'])}")
    print(f"  Partial (manual):  {len(results['Partial'])}")

    if results["High"]:
        print(f"\n  High Confidence Contacts:")
        for r in results["High"]:
            print(f"    [{r['tier']}] {r['company']} -> {r['name']}, {r['title']} <{r['email']}>")

    if results["Low"]:
        print(f"\n  Low Confidence (name, no email):")
        for r in results["Low"]:
            print(f"    [{r['tier']}] {r['company']} -> {r['name']}, {r['title']}")

    if results["Partial"]:
        print(f"\n  Partial (needs Jason):")
        for r in results["Partial"]:
            print(f"    [{r['tier']}] {r['company']} — {r['notes'][:100]}")

    return results


def _send_contact_alert(contact):
    """Send Teams alert for High confidence Hot company contact."""
    from notify import _post_adaptive_card

    card_body = [
        {"type": "TextBlock", "text": "\U0001f464 Contact Found", "weight": "Bolder", "size": "Large"},
        {"type": "FactSet", "facts": [
            {"title": "Company", "value": f"{contact['company_name']} ({contact['company_tier']})"},
            {"title": "Contact", "value": f"{contact.get('contact_name')}, {contact.get('contact_title')}"},
            {"title": "Email", "value": contact.get("contact_email", "N/A")},
            {"title": "LinkedIn", "value": contact.get("contact_linkedin", "N/A")},
            {"title": "Source", "value": contact["discovery_source"]},
            {"title": "Confidence", "value": contact["match_confidence"]},
        ]},
        {"type": "TextBlock", "text": "Ready for Agent 13 distribution.", "wrap": True, "isSubtle": True},
    ]

    _post_adaptive_card(card_body, f"Contact Found: {contact['company_name']}")


def main():
    parser = argparse.ArgumentParser(description="Agent 14 — Contact Discovery Agent")
    parser.add_argument("--deployment", default="waifinder-national")
    parser.add_argument("--hot-warm-only", action="store_true", default=True)
    parser.add_argument("--all-tiers", action="store_true")
    parser.add_argument("--domain", default=None, help="Score specific domain")
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    hot_warm = not args.all_tiers

    print(f"Agent 14 — Contact Discovery — {datetime.now(timezone.utc).isoformat()}")
    print(f"Deployment: {args.deployment}")
    run_agent14(args.deployment, hot_warm, args.verbose, args.domain)


if __name__ == "__main__":
    main()
