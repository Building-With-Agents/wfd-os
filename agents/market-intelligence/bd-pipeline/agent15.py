"""
Agent 15 — Market Discovery Agent (Runtime Harness)

Finds mid-market organizations pursuing digital transformation
that lack the technical capacity to execute. Feeds prospect_companies
for Agent 12 to score.

Runs daily at 4am PST — before Agent 12 at 5am.

Uses Gemini + Google Search grounding for discovery and evaluation.

Usage:
    python agent15.py
    python agent15.py --deployment waifinder-national --limit 5
    python agent15.py --weekly-summary
"""
import os
import sys
import json
import time
import re
import argparse
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
import psycopg2
from pgconfig import PG_CONFIG
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"), override=True)

import requests as http_requests

# ============================================================
# CONFIG
# ============================================================

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MAX_RETRIES = 3
BASE_DELAY = 3
INTER_CALL_DELAY = 2.5

SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "agent15_system.txt")

# --- Search queries organized by dimension ---

DIMENSION_1_VERTICAL = [
    "workforce development digital transformation 2025 2026",
    "community health center digital transformation",
    "FQHC digital transformation data",
    "workforce board technology modernization",
    "nonprofit operations digital transformation",
    "county government digital transformation plan",
    "regional healthcare digital transformation",
    "legal services digital transformation",
    "professional services firm digital transformation operations",
    "apprenticeship program digital transformation",
]

DIMENSION_2_STRUGGLE = [
    "digital transformation data integration challenges organization",
    "digital transformation slower than expected nonprofit",
    "digital transformation lessons learned mid-market",
    "digital transformation stalled organization 2025",
    "digital transformation fragmented systems challenge",
    "manual processes digital transformation nonprofit operations",
    "data silos digital transformation healthcare nonprofit",
]

DIMENSION_3_GEOGRAPHY = [
    "Washington State digital transformation organization 2025 2026",
    "Texas nonprofit digital transformation",
    "Seattle mid-market digital transformation",
    "Texas workforce board technology modernization",
    "Pacific Northwest organization digital transformation",
    "Texas healthcare clinic digital transformation",
]

DIMENSION_4_CONFIRMATION = [
    "digital transformation grant awarded nonprofit 2025 2026",
    "digital transformation new CIO hired organization",
    "digital transformation strategic plan workforce board",
    "technology modernization grant workforce development",
    "HRSA digital transformation health center grant",
    "WIOA technology innovation workforce",
    "digital transformation annual report nonprofit operations",
]

ALL_DIMENSIONS = {
    "vertical": DIMENSION_1_VERTICAL,
    "struggle": DIMENSION_2_STRUGGLE,
    "geography": DIMENSION_3_GEOGRAPHY,
    "confirmation": DIMENSION_4_CONFIRMATION,
}

# Fast-filter suppression keywords in company names
SUPPRESS_NAME_KEYWORDS = {
    "consulting", "solutions", "agency", "vendor", "software",
    "tech ", "systems", "it services", "digital agency",
    "technologies", "saas", "platform",
}


def _read_system_prompt():
    with open(SYSTEM_PROMPT_PATH, "r") as f:
        return f.read()


def _get_existing_domains(cur):
    """Get all domains already in prospect_companies."""
    cur.execute("SELECT company_domain FROM prospect_companies WHERE company_domain IS NOT NULL")
    return {row[0] for row in cur.fetchall()}


def _should_suppress_name(name):
    """Fast filter — suppress obvious vendors by name."""
    name_lower = name.lower()
    return any(kw in name_lower for kw in SUPPRESS_NAME_KEYWORDS)


def _extract_domain(url):
    """Extract clean domain from a URL."""
    if not url:
        return None
    try:
        if not url.startswith("http"):
            url = "https://" + url
        parsed = urlparse(url)
        domain = parsed.netloc or parsed.path
        domain = domain.lower()
        domain = re.sub(r"^www\.", "", domain)
        domain = domain.rstrip("/")
        return domain if domain and "." in domain else None
    except Exception:
        return None


def _call_gemini_search(query, system_prompt, retries=MAX_RETRIES):
    """Call Gemini with Google Search grounding to find organizations."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    search_prompt = f"""Search for: {query}

