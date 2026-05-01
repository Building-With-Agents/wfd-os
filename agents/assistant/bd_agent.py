"""BD Agent — Jason's BD Command Center Assistant.

Helps Jason work the Waifinder BD pipeline. Reads from company_scores,
hot_warm_contacts, warm_signals, distribution_log, email_sequences.
Synthesizes Agent 12/13/14/15 intelligence into actionable answers.

Never sends emails or contacts prospects directly — drafts only.
"""
from __future__ import annotations
import os
import sys
import json
import re
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import google.generativeai as genai

from agents.assistant.base import BaseAgent, Tool

# Import shared db config
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts"))
try:
    from pgconfig import PG_CONFIG
except Exception:
    PG_CONFIG = {
        "host": "127.0.0.1",
        "database": "wfd_os",
        "user": "postgres",
        "password": os.getenv("PG_PASSWORD", "wfdos2026"),
        "port": 5432,
    }

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
if os.getenv("GEMINI_API_KEY"):
    genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


SYSTEM_PROMPT = """You are Jason's BD Assistant for Waifinder.

ABOUT WAIFINDER — READ THIS CAREFULLY, NEVER FORGET IT
Waifinder is the consulting brand of Computing for All. Waifinder sells
CONSULTING ENGAGEMENTS ONLY. There is no "workforce product," no "platform
product," no productized offering of any kind. The consulting engagement IS
the product. Every engagement is a custom build: data engineering, data
integration, agentic AI systems, labor market intelligence platforms. Some
engagements focus on workforce data (like the Borderplex labor market
intelligence platform we already built), but these are still bespoke
consulting builds, not a shelf product.

If Jason or anyone refers to a "workforce product" or "consulting product,"
correct the framing gently and clarify: "Waifinder doesn't have a separate
product — everything is consulting. Here's how I'd split these prospects by
focus area instead..."

ABOUT JASON
Jason is the BD lead. He uses Microsoft 365 and LinkedIn for outreach
execution. He is not technical. He wants short, specific, actionable answers
with numbers — not theory.

YOUR JOB
You give Jason the intelligence he needs — which prospects are worth his
time and exactly what to say to them. You surface intelligence and draft
outreach. You never contact anyone.

CORE RULES

1. COUNT BEFORE YOU DEFEND. When Jason challenges the pipeline composition
   ("there are a lot of workforce boards", "why are there so many X?"), your
   FIRST action is to call categorize_prospects or get_hot_warm_prospects
   and count the actual numbers. Only then can you answer. Never agree with
   a framing without checking it against real data. If the data contradicts
   Jason, say so directly.

1a. NEVER INVENT NUMBERS. Every count you quote to Jason MUST come directly
   from a tool response. Specifically, categorize_prospects returns a
   "headline" field with the exact totals — quote it verbatim. Do not
   estimate, round, or recompute counts. If you find yourself guessing a
   number, stop and call the tool again. Wrong numbers are worse than no
   numbers.

2. NEVER ASK FOR A DOMAIN. When Jason names a company ("Mountain West
   Conference", "Food & Friends"), never ask him for the domain. Call
   find_company_by_name first to resolve the name to a domain, then use
   that domain with other tools. Jason should never need to know a
   prospect's domain.

3. PICK ONE WHEN ASKED FOR A SAMPLE. If Jason asks for "a sample," "an
   example," "show me some messaging," or "what does the messaging look
   like" — pick one prospect yourself (preferably the top Hot one with a
   draft already generated) and show it. Do not ask him to choose. The
   whole point of the assistant is to save him clicks.

4. SHOW REAL DRAFTS, NOT GENERATED SAMPLES. When Jason asks to see
   messaging, always pull the actual Touch 1 body from email_sequences via
   list_email_drafts or get_email_draft — these are the real drafts that
   will actually go out. Do not generate a new sample email unless he
   explicitly asks you to generate one.

5. WORKFORCE BOARDS ARE CONTENT TARGETS, NOT CONSULTING PROSPECTS.
   Workforce development boards (WIOA agencies, regional workforce boards,
   one-stop centers) typically cannot buy $50K-$500K consulting engagements
   — their budgets are constrained by federal grant rules. Treat them as
   "content distribution targets" — useful for getting workforce-project
   case studies in front of their network for relationship and referral
   value, but NOT as direct consulting leads. Flag them that way in your
   answers. This is Jason's explicit business judgment — honor it.

6. ALWAYS END WITH ONE CLEAR NEXT ACTION. Every response should end with
   "Next action: <one specific thing Jason should do>". Not two things.
   One thing. Specific. Actionable in under 60 seconds.

7. BE CONCISE. Bullet points beat paragraphs. Numbers beat adjectives.
   Cite sources briefly in parens — "(source: company_scores)" — not in
   verbose technical language.

8. DRAFTS ONLY. You never send emails or contact anyone. If Jason asks you
   to send something, the best you can do is point him at the Approve &
   Send button in the dashboard. The dashboard is the only place a real
   email leaves his account.

TOOL STRATEGY (when to call what)

MANDATORY: call categorize_prospects BEFORE answering ANY of these:
  - "which are good consulting clients"
  - "consulting vs product/workforce/something else"
  - "how many prospects are <type>"
  - "which are weak fits"
  - "is this by design?"
  - "categorize my prospects"
  - "what's the pipeline composition"
  - anything that asks about prospect counts, verticals, or categorization

After calling categorize_prospects, your response MUST include the exact
numbers from the "headline" field of the tool result. Quote the headline
as a bold one-line summary at the top of your answer. Do NOT paraphrase
the numbers, do NOT round, do NOT add or subtract. Example:

    **9 Hot/Warm prospects total. 7 strong consulting fits, 1 weak
    consulting fit, 1 content distribution target.**

If you output different numbers from what the headline says, you are
lying to Jason.

Other tool routing:
- "What should I work on today?" → get_hot_warm_prospects + get_warm_signals
- "Tell me about <company name>" → find_company_by_name THEN get_prospect_details
- "Show me the messaging for <company>" → find_company_by_name THEN get_email_draft
- "Show me a sample" / "show me some messaging" → list_email_drafts → pick the top Hot one → show its touch_1_body verbatim
- "Where are my prospects in the pipeline?" → get_pipeline_summary
- "Generate a LinkedIn note for <company>" → find_company_by_name THEN generate_linkedin_note
- "Draft an opening line for <company>" → find_company_by_name THEN generate_email_opening
- "Who at <company> should I contact?" → find_company_by_name THEN get_prospect_details"""


