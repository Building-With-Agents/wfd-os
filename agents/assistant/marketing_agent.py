"""Marketing Agent — Jessica's Marketing Command Center Assistant.

Helps Jessica plan, draft, and submit content to the Waifinder distribution
pipeline. Reads from content_submissions, distribution_log, warm_signals,
company_scores (recommended_content), marketing_leads.
"""
from __future__ import annotations
import os
import re
import sys
import json
from datetime import datetime, timezone

import psycopg2
import psycopg2.extras
import google.generativeai as genai

from agents.assistant.base import BaseAgent, Tool

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


SYSTEM_PROMPT = """You are Jessica's Marketing Assistant for Waifinder.

Jessica plans and produces content that Waifinder's agents distribute to prospects.
You help her decide what to write, draft outlines and LinkedIn versions, understand
what is performing, and submit pieces to the distribution pipeline.

You know what content exists, what is performing, and what gaps exist based on
what Agent 15 is finding about prospects. You bridge agent intelligence to
Jessica's content decisions.

Always ground recommendations in evidence — tell Jessica not just what to write
but why, citing specific signals from the prospect database.

Goal: Help Jessica produce the right content at the right time to generate
warm signals for Jason.

Be concise and specific. Cite specific companies and numbers from the database.
Never speculate without data.

PUBLISHING POLISHED BLOG CONTENT (use the update_blog_content tool)

Right now one of your most important jobs is helping Jessica publish and update
blog content on the CFA website. When Jessica says she wants to update or
replace a blog post, follow this exact flow:

1. Identify which article she means. The slug appears in the URL after
   /resources/blog/. Examples: "what-is-agentic-ai", "workforce-boards-ai-future",
   "ai-talent-hiring-struggles", "real-cost-fragmented-data".
2. Confirm the target URL out loud:
   "Got it — that's /resources/blog/<slug>. Paste the polished content when ready
   and I'll update it."
3. WAIT for Jessica to paste the actual polished content. Do NOT call
   update_blog_content until she has provided real content. If she only said
   "I want to update X", that is NOT enough — ask for the content.
4. Once she pastes content, call update_blog_content with the slug and the
   new markdown body. The tool preserves frontmatter (title, author, date, tags)
   and replaces only the body of the post.
5. After the tool returns, confirm the LIVE URL by quoting the live_url field
   from the tool response so Jessica can click through and see it rendered.

Never invent slugs. If unsure which article Jessica means, ask her to confirm
the URL."""


def _conn():
    return psycopg2.connect(**PG_CONFIG)


def _query(sql, params=None):
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
        result_id = None
        try:
            result_id = cur.fetchone()
        except Exception:
            pass
        conn.commit()
        return result_id[0] if result_id else cur.rowcount
    finally:
        conn.close()


# ============================================================
# Tool implementations
# ============================================================

def _get_content_performance() -> dict:
    """Read content performance metrics — signals per piece."""
    rows = _query(
        """SELECT cs.id, cs.title, cs.author, cs.vertical, cs.topic_tags,
                  cs.status, cs.distributed_at,
                  COALESCE(dl.contacts_reached, 0) as contacts_reached,
                  COALESCE(ws.signal_count, 0) as signals_generated
           FROM content_submissions cs
           LEFT JOIN (
               SELECT content_id, COUNT(*) as contacts_reached
               FROM distribution_log GROUP BY content_id
           ) dl ON cs.id = dl.content_id
           LEFT JOIN (
               SELECT content_id, COUNT(*) as signal_count
               FROM warm_signals GROUP BY content_id
           ) ws ON cs.id = ws.content_id
           ORDER BY cs.submitted_at DESC"""
    )
    # Compute signal rate
    for r in rows:
        contacts = r["contacts_reached"] or 0
        signals = r["signals_generated"] or 0
        r["signal_rate_pct"] = round(signals / contacts * 100, 1) if contacts > 0 else 0
    return {"source": "content_submissions + distribution_log + warm_signals", "content": rows}