Find specific organizations (not articles about the topic) that are pursuing digital transformation.

For each organization found, extract:
- Organization name
- Domain (website URL)
- What specific digital transformation signal you found
- Source URL where the signal was found

Return a JSON array of objects:
[
  {{
    "name": "Organization Name",
    "domain": "example.org",
    "signal": "Specific digital transformation signal found",
    "source_url": "URL where this was found"
  }}
]

Only include organizations that:
- Are real, specific organizations (not categories or lists)
- Have a website domain you can identify
- Show genuine digital transformation activity (not marketing/vendor content)
- Are NOT technology companies, consulting firms, or software vendors

Return ONLY the JSON array. No markdown fences. If no qualifying organizations found, return an empty array []."""

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": search_prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1},
    }

    for attempt in range(retries):
        try:
            resp = http_requests.post(url, json=payload, timeout=120)

            if resp.status_code == 429:
                delay = BASE_DELAY * (2 ** (attempt + 1))
                print(f"      Rate limited, waiting {delay}s")
                time.sleep(delay)
                continue

            if resp.status_code != 200:
                print(f"      API error: {resp.status_code}")
                if attempt < retries - 1:
                    time.sleep(BASE_DELAY)
                continue

            data = resp.json()
            candidates = data.get("candidates", [])
            if not candidates:
                return [], 0

            text = ""
            for part in candidates[0].get("content", {}).get("parts", []):
                if "text" in part:
                    text += part["text"]

            text = text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])

            tokens = data.get("usageMetadata", {}).get("totalTokenCount", 0)

            try:
                results = json.loads(text)
                if isinstance(results, list):
                    return results, tokens
                return [], tokens
            except json.JSONDecodeError:
                return [], tokens

        except Exception as e:
            print(f"      Search error (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                time.sleep(BASE_DELAY)

    return [], 0


def _call_gemini_evaluate(name, domain, signal, source_url, system_prompt, retries=MAX_RETRIES):
    """Call Gemini to evaluate a candidate organization."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    eval_prompt = f"""Evaluate this organization as a potential Waifinder prospect.

Waifinder builds agentic data engineering systems for mid-market organizations that are pursuing digital transformation but lack the technical capacity to execute fully. We connect fragmented systems, automate manual workflows, and build intelligence layers on top of operational data.

Organization: {name}
Domain: {domain}
Signal found: {signal}
Source: {source_url}

Evaluate on four dimensions:

ONE: Transformation type
Is this organization showing:
- Vendor: they sell transformation — suppress immediately
- Aspiration: stated intent, no action yet
- In-progress: active initiatives underway
- Struggling: started and hitting walls

TWO: Execution gap evidence
What specifically suggests they cannot build this themselves?

THREE: Budget capacity
What confirms they have money to spend?

FOUR: Size and vertical fit
- Estimated employee count — must be 20-1,000
- Vertical — workforce, healthcare, legal, nonprofit, government, professional_services, or other
- Not a technology company
- Not an individual practice

Return JSON:
{{
  "assessment": "yes|no|maybe",
  "transformation_type": "vendor|aspiration|in-progress|struggling",
  "signal_strength": "High|Medium|Low",
  "vertical": "workforce|healthcare|legal|nonprofit|government|professional_services|other",
  "execution_gap_evidence": "one sentence or null",
  "budget_evidence": "one sentence or null",
  "estimated_size": "20-50|50-200|200-500|500-1000|unknown",
  "key_signal": "one sentence — the most compelling evidence",
  "discovery_source": "signal type",
  "suppress_reason": "null or reason if no"
}}