def _conn():
    return psycopg2.connect(**PG_CONFIG)


def _query(sql, params=None):
    """Run a SELECT and return list of dicts."""
    conn = _conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute(sql, params or ())
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.isoformat()
        return rows
    finally:
        conn.close()


def _execute(sql, params=None):
    conn = _conn()
    cur = conn.cursor()
    try:
        cur.execute(sql, params or ())
        conn.commit()
        return cur.rowcount
    finally:
        conn.close()


# ============================================================
# Classification helpers — workforce board / county / nonprofit / healthcare / etc.
# ============================================================

# Patterns for classifying prospects into verticals and consulting-fit buckets
WORKFORCE_BOARD_PATTERNS = [
    r"\bemploy\b",  # "Employ Prince George's" etc
    r"workforce\s+(development|board|investment|solutions|services)\s+(board|council|agency)?",
    r"\bwib\b",  # workforce investment board
    r"workforce\s+development\s+area",
    r"one[- ]stop",
]

COUNTY_GOV_PATTERNS = [
    r"county\s+of\s+",
    r"\bcounty\s+government\b",
    r"\bcounty\b",  # weaker but catches "Carroll County Government"
]

FQHC_HEALTHCARE_PATTERNS = [
    r"federally\s+qualified",
    r"\bfqhc\b",
    r"community\s+health",
    r"health\s+services",
    r"health\s+center",
    r"health\s+clinic",
    r"children'?s\s+hospital",
]

NONPROFIT_PATTERNS = [
    r"\bfoundation\b",
    r"\bnonprofit\b",
    r"\b501\(c\)\b",
]

MEDIA_PATTERNS = [
    r"\btimes\b",
    r"\bpost\b",
    r"\bjournal\b",
    r"\bnews\b",
    r"\bmedia\b",
    r"\bpublisher\b",
]


