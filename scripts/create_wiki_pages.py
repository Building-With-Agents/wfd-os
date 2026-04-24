"""Create the WFD OS internal wiki on the wAIFinder SharePoint site.

One-shot script. Safe to re-run — if a page already exists the script
prints a note and moves on without overwriting. Uses the Microsoft Graph
beta Pages API, same pattern as agents/graph/sharepoint.py.

Creates 8 pages under /sites/wAIFinder/SitePages/:
  WikiHome.aspx     — Platform overview
  ForGary.aspx      — Technical documentation
  ForJason.aspx     — BD system guide
  ForJessica.aspx   — Marketing system guide
  ForKrista.aspx    — Placeholder
  ForBethany.aspx   — Placeholder
  Architecture.aspx — Decisions + diagrams
  Products.aspx     — Product definitions

All pages use the "article" layout with a simple title + paragraph text
web part. Real content will be populated later via the Graph API or
directly in SharePoint's in-browser editor.
"""

import sys
import time
import httpx
from azure.identity import ClientSecretCredential

sys.path.insert(0, "C:/Users/ritub/projects/wfd-os")
from agents.graph import config

GRAPH_BETA = "https://graph.microsoft.com/beta"
GRAPH_V1 = "https://graph.microsoft.com/v1.0"

# -----------------------------------------------------------------------------
# Auth
# -----------------------------------------------------------------------------

def get_token() -> str:
    credential = ClientSecretCredential(
        tenant_id=config.AZURE_TENANT_ID,
        client_id=config.AZURE_CLIENT_ID,
        client_secret=config.AZURE_CLIENT_SECRET,
    )
    return credential.get_token("https://graph.microsoft.com/.default").token


HEADERS = {
    "Authorization": f"Bearer {get_token()}",
    "Content-Type": "application/json",
}

# Use the same wAIFinder site ID the rest of the app uses.
SITE_ID = config.INTERNAL_SITE_ID
SITE_URL_BASE = f"{config.SHAREPOINT_TENANT_URL}/sites/wAIFinder"

# -----------------------------------------------------------------------------
# Page definitions
# -----------------------------------------------------------------------------