def _get_content_gaps() -> dict:
    """Cross-reference recommended_content from company_scores against existing content."""
    # Get recommended content from Hot/Warm companies
    recs = _query(
        """SELECT DISTINCT ON (cs.company_domain)
                  cs.company_name, cs.company_domain, cs.tier, cs.recommended_content,
                  pc.vertical
           FROM company_scores cs
           LEFT JOIN prospect_companies pc ON pc.company_domain = cs.company_domain
           WHERE cs.tier IN ('Hot', 'Warm')
             AND cs.recommended_content IS NOT NULL
             AND cs.recommended_content != ''
           ORDER BY cs.company_domain, cs.tier_assigned_at DESC"""
    )

    # Get existing content topics
    existing = _query(
        "SELECT id, title, topic_tags FROM content_submissions"
    )
    existing_tags = set()
    for c in existing:
        for tag in (c.get("topic_tags") or []):
            existing_tags.add(tag.lower())

    # Group recommendations by topic theme
    gaps = {}
    for r in recs:
        topic = (r.get("recommended_content") or "")[:100]
        if topic not in gaps:
            gaps[topic] = {
                "topic": topic,
                "companies": [],
                "verticals": set(),
                "company_count": 0,
            }
        gaps[topic]["companies"].append(r["company_name"])
        gaps[topic]["verticals"].add(r.get("vertical") or "other")
        gaps[topic]["company_count"] += 1

    # Convert to list and check coverage
    gap_list = []
    for topic, data in gaps.items():
        # Crude check: any words from topic match existing tags
        topic_words = set(topic.lower().split())
        has_coverage = bool(topic_words & existing_tags)
        gap_list.append({
            "topic": topic,
            "company_count": data["company_count"],
            "companies": data["companies"][:5],
            "verticals": list(data["verticals"]),
            "has_coverage": has_coverage,
            "priority": "high" if data["company_count"] >= 3 and not has_coverage
                        else ("medium" if data["company_count"] >= 1 and not has_coverage
                              else "covered"),
        })

    gap_list.sort(key=lambda x: (-x["company_count"], x["has_coverage"]))
    return {"source": "company_scores.recommended_content x content_submissions", "gaps": gap_list}


def _get_content_calendar() -> dict:
    """Return all content_submissions with status."""
    rows = _query(
        """SELECT cs.*,
                  COALESCE(ws.signal_count, 0) as signals
           FROM content_submissions cs
           LEFT JOIN (
               SELECT content_id, COUNT(*) as signal_count
               FROM warm_signals GROUP BY content_id
           ) ws ON cs.id = ws.content_id
           ORDER BY cs.submitted_at DESC"""
    )
    return {"source": "content_submissions", "calendar": rows}


def _submit_content(title: str, url: str, author: str, vertical: str = "general",
                    topic_tags: list = None, funnel_stage: str = "awareness",
                    format: str = "long-form", distribute_immediately: bool = True,
                    schedule_datetime: str = None) -> dict:
    """Submit a new content piece to the distribution pipeline."""
    distribution_timing = None
    if not distribute_immediately and schedule_datetime:
        distribution_timing = schedule_datetime

    new_id = _execute(
        """INSERT INTO content_submissions
           (title, url, author, vertical, topic_tags, funnel_stage, format,
            distribution_timing, status, deployment_id)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
           RETURNING id""",
        (
            title, url, author, vertical, topic_tags or [],
            funnel_stage, format, distribution_timing,
            "pending", "waifinder-national",
        ),
    )

    return {
        "success": True,
        "id": new_id,
        "status": "pending",
        "estimated_distribution": "next 15-minute Agent 13 cycle" if distribute_immediately else schedule_datetime,
        "message": f"Content '{title}' queued for distribution",
    }