def _classify_company(name: str, domain: str, scoring_rationale: str = "") -> dict:
    """Classify a company into vertical + consulting-fit bucket using name,
    domain, and scoring rationale text. Returns:
        {
          "vertical": "workforce_board" | "county_gov" | "nonprofit" |
                      "healthcare" | "media" | "commercial" | "other",
          "consulting_fit": "strong" | "weak" | "distribution_target",
          "reason": "one sentence"
        }
    """
    text = f"{name} {domain} {scoring_rationale}".lower()

    # Workforce boards first (most specific — and they're distribution targets)
    for pat in WORKFORCE_BOARD_PATTERNS:
        if re.search(pat, text):
            return {
                "vertical": "workforce_board",
                "consulting_fit": "distribution_target",
                "reason": "Workforce boards rarely buy $50K+ consulting due to federal grant budget constraints. Use for workforce-project content distribution instead.",
            }

    # County/local government
    for pat in COUNTY_GOV_PATTERNS:
        if re.search(pat, text):
            return {
                "vertical": "county_gov",
                "consulting_fit": "weak",
                "reason": "County governments have longer procurement cycles but can be consulting fits for IT/data modernization budgets. Needs patient outreach.",
            }

    # FQHC / healthcare clinic
    for pat in FQHC_HEALTHCARE_PATTERNS:
        if re.search(pat, text):
            return {
                "vertical": "healthcare",
                "consulting_fit": "strong",
                "reason": "FQHCs and community health orgs have real data integration pain and grant/HRSA budget capacity — strong consulting fits.",
            }

    # Media
    for pat in MEDIA_PATTERNS:
        if re.search(pat, text):
            return {
                "vertical": "media",
                "consulting_fit": "strong",
                "reason": "Media companies have unified-data-platform needs and discretionary tech budgets — strong consulting fits.",
            }

    # Nonprofit (generic, catch after healthcare/media)
    for pat in NONPROFIT_PATTERNS:
        if re.search(pat, text):
            return {
                "vertical": "nonprofit",
                "consulting_fit": "strong",
                "reason": "Mid-market nonprofits with operational data pain and grant funding are strong consulting fits.",
            }

    # Default
    return {
        "vertical": "commercial_or_other",
        "consulting_fit": "strong",
        "reason": "Commercial mid-market with operational data needs — evaluate case-by-case.",
    }


# ============================================================
# Tools
# ============================================================

def _find_company_by_name(name: str) -> dict:
    """Resolve a company name to its domain + latest tier + basic details.

    Supports partial matches: 'Mountain West' finds 'Mountain West Conference'.
    Returns up to 5 candidates using the MOST RECENT score per domain.
    """
    rows = _query(
        """WITH latest AS (
               SELECT DISTINCT ON (company_domain)
                      company_name, company_domain, tier, confidence, tier_assigned_at
               FROM company_scores
               ORDER BY company_domain, tier_assigned_at DESC
           )
           SELECT * FROM latest
           WHERE LOWER(company_name) LIKE LOWER(%s)
              OR LOWER(company_domain) LIKE LOWER(%s)
           ORDER BY tier_assigned_at DESC
           LIMIT 5""",
        (f"%{name}%", f"%{name}%"),
    )
    if not rows:
        return {
            "source": "company_scores",
            "query": name,
            "matches": [],
            "note": f"No company found matching '{name}'. Try get_hot_warm_prospects to see all companies, or check spelling.",
        }
    return {
        "source": "company_scores",
        "query": name,
        "matches": rows,
        "best_match": rows[0],
    }


def _list_email_drafts(include_sent: bool = False) -> dict:
    """List all email drafts across all companies with their status and
    which touch is currently up for review.
    """
    if include_sent:
        where = ""
    else:
        where = "WHERE sequence_status = 'pending_review'"
    rows = _query(
        f"""SELECT id, company_name, company_domain, contact_name, contact_email,
                   sender, subject_line,
                   COALESCE(current_touch, 1) as current_touch,
                   touch_1_body, touch_2_body, touch_3_body,
                   sequence_status, touch_1_sent_at, touch_2_sent_at, touch_3_sent_at,
                   created_at
           FROM email_sequences
           {where}
           ORDER BY created_at DESC"""
    )
    # Get scoring info for context
    for r in rows:
        score = _query(
            """SELECT tier, confidence, recommended_buyer
               FROM company_scores
               WHERE company_domain = %s
               ORDER BY tier_assigned_at DESC LIMIT 1""",
            (r["company_domain"],),
        )
        if score:
            r["tier"] = score[0]["tier"]
            r["confidence"] = score[0]["confidence"]
        else:
            r["tier"] = None
    return {
        "source": "email_sequences",
        "count": len(rows),
        "drafts": rows,
    }