Return ONLY the JSON. No markdown fences."""

    payload = {
        "system_instruction": {"parts": [{"text": system_prompt}]},
        "contents": [{"role": "user", "parts": [{"text": eval_prompt}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.1},
    }

    for attempt in range(retries):
        try:
            resp = http_requests.post(url, json=payload, timeout=120)

            if resp.status_code == 429:
                delay = BASE_DELAY * (2 ** (attempt + 1))
                time.sleep(delay)
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
            print(f"      Eval error (attempt {attempt + 1}): {e}")
            if attempt < retries - 1:
                time.sleep(BASE_DELAY)

    return None, 0


def _select_daily_queries(day_of_week):
    """Select 10-15 queries rotating across dimensions so none goes unsearched > 2 days."""
    queries = []
    dims = list(ALL_DIMENSIONS.keys())

    # Primary dimension rotates daily
    primary = dims[day_of_week % len(dims)]
    secondary = dims[(day_of_week + 1) % len(dims)]

    # 5-6 from primary, 3-4 from secondary, 2-3 from others
    primary_qs = ALL_DIMENSIONS[primary]
    secondary_qs = ALL_DIMENSIONS[secondary]
    other_dims = [d for d in dims if d not in (primary, secondary)]

    queries.extend(primary_qs[:6])
    queries.extend(secondary_qs[:4])
    for d in other_dims:
        queries.extend(ALL_DIMENSIONS[d][:2])

    return queries, primary


def run_discovery(deployment_id, limit=None):
    """Run the daily discovery pipeline."""
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    system_prompt = _read_system_prompt()
    existing_domains = _get_existing_domains(cur)
    print(f"  Existing domains in pipeline: {len(existing_domains)}")

    # Select today's queries
    day_of_week = datetime.now().weekday()
    queries, primary_dim = _select_daily_queries(day_of_week)
    if limit:
        queries = queries[:limit]
    print(f"  Running {len(queries)} searches (primary dimension: {primary_dim})")

    total_found = 0
    total_added = 0
    total_suppressed = 0
    total_duplicate = 0
    total_tokens = 0
    added_companies = []
    search_results_by_pattern = {}

    for i, query in enumerate(queries):
        print(f"\n  [{i + 1}/{len(queries)}] Searching: {query}")

        candidates, search_tokens = _call_gemini_search(query, system_prompt)
        total_tokens += search_tokens

        if not candidates:
            print(f"    No candidates found")
            search_results_by_pattern[query] = {"found": 0, "added": 0}
            time.sleep(INTER_CALL_DELAY)
            continue

        print(f"    Found {len(candidates)} candidates")
        total_found += len(candidates)
        pattern_added = 0

        for cand in candidates:
            name = cand.get("name", "")
            domain = _extract_domain(cand.get("domain", ""))
            signal = cand.get("signal", "")
            source_url = cand.get("source_url", "")

            if not name or not domain:
                continue

            # Fast filter: already in pipeline
            if domain in existing_domains:
                total_duplicate += 1
                continue

            # Fast filter: vendor name
            if _should_suppress_name(name):
                total_suppressed += 1
                print(f"    SUPPRESS (name filter): {name}")
                continue

            # Evaluate with Gemini
            print(f"    Evaluating: {name} ({domain})")
            result, eval_tokens = _call_gemini_evaluate(
                name, domain, signal, source_url, system_prompt
            )
            total_tokens += eval_tokens
            time.sleep(INTER_CALL_DELAY)

            if result is None:
                print(f"      No valid evaluation")
                continue

            assessment = result.get("assessment", "no")
            transformation_type = result.get("transformation_type", "")

            # Filter vendors and hard no's
            if assessment == "no" or transformation_type == "vendor":
                suppress_reason = result.get("suppress_reason") or "vendor/no assessment"
                total_suppressed += 1
                print(f"      SUPPRESS: {suppress_reason}")
                continue

            # Write to prospect_companies
            key_signal = result.get("key_signal", signal)
            vertical = result.get("vertical", "other")
            signal_strength = result.get("signal_strength", "Low")
            estimated_size = result.get("estimated_size", "unknown")

            try:
                cur.execute(
                    """INSERT INTO prospect_companies
                       (company_name, company_domain, entry_source,
                        discovery_signal, discovery_source_url,
                        transformation_type, signal_strength,
                        vertical, estimated_size,
                        deployment_id, region)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                       ON CONFLICT (company_domain) DO NOTHING""",
                    (
                        name, domain, "market_discovery_agent",
                        key_signal, source_url,
                        transformation_type, signal_strength,
                        vertical, estimated_size,
                        deployment_id, None,
                    ),
                )
                if cur.rowcount > 0:
                    total_added += 1
                    pattern_added += 1
                    existing_domains.add(domain)
                    added_companies.append({
                        "name": name,
                        "domain": domain,
                        "type": transformation_type,
                        "signal": key_signal,
                        "vertical": vertical,
                        "strength": signal_strength,
                    })
                    print(f"      ADDED: {transformation_type} | {vertical} | {signal_strength}")
                else:
                    total_duplicate += 1
            except Exception as e:
                print(f"      DB error: {e}")

        search_results_by_pattern[query] = {"found": len(candidates), "added": pattern_added}

    conn.close()

    # Summary
    print(f"\n{'='*60}")
    print(f"Market Discovery Complete")
    print(f"{'='*60}")
    print(f"  Searches run:    {len(queries)}")
    print(f"  Candidates found: {total_found}")
    print(f"  Added to pipeline: {total_added}")
    print(f"  Duplicates:      {total_duplicate}")
    print(f"  Suppressed:      {total_suppressed}")
    print(f"  Gemini tokens:   {total_tokens:,}")

    if added_companies:
        print(f"\n  New Discoveries:")
        for c in added_companies:
            print(f"    [{c['type']}] {c['name']} ({c['domain']}) — {c['signal'][:80]}")

    # Best/worst patterns
    best = max(search_results_by_pattern.items(), key=lambda x: x[1]["added"], default=None)
    worst = min(
        ((k, v) for k, v in search_results_by_pattern.items() if v["found"] > 0),
        key=lambda x: x[1]["added"],
        default=None,
    )
    if best:
        print(f"\n  Best search pattern: '{best[0]}' ({best[1]['added']} added)")
    if worst:
        print(f"  Worst search pattern: '{worst[0]}' ({worst[1]['added']} added from {worst[1]['found']} found)")

    return {
        "found": total_found,
        "added": total_added,
        "suppressed": total_suppressed,
        "duplicates": total_duplicate,
        "tokens": total_tokens,
        "companies": added_companies,
        "patterns": search_results_by_pattern,
    }


def weekly_summary(deployment_id):
    """Calculate weekly performance and send Teams summary."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    week_end = datetime.now(timezone.utc).date()
    week_start = week_end - timedelta(days=7)

    # Total discovered this week
    cur.execute(
        """SELECT COUNT(*) FROM prospect_companies
           WHERE entry_source = 'market_discovery_agent'
             AND deployment_id = %s
             AND entry_date >= %s""",
        (deployment_id, week_start),
    )
    total_discovered = cur.fetchone()[0]

    # How Agent 12 scored our discoveries
    cur.execute(
        """SELECT cs.tier, COUNT(*)
           FROM company_scores cs
           JOIN prospect_companies pc ON cs.company_domain = pc.company_domain
           WHERE pc.entry_source = 'market_discovery_agent'
             AND pc.deployment_id = %s
           GROUP BY cs.tier""",
        (deployment_id,),
    )
    scores = dict(cur.fetchall())

    # By transformation type
    cur.execute(
        """SELECT transformation_type, COUNT(*)
           FROM prospect_companies
           WHERE entry_source = 'market_discovery_agent'
             AND deployment_id = %s
             AND entry_date >= %s
           GROUP BY transformation_type""",
        (deployment_id, week_start),
    )
    by_type = dict(cur.fetchall())

    # By vertical
    cur.execute(
        """SELECT vertical, COUNT(*)
           FROM prospect_companies
           WHERE entry_source = 'market_discovery_agent'
             AND deployment_id = %s
             AND entry_date >= %s
           GROUP BY vertical""",
        (deployment_id, week_start),
    )
    by_vertical = dict(cur.fetchall())

    # Top discoveries
    cur.execute(
        """SELECT pc.company_name, pc.discovery_signal
           FROM prospect_companies pc
           LEFT JOIN company_scores cs ON pc.company_domain = cs.company_domain
           WHERE pc.entry_source = 'market_discovery_agent'
             AND pc.deployment_id = %s
             AND pc.entry_date >= %s
           ORDER BY
             CASE cs.tier WHEN 'Hot' THEN 1 WHEN 'Warm' THEN 2 ELSE 3 END,
             pc.entry_date DESC
           LIMIT 3""",
        (deployment_id, week_start),
    )
    top_discoveries = cur.fetchall()

    # Write to discovery_performance
    cur.execute(
        """INSERT INTO discovery_performance
           (week_start, week_end, total_discovered,
            scored_hot, scored_warm, scored_monitor, scored_suppressed,
            by_vertical, by_transformation_type,
            deployment_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (
            week_start, week_end, total_discovered,
            scores.get("Hot", 0), scores.get("Warm", 0),
            scores.get("Monitor", 0), scores.get("Suppressed", 0),
            json.dumps(by_vertical), json.dumps(by_type),
            deployment_id,
        ),
    )

    conn.close()

    # Print summary
    print(f"\n{'='*60}")
    print(f"MARKET DISCOVERY WEEKLY SUMMARY")
    print(f"{'='*60}")
    print(f"  New companies discovered: {total_discovered}")
    print(f"\n  Breakdown by transformation type:")
    for t in ["struggling", "in-progress", "aspiration"]:
        print(f"    {t}: {by_type.get(t, 0)}")
    print(f"\n  By vertical:")
    for v in ["workforce", "healthcare", "nonprofit", "government", "legal", "professional_services", "other"]:
        cnt = by_vertical.get(v, 0)
        if cnt:
            print(f"    {v}: {cnt}")
    if top_discoveries:
        print(f"\n  Top discoveries this week:")
        for name, signal in top_discoveries:
            sig_preview = (signal or "")[:80]
            print(f"    {name} — {sig_preview}")
    print(f"\n  Agent 12 scores on our discoveries:")
    print(f"    Hot: {scores.get('Hot', 0)} | Warm: {scores.get('Warm', 0)} | "
          f"Monitor: {scores.get('Monitor', 0)} | Suppressed: {scores.get('Suppressed', 0)}")

    # Build Teams notification
    from notify import _post_adaptive_card

    card_body = [
        {"type": "TextBlock", "text": "\U0001f50d Market Discovery Weekly Summary",
         "weight": "Bolder", "size": "Large"},
        {"type": "TextBlock", "text": f"New companies discovered: {total_discovered}", "wrap": True},
        {"type": "TextBlock", "text": "**By transformation type:**", "wrap": True},
        {"type": "TextBlock", "text": f"  Struggling: {by_type.get('struggling', 0)}", "wrap": True},
        {"type": "TextBlock", "text": f"  In-progress: {by_type.get('in-progress', 0)}", "wrap": True},
        {"type": "TextBlock", "text": f"  Aspiration: {by_type.get('aspiration', 0)}", "wrap": True},
        {"type": "TextBlock", "text": "**Agent 12 scores on discoveries:**", "wrap": True},
        {"type": "TextBlock",
         "text": f"  Hot: {scores.get('Hot', 0)} | Warm: {scores.get('Warm', 0)} | "
                 f"Monitor: {scores.get('Monitor', 0)} | Suppressed: {scores.get('Suppressed', 0)}",
         "wrap": True},
    ]

    if top_discoveries:
        card_body.append({"type": "TextBlock", "text": "**Top discoveries:**", "wrap": True})
        for name, signal in top_discoveries:
            card_body.append({
                "type": "TextBlock",
                "text": f"  {name} — {(signal or '')[:80]}",
                "wrap": True,
                "size": "Small",
            })

    card_body.append({
        "type": "TextBlock",
        "text": "Agent 12 scores all new discoveries at 5am Monday.",
        "wrap": True,
        "isSubtle": True,
    })

    _post_adaptive_card(card_body, "Market Discovery Weekly Summary")

    return {
        "discovered": total_discovered,
        "scored": scores,
        "by_type": by_type,
        "by_vertical": by_vertical,
    }


def main():
    parser = argparse.ArgumentParser(description="Agent 15 — Market Discovery Agent")
    parser.add_argument("--deployment", default="waifinder-national")
    parser.add_argument("--limit", type=int, default=None,
                        help="Limit number of search queries (for testing)")
    parser.add_argument("--weekly-summary", action="store_true",
                        help="Run weekly performance summary")
    args = parser.parse_args()

    print(f"Agent 15 — Market Discovery — {datetime.now(timezone.utc).isoformat()}")
    print(f"Deployment: {args.deployment}")

    if args.weekly_summary:
        weekly_summary(args.deployment)
    else:
        run_discovery(args.deployment, args.limit)


if __name__ == "__main__":
    main()