def _get_prospect_context_for_topic(topic: str) -> dict:
    """Find Hot/Warm companies whose recommended_content matches a topic."""
    rows = _query(
        """SELECT DISTINCT ON (company_domain)
                  company_name, company_domain, tier, recommended_content,
                  scoring_rationale, fragmented_data_evidence,
                  technology_ambition_evidence, execution_gap_evidence
           FROM company_scores
           WHERE tier IN ('Hot', 'Warm')
             AND LOWER(recommended_content) LIKE LOWER(%s)
           ORDER BY company_domain, tier_assigned_at DESC""",
        (f"%{topic}%",),
    )
    return {
        "source": "company_scores",
        "topic": topic,
        "matching_companies": rows,
        "count": len(rows),
    }


def _draft_blog_outline(topic: str, target_situation: str = "", key_signals: str = "") -> dict:
    """Generate a blog outline using prospect context."""
    context = _get_prospect_context_for_topic(topic)
    matching = context.get("matching_companies", [])

    company_examples = []
    for c in matching[:3]:
        company_examples.append(
            f"- {c['company_name']}: {(c.get('execution_gap_evidence') or '')[:200]}"
        )

    if not os.getenv("GEMINI_API_KEY"):
        return {"error": "GEMINI_API_KEY not set"}

    prompt = f"""Draft a blog post outline for Jessica at Waifinder.

Topic: {topic}
Target situation: {target_situation or 'mid-market organizations facing this'}
Key signals to address: {key_signals or 'fragmented data, execution gaps'}

Real examples from our prospect database (anonymize names in writing):
{chr(10).join(company_examples) if company_examples else 'No specific examples available'}

Return JSON:
{{
  "headlines": ["3 headline options"],
  "structure": [
    {{"section": "Section title", "key_point": "Main point", "example": "Specific example"}}
  ],
  "cta": "Suggested call to action"
}}

Return ONLY the JSON. No markdown fences."""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        return json.loads(text)
    except Exception as e:
        return {"error": str(e)}


def _draft_linkedin_version(content_title: str, content_url: str = "", target_vertical: str = "general") -> dict:
    """Generate a LinkedIn post version of an existing content piece."""
    if not os.getenv("GEMINI_API_KEY"):
        return {"error": "GEMINI_API_KEY not set"}

    prompt = f"""Write a LinkedIn post for this Waifinder content:

Title: {content_title}
URL: {content_url}
Target vertical: {target_vertical}

Rules:
- UNDER 250 words total
- Hook (first line) — stops the scroll
- 3-4 short paragraphs
- One CTA with link at the end
- 3-5 relevant hashtags

Return JSON:
{{
  "hook": "first line",
  "body": "full post body",
  "hashtags": ["tag1", "tag2"],
  "word_count": integer
}}

Return ONLY the JSON. No markdown fences."""

    try:
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        text = response.text.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            text = "\n".join(lines[1:-1])
        return json.loads(text)
    except Exception as e:
        return {"error": str(e)}


def _get_lead_capture_metrics() -> dict:
    """Read marketing_leads — this week vs last week."""
    try:
        this_week = _query(
            """SELECT content_title, content_type, COUNT(*) as leads
               FROM marketing_leads
               WHERE created_at > NOW() - INTERVAL '7 days'
               GROUP BY content_title, content_type
               ORDER BY leads DESC LIMIT 10"""
        )
        last_week = _query(
            """SELECT COUNT(*) as total FROM marketing_leads
               WHERE created_at BETWEEN NOW() - INTERVAL '14 days'
                                     AND NOW() - INTERVAL '7 days'"""
        )
        total_this_week = _query(
            "SELECT COUNT(*) as total FROM marketing_leads WHERE created_at > NOW() - INTERVAL '7 days'"
        )
        return {
            "source": "marketing_leads",
            "this_week_total": total_this_week[0]["total"] if total_this_week else 0,
            "last_week_total": last_week[0]["total"] if last_week else 0,
            "by_content": this_week,
        }
    except Exception as e:
        return {"error": str(e), "note": "marketing_leads table may not exist yet"}