def _get_email_draft(company_name_or_domain: str) -> dict:
    """Get the current email draft for a specific company by name OR domain.

    Resolves name → domain first if needed, then returns the draft with
    the body for whichever touch is currently up for review.
    """
    # First try as a domain
    rows = _query(
        """SELECT id, company_name, company_domain, contact_name, contact_email,
                  sender, subject_line,
                  COALESCE(current_touch, 1) as current_touch,
                  touch_1_body, touch_2_body, touch_3_body,
                  sequence_status, touch_1_sent_at, touch_2_sent_at, touch_3_sent_at
           FROM email_sequences
           WHERE company_domain = %s
              OR LOWER(company_name) LIKE LOWER(%s)
           ORDER BY created_at DESC
           LIMIT 1""",
        (company_name_or_domain, f"%{company_name_or_domain}%"),
    )
    if not rows:
        return {
            "source": "email_sequences",
            "query": company_name_or_domain,
            "error": f"No email draft found for '{company_name_or_domain}'. Check list_email_drafts for the full list.",
        }
    r = rows[0]
    # Return the body for the current touch
    ct = r.get("current_touch") or 1
    body_field = f"touch_{ct}_body"
    r["current_body"] = r.get(body_field) or r.get("touch_1_body")
    r["current_subject"] = r["subject_line"] if ct == 1 else f"Re: {r['subject_line']}"
    return {
        "source": "email_sequences",
        "draft": r,
    }


def _categorize_prospects() -> dict:
    """Count Hot/Warm prospects by vertical and consulting-fit bucket.

    Returns counts + a per-prospect list with classification. Use this
    whenever Jason challenges the pipeline composition.

    IMPORTANT: Uses the MOST RECENT scoring per company, not the first
    Hot/Warm row found. This prevents stale "Hot" rows from showing up
    after a re-score demoted the company to Warm/Monitor/Suppressed.
    """
    rows = _query(
        """WITH latest AS (
               SELECT DISTINCT ON (company_domain)
                      company_name, company_domain, tier, confidence,
                      recommended_buyer, scoring_rationale
               FROM company_scores
               ORDER BY company_domain, tier_assigned_at DESC
           )
           SELECT * FROM latest
           WHERE tier IN ('Hot', 'Warm')
           ORDER BY
             CASE tier WHEN 'Hot' THEN 1 WHEN 'Warm' THEN 2 ELSE 3 END,
             company_name"""
    )

    by_vertical = {}
    by_fit = {"strong": [], "weak": [], "distribution_target": []}
    classified = []

    for r in rows:
        cls = _classify_company(r["company_name"], r["company_domain"], r.get("scoring_rationale") or "")
        r["vertical"] = cls["vertical"]
        r["consulting_fit"] = cls["consulting_fit"]
        r["fit_reason"] = cls["reason"]

        by_vertical.setdefault(cls["vertical"], 0)
        by_vertical[cls["vertical"]] += 1
        by_fit[cls["consulting_fit"]].append({
            "company": r["company_name"],
            "domain": r["company_domain"],
            "tier": r["tier"],
        })
        classified.append({
            "company": r["company_name"],
            "domain": r["company_domain"],
            "tier": r["tier"],
            "vertical": cls["vertical"],
            "consulting_fit": cls["consulting_fit"],
            "reason": cls["reason"],
        })

    # EXACT counts — agent MUST use these literal numbers in any response.
    # Do not let the LLM hallucinate totals. Include a headline string the
    # LLM can quote verbatim to guarantee numeric accuracy.
    n_strong = len(by_fit["strong"])
    n_weak = len(by_fit["weak"])
    n_dist = len(by_fit["distribution_target"])
    total = len(rows)

    # The headline is what the agent MUST quote. Keep it clean — no meta
    # instructions inside the string itself. The "must quote verbatim" rule
    # lives in the system prompt, not in the tool output.
    headline = (
        f"{total} Hot/Warm prospects total. "
        f"{n_strong} strong consulting fits, "
        f"{n_weak} weak consulting fit{'' if n_weak == 1 else 's'}, "
        f"{n_dist} content distribution target{'' if n_dist == 1 else 's'}."
    )

    return {
        "headline": headline,
        "source": "company_scores + _classify_company",
        "total_hot_warm_prospects": total,
        "count_strong_consulting_fits": n_strong,
        "count_weak_consulting_fits": n_weak,
        "count_content_distribution_targets": n_dist,
        "by_vertical": by_vertical,
        "strong_consulting_prospects": by_fit["strong"],
        "weak_consulting_prospects": by_fit["weak"],
        "content_distribution_targets": by_fit["distribution_target"],
        "full_list": classified,
    }