PAGES = [
    {
        "name": "WikiHome.aspx",
        "title": "WFD OS Knowledge Base",
        "description": "Platform overview and navigation hub for the WFD OS wiki.",
        "body": [
            ("WFD OS — Internal Knowledge Base", "h1"),
            (
                "This is the internal wiki for Computing for All's WFD OS platform. "
                "It's the team's single source of truth for architecture, product "
                "definitions, and role-specific playbooks.",
                "p",
            ),
            ("Three-Layer Architecture", "h2"),
            (
                "WFD OS is organized into three layers: the Data layer (ingestion, "
                "normalization, storage), the Intelligence layer (scoring, extraction, "
                "analytics), and the Assistants layer (role-specific conversational "
                "interfaces for staff, students, employers, and colleges).",
                "p",
            ),
            ("Sections", "h2"),
            (
                "This wiki is organized into six areas. Use the navigation menu to "
                "jump to any section: For Gary (technical documentation), For Jason "
                "(BD system guide), For Jessica (marketing system guide), For Krista, "
                "For Bethany, Architecture (decisions + diagrams), and Products "
                "(LaborPulse, Career Navigator, WorkforceAgent, College Intelligence).",
                "p",
            ),
            (
                "Placeholder content — this page will be replaced with real platform "
                "overview material. Edit directly in SharePoint or update via the "
                "Microsoft Graph API.",
                "p-italic",
            ),
        ],
    },
    {
        "name": "ForGary.aspx",
        "title": "For Gary — Technical Documentation",
        "description": "Platform architecture, intelligence engines, and the cohort sprint plan.",
        "body": [
            ("For Gary — Technical Documentation", "h1"),
            (
                "Technical reference for Gary. Covers platform architecture, the four "
                "intelligence engines, the 12-week cohort sprint plan, and the "
                "independent feature ownership guide for cohort participants.",
                "p",
            ),
            ("Platform Architecture", "h2"),
            (
                "Multi-agent Python pipeline + Next.js portal. MSSQL for the existing "
                "app data, PostgreSQL for agent state. Agents communicate via typed, "
                "versioned events — direct function calls between agents are "
                "forbidden. See the Architecture page for the full decision log.",
                "p",
            ),
            ("Intelligence Engines Overview", "h2"),
            (
                "Four intelligence engines power WFD OS: ingestion + normalization, "
                "work intelligence (skills + tools + tasks extraction), enrichment "
                "(SOC/NAICS, employer profiles, temporal aggregates), and analytics "
                "(demand analysis, role clustering, disruption fingerprints).",
                "p",
            ),
            ("Cohort Sprint Plan", "h2"),
            (
                "12-week program that teaches participants to build a production-grade "
                "eight-agent system. Each week delivers specific agents and capabilities. "
                "Link to the lesson framework and sprint guides will be added here.",
                "p",
            ),
            ("Independent Feature Ownership Guide", "h2"),
            (
                "Each cohort pair owns a slice of the platform end-to-end. The guide "
                "explains how to propose, scope, build, and ship a feature autonomously "
                "with instructor review gates.",
                "p",
            ),
            (
                "Placeholder content — real technical docs will be added here.",
                "p-italic",
            ),
        ],
    },
    {
        "name": "ForJason.aspx",
        "title": "For Jason — BD System Guide",
        "description": "Waifinder BD pipeline, hot prospects, and the BD Command Center assistant.",
        "body": [
            ("For Jason — BD System Guide", "h1"),
            (
                "Jason's guide to the Waifinder BD system. Covers what Waifinder is, "
                "who the team targets, how the four-agent BD pipeline works, and how "
                "to use the BD Command Center and its conversational assistant.",
                "p",
            ),
            ("What Waifinder Is and Who We Target", "h2"),
            (
                "Waifinder builds agentic data engineering systems for mid-market "
                "organizations (20–1,000 employees, sweet spot 50–500). Targets are "
                "defined by three characteristics: fragmented data, technology ambition, "
                "and execution gap. Problem-based targeting, not vertical-based.",
                "p",
            ),
            ("How the BD Pipeline Works", "h2"),
            (
                "Four autonomous agents run continuously. Agent 15 (Market Discovery) "
                "scans for digital-transformation signals daily at 4 AM. Agent 12 "
                "(Lead Scoring) evaluates each discovered company using Gemini with "
                "live web search. Agent 14 (Contact Discovery) finds the right "
                "operational leader at every Hot or Warm company. Agent 13 (Content "
                "Distribution) generates personalized 3-touch email sequences.",
                "p",
            ),
            ("How to Use Your BD Command Center", "h2"),
            (
                "The BD Command Center lives at /internal/bd in the student portal. "
                "It shows hot prospects, unacted warm signals, pipeline status, and "
                "draft emails awaiting approval. The BD Assistant chat panel can answer "
                "any question about your pipeline — click a suggestion pill or type "
                "your own question.",
                "p",
            ),
            ("Current Hot Prospects", "h2"),
            (
                "As of the most recent pipeline run: COMC, Employ Prince George's, "
                "Food & Friends, Harbor Path, Mountain West Conference, Piedmont Health "
                "Services, and The Seattle Times are Hot. Vesta Inc. is Warm. "
                "The BD Command Center always shows the live list.",
                "p",
            ),
            (
                "Placeholder content — detailed playbooks for each workflow will be "
                "added here.",
                "p-italic",
            ),
        ],
    },
    {
        "name": "ForJessica.aspx",
        "title": "For Jessica — Marketing System Guide",
        "description": "Content strategy, marketing pipeline, assistant, and Apollo sequences.",
        "body": [
            ("For Jessica — Marketing System Guide", "h1"),
            (
                "Jessica's guide to the WFD OS marketing system. Covers content "
                "strategy, how the marketing pipeline fuels BD outreach, how to use "
                "the Marketing Assistant, and how to update Apollo sequences for "
                "the problem-based ICP framing.",
                "p",
            ),
            ("Content Strategy Guide", "h2"),
            (
                "Content is the fuel for the entire BD system. Agent 13 can only "
                "distribute what the team produces. Better content → more warm signals. "
                "Write to the three problem characteristics: fragmented data, "
                "technology ambition, execution gap.",
                "p",
            ),
            ("How the Marketing Pipeline Works", "h2"),
            (
                "When a new piece is published to the Resources section, Agent 13 picks "
                "it up within 15 minutes, matches it to the right prospects based on "
                "their scored evidence, and drafts personalized 3-touch email sequences "
                "in Ritu or Jason's voice. Drafts appear in Outlook for human review "
                "before sending.",
                "p",
            ),
            ("How to Use Your Marketing Assistant", "h2"),
            (
                "The Marketing Command Center lives at /internal/jessica in the student "
                "portal. It shows content performance, gap analysis (what topics Hot and "
                "Warm companies need that don't exist yet), and a conversational "
                "assistant that can plan, draft, and submit content.",
                "p",
            ),
            ("Apollo Sequence Update Instructions", "h2"),
            (
                "Pending: update Apollo sequences to reflect the problem-based ICP "
                "framing — fragmented data, technology ambition, execution gap — "
                "rather than vertical-specific language. Add a General/Nonprofit "
                "sequence for companies like Food & Friends and County of Berks.",
                "p",
            ),
            (
                "Placeholder content — detailed workflows will be added here.",
                "p-italic",
            ),
        ],
    },
    {
        "name": "ForKrista.aspx",
        "title": "For Krista",
        "description": "Placeholder — to be populated.",
        "body": [
            ("For Krista", "h1"),
            (
                "This page is a placeholder. The scope and content for Krista's "
                "section of the wiki will be defined separately.",
                "p",
            ),
        ],
    },
    {
        "name": "ForBethany.aspx",
        "title": "For Bethany",
        "description": "Placeholder — to be populated.",
        "body": [
            ("For Bethany", "h1"),
            (
                "This page is a placeholder. The scope and content for Bethany's "
                "section of the wiki will be defined separately.",
                "p",
            ),
        ],
    },
    {
        "name": "Architecture.aspx",
        "title": "Architecture — Decisions and Diagrams",
        "description": "Platform architecture, the four intelligence engines, and the design decisions log.",
        "body": [
            ("Architecture — Decisions and Diagrams", "h1"),
            (
                "Canonical reference for WFD OS architecture. Covers the platform "
                "architecture diagram, the four intelligence engines, agent "
                "specifications, and the design decisions log.",
                "p",
            ),
            ("Platform Architecture Diagram", "h2"),
            (
                "Next.js portal (TypeScript, React 19) on localhost:3000. Python "
                "FastAPI backends on ports 8002 (showcase), 8003, 8004 (college), "
                "8006 (consulting), 8007 (WJI), 8008 (marketing), 8009 (assistant), "
                "8010 (Apollo), 8011 (content). PostgreSQL wfd_os database for "
                "agent state. MSSQL for legacy Next.js app. Microsoft Graph API "
                "for SharePoint, Outlook, Teams integration.",
                "p",
            ),
            ("Four Intelligence Engines", "h2"),
            (
                "1. Ingestion + Normalization — scrape, clean, dedupe. "
                "2. Work Intelligence — extract skills, tools, tasks, responsibilities. "
                "3. Enrichment — SOC codes, NAICS, employer profiles, temporal periods. "
                "4. Analytics — demand analysis, role clustering, disruption fingerprints.",
                "p",
            ),
            ("Agent Specifications", "h2"),
            (
                "Every agent: one responsibility, typed event communication, "
                "health_check() method, self-evaluation metrics, and a non-negotiable "
                "target. Full spec lives in ARCHITECTURE_DEEP.md.",
                "p",
            ),
            ("Design Decisions Log", "h2"),
            (
                "Architectural decisions recorded as ADRs: classified as IC "
                "(individual contributor), SA (software architect), or D (design) "
                "decisions. Reference implementations available for every SA/D "
                "decision. See ARCHITECTURAL_DECISIONS.md.",
                "p",
            ),
            (
                "Placeholder content — full architecture docs will be imported here.",
                "p-italic",
            ),
        ],
    },
    {
        "name": "Products.aspx",
        "title": "Products — LaborPulse, Career Navigator, WorkforceAgent, College Intelligence",
        "description": "Definitions of the four WFD OS products.",
        "body": [
            ("Products", "h1"),
            (
                "WFD OS is packaged as four products, each targeting a different "
                "customer segment but sharing the same underlying platform.",
                "p",
            ),
            ("LaborPulse", "h2"),
            (
                "Real-time labor market intelligence for workforce boards, economic "
                "development agencies, and state workforce planners. Tracks in-demand "
                "skills, emerging roles, and regional disruption signals.",
                "p",
            ),
            ("Career Navigator", "h2"),
            (
                "AI career advisor for jobseekers — matches skills to open roles, "
                "identifies skill gaps, recommends training pathways, and surfaces "
                "employer connections from the verified pipeline.",
                "p",
            ),
            ("WorkforceAgent", "h2"),
            (
                "Agentic automation for HR and talent acquisition teams at mid-market "
                "employers. Ingests job requisitions, normalizes requirements, sources "
                "candidates from the talent pool, and drafts outreach.",
                "p",
            ),
            ("College Intelligence", "h2"),
            (
                "Decision-support platform for community colleges and workforce "
                "training providers. Aligns curriculum with regional labor demand, "
                "tracks graduate placement, and identifies emerging-skill gaps.",
                "p",
            ),
            (
                "Placeholder content — detailed product specs will be added here.",
                "p-italic",
            ),
        ],
    },
]