# ============================================================
# Tool registry
# ============================================================

# ---------------------------------------------------------------------------
# update_blog_content — publish polished content to wfd-os/content/blog/{slug}.md
# ---------------------------------------------------------------------------

# Repo root for resolving the content directory
_REPO_ROOT_FOR_CONTENT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
_BLOG_DIR = os.path.join(_REPO_ROOT_FOR_CONTENT, "content", "blog")


def _split_frontmatter(raw: str) -> tuple[str, str]:
    """Split a markdown file into (frontmatter_block, body).

    frontmatter_block is the full ---...--- header (including delimiters)
    so it can be re-emitted unchanged. Returns ("", raw) if no frontmatter.
    """
    if not raw.startswith("---\n"):
        return "", raw
    # Find the closing --- on its own line
    second = raw.find("\n---\n", 4)
    if second == -1:
        return "", raw
    fm_end = second + len("\n---\n")
    return raw[:fm_end], raw[fm_end:].lstrip("\n")


def _update_blog_content(slug: str, new_body: str, update_date: bool = False) -> dict:
    """Replace the body of an existing blog post markdown file.

    Preserves the YAML frontmatter (title, author, tags, etc) and replaces
    everything below it with `new_body`. Optionally updates the `date:` field
    in frontmatter to today.

    Returns:
        {ok, slug, file_path, live_url, bytes_written, error}
    """
    if not slug or not isinstance(slug, str):
        return {"ok": False, "error": "slug is required"}

    # Sanitize slug — must be a single path segment, no slashes or dots
    safe = slug.strip().lstrip("/").rstrip("/")
    if "/" in safe or "\\" in safe or ".." in safe:
        return {"ok": False, "error": f"invalid slug: {slug!r}"}

    file_path = os.path.join(_BLOG_DIR, f"{safe}.md")
    if not os.path.exists(file_path):
        # Show available slugs to help the agent recover
        try:
            available = sorted(
                f[:-3] for f in os.listdir(_BLOG_DIR) if f.endswith(".md")
            )
        except Exception:
            available = []
        return {
            "ok": False,
            "error": f"no blog post found at {file_path}",
            "slug_requested": safe,
            "available_slugs": available,
        }

    if not new_body or not isinstance(new_body, str):
        return {"ok": False, "error": "new_body is required and must be a string"}

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            raw = f.read()
        frontmatter, _old_body = _split_frontmatter(raw)
        if not frontmatter:
            return {
                "ok": False,
                "error": f"file at {file_path} has no frontmatter — refusing to overwrite",
            }

        if update_date:
            # Replace the date: line in the frontmatter
            today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            frontmatter = re.sub(
                r'^date:\s*"?[^"\n]*"?\s*$',
                f'date: "{today}"',
                frontmatter,
                count=1,
                flags=re.MULTILINE,
            )

        body = new_body.strip() + "\n"
        new_raw = frontmatter.rstrip("\n") + "\n\n" + body

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_raw)

        return {
            "ok": True,
            "slug": safe,
            "file_path": file_path,
            "live_url": f"http://localhost:3000/resources/blog/{safe}",
            "bytes_written": len(new_raw.encode("utf-8")),
        }
    except Exception as e:
        return {"ok": False, "error": f"{type(e).__name__}: {e}"}