def _get_pipeline_summary() -> dict:
    """Get pipeline summary — all contacts grouped by stage with company tier."""
    rows = _query(
        """SELECT hwc.id, hwc.company_name, hwc.company_domain,
                  hwc.contact_name, hwc.contact_title, hwc.contact_email,
                  hwc.company_tier, hwc.match_confidence,
                  COALESCE(hwc.pipeline_stage, 'Identified') as pipeline_stage,
                  hwc.found_at
           FROM hot_warm_contacts hwc
           ORDER BY
             CASE COALESCE(hwc.pipeline_stage, 'Identified')
               WHEN 'Identified' THEN 1
               WHEN 'LinkedIn Sent' THEN 2
               WHEN 'LinkedIn Connected' THEN 3
               WHEN 'Email Sent' THEN 4
               WHEN 'Replied' THEN 5
               WHEN 'Conversation' THEN 6
               WHEN 'Proposal' THEN 7
               WHEN 'Client' THEN 8
               ELSE 9
             END,
             hwc.company_tier, hwc.found_at DESC"""
    )
    stages = {}
    for r in rows:
        stage = r["pipeline_stage"]
        stages.setdefault(stage, []).append(r)
    return {
        "source": "hot_warm_contacts",
        "total_contacts": len(rows),
        "by_stage": {k: len(v) for k, v in stages.items()},
        "contacts_by_stage": stages,
    }


def _get_hot_warm_prospects() -> dict:
    """Return all Hot and Warm companies using MOST RECENT scoring.

    Uses the latest score per company — a re-score that demotes a company
    to Monitor/Suppressed correctly removes it from Jason's Hot/Warm list.
    """
    rows = _query(
        """WITH latest AS (
               SELECT DISTINCT ON (company_domain)
                      company_name, company_domain, tier, confidence,
                      fragmented_data_evidence, technology_ambition_evidence,
                      execution_gap_evidence, recommended_buyer, recommended_content,
                      scoring_rationale, key_signals, tier_assigned_at
               FROM company_scores
               ORDER BY company_domain, tier_assigned_at DESC
           )
           SELECT * FROM latest
           WHERE tier IN ('Hot', 'Warm')
           ORDER BY
             CASE tier WHEN 'Hot' THEN 1 WHEN 'Warm' THEN 2 ELSE 3 END,
             company_name"""
    )
    return {
        "source": "company_scores",
        "count": len(rows),
        "prospects": rows,
    }


def _get_warm_signals(unacted_only: bool = True) -> dict:
    where = "WHERE converted_to_conversation = FALSE" if unacted_only else ""
    rows = _query(
        f"""SELECT id, company_name, company_domain, contact_name, contact_title,
                   signal_type, signal_detail, priority, company_tier_at_signal,
                   detected_at, alert_sent
            FROM warm_signals
            {where}
            ORDER BY
              CASE priority WHEN 'Immediate' THEN 1 WHEN 'High' THEN 2 ELSE 3 END,
              detected_at DESC
            LIMIT 50"""
    )
    return {
        "source": "warm_signals",
        "count": len(rows),
        "signals": rows,
    }


def _get_prospect_details(company_name_or_domain: str) -> dict:
    """Synthesize all data we have on a single company.

    Accepts EITHER a company name or a domain. Never asks Jason to provide
    a domain — always resolves the name internally.
    """
    # If it doesn't look like a domain, resolve by name first
    looks_like_domain = "." in company_name_or_domain and " " not in company_name_or_domain
    if not looks_like_domain:
        lookup = _find_company_by_name(company_name_or_domain)
        if not lookup.get("matches"):
            return {"error": f"No company found matching '{company_name_or_domain}'. Try list_email_drafts or get_hot_warm_prospects to see options."}
        domain = lookup["best_match"]["company_domain"]
    else:
        domain = company_name_or_domain

    score = _query(
        """SELECT * FROM company_scores
           WHERE company_domain = %s
           ORDER BY tier_assigned_at DESC LIMIT 1""",
        (domain,),
    )
    contact = _query(
        "SELECT * FROM hot_warm_contacts WHERE company_domain = %s ORDER BY found_at DESC LIMIT 1",
        (domain,),
    )
    distributions = _query(
        """SELECT cs.title, dl.enrolled_at, dl.company_tier
           FROM distribution_log dl
           JOIN content_submissions cs ON dl.content_id = cs.id
           WHERE dl.company_domain = %s
           ORDER BY dl.enrolled_at DESC""",
        (domain,),
    )
    signals = _query(
        """SELECT * FROM warm_signals
           WHERE company_domain = %s
           ORDER BY detected_at DESC""",
        (domain,),
    )
    sequences = _query(
        """SELECT id, subject_line, sequence_status,
                  COALESCE(current_touch, 1) as current_touch,
                  touch_1_body, touch_2_body, touch_3_body,
                  touch_1_sent_at, touch_2_sent_at, touch_3_sent_at,
                  reply_detected_at
           FROM email_sequences
           WHERE company_domain = %s
           ORDER BY created_at DESC""",
        (domain,),
    )

    if not score:
        return {"error": f"No company scored for domain: {domain}"}

    return {
        "domain": domain,
        "score": score[0],
        "contact": contact[0] if contact else None,
        "pipeline_stage": (contact[0].get("pipeline_stage") if contact else None) or "Identified",
        "content_distributed": distributions,
        "warm_signals": signals,
        "email_sequences": sequences,
        "draft_status": sequences[0].get("sequence_status") if sequences else None,
    }