# -----------------------------------------------------------------------------
# Web part builders
# -----------------------------------------------------------------------------

def build_text_webpart(html: str) -> dict:
    """Construct a text web part for the canvasLayout."""
    return {
        "@odata.type": "#microsoft.graph.textWebPart",
        "innerHtml": html,
    }


def build_canvas_layout(body_blocks: list[tuple[str, str]]) -> dict:
    """Turn a list of (text, kind) tuples into a single-column canvasLayout.

    kind is one of: 'h1', 'h2', 'p', 'p-italic'. Each block becomes one text
    web part in a single vertical column.
    """
    html_parts: list[str] = []
    for text, kind in body_blocks:
        # Escape anything that could break the HTML — we control the content
        # here, but still be defensive.
        safe = (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
        )
        if kind == "h1":
            html_parts.append(f"<h1>{safe}</h1>")
        elif kind == "h2":
            html_parts.append(f"<h2>{safe}</h2>")
        elif kind == "p-italic":
            html_parts.append(f"<p><em>{safe}</em></p>")
        else:  # default p
            html_parts.append(f"<p>{safe}</p>")

    combined_html = "\n".join(html_parts)
    return {
        "horizontalSections": [
            {
                "layout": "oneColumn",
                "columns": [
                    {
                        "webparts": [build_text_webpart(combined_html)],
                    }
                ],
            }
        ]
    }