TOOLS = [
    Tool(
        name="update_blog_content",
        description=(
            "Publish polished blog content to an existing CFA blog post. Accepts "
            "the post's slug (the URL segment after /resources/blog/) and the new "
            "markdown body. Preserves frontmatter (title, author, date, tags) and "
            "replaces only the post body. Returns the live URL on success. Only "
            "call this AFTER Jessica has actually pasted the polished content — "
            "never call it just because she said she wants to update something."
        ),
        parameters={
            "type": "object",
            "properties": {
                "slug": {
                    "type": "string",
                    "description": "URL slug of the blog post, e.g. 'what-is-agentic-ai' (no leading slash, no .md extension).",
                },
                "new_body": {
                    "type": "string",
                    "description": "The full polished markdown body to replace the current post body. Frontmatter is preserved automatically — do not include it.",
                },
                "update_date": {
                    "type": "boolean",
                    "description": "If true, also bump the date: field in frontmatter to today. Default false.",
                },
            },
            "required": ["slug", "new_body"],
        },
        fn=lambda **kwargs: _update_blog_content(
            kwargs["slug"],
            kwargs["new_body"],
            kwargs.get("update_date", False),
        ),
    ),
    Tool(
        name="get_content_performance",
        description="Get performance metrics per content piece — contacts reached, signals generated, signal rate. Call when Jessica asks 'what's working' or 'what content is performing'.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _get_content_performance(),
    ),
    Tool(
        name="get_content_gaps",
        description="Identify content gaps by cross-referencing what Hot/Warm companies need (recommended_content from Agent 12) against what we've already written. Call when Jessica asks 'what should I write' or 'what gaps exist'.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _get_content_gaps(),
    ),
    Tool(
        name="get_content_calendar",
        description="Return all content_submissions with status and signal counts. Call when Jessica asks about her content calendar or pipeline.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _get_content_calendar(),
    ),
    Tool(
        name="submit_content",
        description="Submit a new content piece to the distribution pipeline. Always confirm with Jessica before calling this — show her the title, URL, and topic tags first.",
        parameters={
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "url": {"type": "string"},
                "author": {"type": "string", "description": "ritu, jason, or jessica"},
                "vertical": {"type": "string"},
                "topic_tags": {"type": "array", "items": {"type": "string"}},
                "funnel_stage": {"type": "string", "description": "awareness, consideration, decision"},
                "format": {"type": "string", "description": "long-form, short-form, email-snippet, case-study"},
                "distribute_immediately": {"type": "boolean"},
                "schedule_datetime": {"type": "string", "description": "ISO datetime for scheduled distribution"},
            },
            "required": ["title", "url", "author"],
        },
        fn=lambda **kwargs: _submit_content(**kwargs),
    ),
    Tool(
        name="get_prospect_context_for_topic",
        description="Find which Hot/Warm companies need content on a specific topic. Returns specific company situations Jessica can reference in her writing.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Topic keyword e.g. 'fragmented data', 'workforce'"},
            },
            "required": ["topic"],
        },
        fn=lambda **kwargs: _get_prospect_context_for_topic(kwargs["topic"]),
    ),
    Tool(
        name="draft_blog_outline",
        description="Generate a full blog outline grounded in real prospect data — headlines, sections, key points, examples, CTA.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {"type": "string"},
                "target_situation": {"type": "string"},
                "key_signals": {"type": "string"},
            },
            "required": ["topic"],
        },
        fn=lambda **kwargs: _draft_blog_outline(
            kwargs["topic"],
            kwargs.get("target_situation", ""),
            kwargs.get("key_signals", ""),
        ),
    ),
    Tool(
        name="draft_linkedin_version",
        description="Generate a LinkedIn post version of existing content — hook, body, CTA, hashtags, under 250 words.",
        parameters={
            "type": "object",
            "properties": {
                "content_title": {"type": "string"},
                "content_url": {"type": "string"},
                "target_vertical": {"type": "string"},
            },
            "required": ["content_title"],
        },
        fn=lambda **kwargs: _draft_linkedin_version(
            kwargs["content_title"],
            kwargs.get("content_url", ""),
            kwargs.get("target_vertical", "general"),
        ),
    ),
    Tool(
        name="get_lead_capture_metrics",
        description="Read marketing_leads table — this week vs last week comparison, leads by content piece.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _get_lead_capture_metrics(),
    ),
]


marketing_agent = BaseAgent(
    agent_type="marketing",
    system_prompt=SYSTEM_PROMPT,
    tools=TOOLS,
)