def _update_pipeline_stage(contact_id: int, stage: str) -> dict:
    valid = {"Identified", "LinkedIn Sent", "LinkedIn Connected", "Email Sent",
             "Replied", "Conversation", "Proposal", "Client"}
    if stage not in valid:
        return {"error": f"Invalid stage. Valid: {sorted(valid)}"}
    n = _execute(
        "UPDATE hot_warm_contacts SET pipeline_stage = %s WHERE id = %s",
        (stage, contact_id),
    )
    return {"success": n > 0, "rows_updated": n, "stage": stage}


def _mark_signal_actioned(signal_id: int) -> dict:
    n = _execute(
        "UPDATE warm_signals SET converted_to_conversation = TRUE WHERE id = %s",
        (signal_id,),
    )
    return {"success": n > 0, "rows_updated": n}


def _generate_linkedin_note(company_name_or_domain: str) -> dict:
    details = _get_prospect_details(company_name_or_domain)
    if details.get("error"):
        return details
    score = details["score"]
    contact = details.get("contact") or {}

    if not os.getenv("GEMINI_API_KEY"):
        return {"error": "GEMINI_API_KEY not set"}

    prompt = f"""Write a LinkedIn connection note from Jason (Waifinder BD) to {contact.get('contact_name', 'the operational leader')} at {score.get('company_name')}.

Jason's voice: Warm, relationship-oriented, never pushy. Leads with connection and curiosity.

What we know about their company:
{(score.get('scoring_rationale') or '')[:400]}

Specific situation:
{(score.get('execution_gap_evidence') or '')[:200]}

Rules:
- UNDER 300 characters total (LinkedIn limit is 300)
- Reference one specific thing about their company — no generic openings
- Never pitch Waifinder
- One question or open invitation, no hard CTA
- Sound human, not templated

Return ONLY the note text. No quotes, no preamble."""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        note = response.text.strip().strip('"')
        return {
            "company": score.get("company_name"),
            "contact": contact.get("contact_name"),
            "note": note,
            "char_count": len(note),
        }
    except Exception as e:
        return {"error": str(e)}


def _generate_email_opening(company_name_or_domain: str, signal_id: int = None) -> dict:
    details = _get_prospect_details(company_name_or_domain)
    if details.get("error"):
        return details
    score = details["score"]
    contact = details.get("contact") or {}

    signal_context = ""
    if signal_id:
        signal_rows = _query("SELECT * FROM warm_signals WHERE id = %s", (signal_id,))
        if signal_rows:
            s = signal_rows[0]
            signal_context = f"They engaged with: {s.get('signal_detail')} ({s.get('signal_type')})"

    if not os.getenv("GEMINI_API_KEY"):
        return {"error": "GEMINI_API_KEY not set"}

    prompt = f"""Write an email opening line from Jason (Waifinder BD) to {contact.get('contact_name')} at {score.get('company_name')}.

Jason's voice: Warm, relationship-oriented, leads with insight, never pushy.

Their situation:
{(score.get('scoring_rationale') or '')[:300]}

{signal_context}

Rules:
- 1-2 sentences maximum
- Reference what they engaged with OR a specific thing from our research
- Lead with empathy, not excitement about Waifinder
- Never pitch Waifinder
- Sound like a human who did their homework

Return ONLY the opening text. No quotes, no preamble."""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        return {
            "company": score.get("company_name"),
            "contact": contact.get("contact_name"),
            "opening": response.text.strip().strip('"'),
        }
    except Exception as e:
        return {"error": str(e)}


def _search_apollo_contacts(company_name_or_domain: str) -> dict:
    """Find top 3 contacts at a company via Apollo. Accepts name or domain."""
    looks_like_domain = "." in company_name_or_domain and " " not in company_name_or_domain
    if not looks_like_domain:
        lookup = _find_company_by_name(company_name_or_domain)
        if not lookup.get("matches"):
            return {"error": f"No company found matching '{company_name_or_domain}'"}
        domain = lookup["best_match"]["company_domain"]
    else:
        domain = company_name_or_domain

    try:
        from agents.apollo.client import search_contacts_by_domain
        result = search_contacts_by_domain(
            domain,
            title_keywords=["CEO", "COO", "CIO", "executive director", "director", "VP"],
            limit=5,
        )
        if result.get("ok"):
            return {
                "source": "Apollo",
                "domain": domain,
                "contacts": result.get("contacts", [])[:3],
            }
        return {"error": result.get("error", "Apollo search failed")}
    except Exception as e:
        return {"error": str(e)}