# -----------------------------------------------------------------------------
# Page operations
# -----------------------------------------------------------------------------

def page_exists(name: str) -> dict | None:
    """Return the existing sitePage if it already exists, else None."""
    r = httpx.get(f"{GRAPH_BETA}/sites/{SITE_ID}/pages", headers=HEADERS, timeout=30.0)
    if r.status_code != 200:
        print(f"  [warn] list pages failed: HTTP {r.status_code}")
        return None
    for p in r.json().get("value", []):
        if p.get("name", "").lower() == name.lower():
            return p
    return None


def create_page(spec: dict) -> dict | None:
    """Create and publish a single page. Returns the published page dict."""
    existing = page_exists(spec["name"])
    if existing:
        print(f"  [skip]    {spec['name']} — already exists (id={existing.get('id','')[:8]})")
        return existing

    body = {
        "@odata.type": "#microsoft.graph.sitePage",
        "name": spec["name"],
        "title": spec["title"],
        "pageLayout": "article",
        "showComments": True,
        "showRecommendedPages": False,
        "titleArea": {
            "enableGradientEffect": True,
            "imageWebUrl": None,
            "layout": "imageAndTitle",
            "showAuthor": True,
            "showPublishedDate": False,
            "showTextBlockAboveTitle": False,
            "textAboveTitle": "",
            "textAlignment": "left",
            "title": spec["title"],
        },
        "canvasLayout": build_canvas_layout(spec["body"]),
        "description": spec.get("description", ""),
    }

    url = f"{GRAPH_BETA}/sites/{SITE_ID}/pages"
    r = httpx.post(url, headers=HEADERS, json=body, timeout=60.0)

    if r.status_code not in (200, 201):
        print(f"  [error]   {spec['name']} — create HTTP {r.status_code}: {r.text[:300]}")
        return None

    page = r.json()
    page_id = page.get("id", "")
    print(f"  [created] {spec['name']}  (id={page_id[:8]})")

    # Publish so it's visible to everyone
    publish_url = f"{GRAPH_BETA}/sites/{SITE_ID}/pages/{page_id}/microsoft.graph.sitePage/publish"
    pr = httpx.post(publish_url, headers=HEADERS, timeout=30.0)
    if pr.status_code in (200, 204):
        print(f"  [pub'd]   {spec['name']}")
    else:
        print(f"  [warn]    {spec['name']} — publish HTTP {pr.status_code}: {pr.text[:200]}")

    return page


# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------

def main() -> None:
    print("=" * 70)
    print("Creating WFD OS internal wiki on wAIFinder")
    print("=" * 70)
    print(f"Site: {SITE_URL_BASE}")
    print(f"Site ID: {SITE_ID[:40]}...")
    print(f"Pages to create: {len(PAGES)}")
    print()

    created: list[tuple[str, str]] = []
    for spec in PAGES:
        page = create_page(spec)
        if page:
            web_url = page.get("webUrl", "")
            created.append((spec["name"], web_url))
        # Small delay so we don't hammer the API
        time.sleep(0.5)

    print()
    print("=" * 70)
    print(f"SUMMARY — {len(created)}/{len(PAGES)} pages ready")
    print("=" * 70)
    for name, url in created:
        print(f"  {name:25s}  {url}")


if __name__ == "__main__":
    main()