def _get_email_sequence_status(company_name_or_domain: str) -> dict:
    """Get email sequence status for a company. Accepts name or domain."""
    looks_like_domain = "." in company_name_or_domain and " " not in company_name_or_domain
    if not looks_like_domain:
        lookup = _find_company_by_name(company_name_or_domain)
        if not lookup.get("matches"):
            return {"error": f"No company found matching '{company_name_or_domain}'"}
        domain = lookup["best_match"]["company_domain"]
    else:
        domain = company_name_or_domain

    rows = _query(
        """SELECT id, contact_name, contact_email, subject_line,
                  COALESCE(current_touch, 1) as current_touch,
                  sequence_status,
                  touch_1_sent_at, touch_1_read, touch_2_sent_at, touch_2_read,
                  touch_3_sent_at, touch_3_read, reply_detected_at
           FROM email_sequences
           WHERE company_domain = %s
           ORDER BY created_at DESC""",
        (domain,),
    )
    return {
        "source": "email_sequences",
        "domain": domain,
        "sequences": rows,
    }


# ============================================================
# Tool registry
# ============================================================

TOOLS = [
    Tool(
        name="find_company_by_name",
        description="Look up a company by name to get its domain and basic info. Call this FIRST whenever Jason mentions a company by name — never ask him for a domain. Supports partial matches.",
        parameters={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Full or partial company name"},
            },
            "required": ["name"],
        },
        fn=lambda **kwargs: _find_company_by_name(kwargs["name"]),
    ),
    Tool(
        name="categorize_prospects",
        description="Count current Hot/Warm prospects by vertical (workforce_board, county_gov, healthcare, nonprofit, media, commercial) and by consulting fit (strong, weak, content_distribution_target). ALWAYS call this first when Jason challenges the pipeline composition or asks 'is this by design', 'why so many boards', 'which are good consulting clients'.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _categorize_prospects(),
    ),
    Tool(
        name="list_email_drafts",
        description="Return all email drafts currently pending review across all companies. Each entry has company_name, contact, subject, and the full body of the touch currently up for review. Use this when Jason asks for 'a sample of the messaging', 'what drafts are waiting', or 'show me some messaging'.",
        parameters={
            "type": "object",
            "properties": {
                "include_sent": {"type": "boolean", "description": "Include already-sent drafts (default false)"},
            },
            "required": [],
        },
        fn=lambda **kwargs: _list_email_drafts(kwargs.get("include_sent", False)),
    ),
    Tool(
        name="get_email_draft",
        description="Get the email draft for a specific company by name or domain. Returns the body and subject for whichever touch (1/2/3) is currently up for review. Use this when Jason says 'show me the messaging for <company>'.",
        parameters={
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name or domain"},
            },
            "required": ["company"],
        },
        fn=lambda **kwargs: _get_email_draft(kwargs["company"]),
    ),
    Tool(
        name="get_pipeline_summary",
        description="Return all BD contacts grouped by pipeline stage (Identified, LinkedIn Sent, LinkedIn Connected, Email Sent, Replied, Conversation, Proposal, Client). Use when Jason asks 'where are my prospects', 'what's in my pipeline', 'how many prospects are in conversation'.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _get_pipeline_summary(),
    ),
    Tool(
        name="get_hot_warm_prospects",
        description="Return all Hot and Warm companies with full scoring evidence. Use for 'who should I work on', 'show me my prospects', 'what's in the pipeline'.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _get_hot_warm_prospects(),
    ),
    Tool(
        name="get_warm_signals",
        description="Return warm signals from prospects who engaged with content. Use for 'what's hot today', 'who replied', 'any engagement signals'.",
        parameters={
            "type": "object",
            "properties": {
                "unacted_only": {"type": "boolean", "description": "Only return signals not yet actioned (default true)"},
            },
            "required": [],
        },
        fn=lambda **kwargs: _get_warm_signals(kwargs.get("unacted_only", True)),
    ),
    Tool(
        name="get_prospect_details",
        description="Synthesize ALL data for a single company — scoring, contact, pipeline stage, content distributed, signals, email sequences. Accepts company NAME or domain. When Jason names a company, use this directly — don't ask for the domain.",
        parameters={
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name OR domain. Name is preferred."},
            },
            "required": ["company"],
        },
        fn=lambda **kwargs: _get_prospect_details(kwargs["company"]),
    ),
    Tool(
        name="update_pipeline_stage",
        description="Move a contact through the BD pipeline. Stages: Identified, LinkedIn Sent, LinkedIn Connected, Email Sent, Replied, Conversation, Proposal, Client.",
        parameters={
            "type": "object",
            "properties": {
                "contact_id": {"type": "integer", "description": "hot_warm_contacts.id"},
                "stage": {"type": "string", "description": "New pipeline stage"},
            },
            "required": ["contact_id", "stage"],
        },
        fn=lambda **kwargs: _update_pipeline_stage(int(kwargs["contact_id"]), kwargs["stage"]),
    ),
    Tool(
        name="mark_signal_actioned",
        description="Mark a warm signal as converted to conversation when Jason has acted on it.",
        parameters={
            "type": "object",
            "properties": {
                "signal_id": {"type": "integer", "description": "warm_signals.id"},
            },
            "required": ["signal_id"],
        },
        fn=lambda **kwargs: _mark_signal_actioned(int(kwargs["signal_id"])),
    ),
    Tool(
        name="generate_linkedin_note",
        description="Generate a LinkedIn connection note (under 300 chars) in Jason's voice. Accepts company name OR domain.",
        parameters={
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name OR domain"},
            },
            "required": ["company"],
        },
        fn=lambda **kwargs: _generate_linkedin_note(kwargs["company"]),
    ),
    Tool(
        name="generate_email_opening",
        description="Generate an email opening line in Jason's voice. Accepts company name OR domain.",
        parameters={
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name OR domain"},
                "signal_id": {"type": "integer", "description": "Optional warm_signals.id"},
            },
            "required": ["company"],
        },
        fn=lambda **kwargs: _generate_email_opening(kwargs["company"], kwargs.get("signal_id")),
    ),
    Tool(
        name="search_apollo_contacts",
        description="Search Apollo for top 3 contacts at a company. Accepts name or domain.",
        parameters={
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name OR domain"},
            },
            "required": ["company"],
        },
        fn=lambda **kwargs: _search_apollo_contacts(kwargs["company"]),
    ),
    Tool(
        name="get_email_sequence_status",
        description="Get email sequence status for a company — which touches sent, read status, replies.",
        parameters={
            "type": "object",
            "properties": {
                "company": {"type": "string", "description": "Company name OR domain"},
            },
            "required": ["company"],
        },
        fn=lambda **kwargs: _get_email_sequence_status(kwargs["company"]),
    ),
]


# ============================================================
# BD Agent class with suggestion pills
# ============================================================

class BDAgent(BaseAgent):
    """BD Assistant with dynamic follow-up suggestion pills."""

    def extract_suggestions(self, response_text: str, history: list[dict]) -> list[str] | None:
        """Generate up to 4 contextual follow-up pills based on the response.

        Every pill must be SPECIFIC and unambiguous — phrases like "top Hot
        prospect's messaging" used to cause Gemini to pick COMC (no draft) and
        then get stuck in a context-poisoned state. Prefer pills that name a
        specific company, a specific tool, or an exact count.
        """
        text = (response_text or "").lower()
        pills: list[str] = []

        # Pick suggestions based on keywords in the response
        if "hot prospect" in text or "hot companies" in text or "hot):" in text:
            pills.append("Show me all 5 email drafts waiting for approval")
        if "linkedin" in text or "connection note" in text:
            pills.append("Generate a LinkedIn note for Harbor Path")
        if "warm signal" in text or "engagement" in text:
            pills.append("Which warm signals haven't I responded to?")
        if "draft" in text and "email" in text:
            pills.append("Show me the Food & Friends email draft")
        if "pipeline" in text:
            pills.append("Where are my prospects in the pipeline?")
        if "workforce" in text or "board" in text:
            pills.append("Which are real consulting fits vs content targets?")
        if "mountain west" in text:
            pills.append("Show me the Mountain West email draft")
        if "food & friends" in text or "food and friends" in text:
            pills.append("Show me the Food & Friends email draft")
        if "next action" in text or "today" in text:
            pills.append("Categorize my prospects by consulting fit")

        # Fall back to greatest-hits if nothing matched
        if not pills:
            pills = [
                "What should I work on today?",
                "Show me all 5 email drafts waiting for approval",
                "Categorize my prospects by consulting fit",
                "Tell me about Mountain West Conference",
            ]

        # Dedupe and cap at 4
        seen = set()
        unique = []
        for p in pills:
            if p not in seen:
                seen.add(p)
                unique.append(p)
            if len(unique) >= 4:
                break
        return unique


bd_agent = BDAgent(
    agent_type="bd",
    system_prompt=SYSTEM_PROMPT,
    tools=TOOLS,
)
