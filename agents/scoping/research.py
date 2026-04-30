"""Prospect research — uses Claude with web search tool for live research.

Claude's built-in web_search tool handles all web research directly,
eliminating the need for a separate Bing API key.

NOTE (#20): the primary path uses Anthropic's provider-specific
`web_search_20250305` tool, which the wfdos_common.llm text-completion
adapter does not expose. That call stays on the Anthropic SDK directly
until agent/tool orchestration lands in #26. The no-web-search fallback
path, however, IS migrated to the adapter so it picks up Azure OpenAI /
Gemini if Anthropic is unavailable.
"""

import httpx
from wfdos_common.graph import config
from anthropic import Anthropic
from wfdos_common.llm import complete as llm_complete
from wfdos_common.models.scoping import ScopingRequest, ResearchResult


async def fetch_page_text(url: str, max_chars: int = 5000) -> str:
    """Fetch a web page and extract text content."""
    try:
        async with httpx.AsyncClient(follow_redirects=True, timeout=10.0) as client:
            resp = await client.get(url)
            if resp.status_code != 200:
                return ""
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, "html.parser")
            for tag in soup(["script", "style", "nav", "footer", "header"]):
                tag.decompose()
            text = soup.get_text(separator=" ", strip=True)
            return text[:max_chars]
    except Exception as e:
        print(f"[RESEARCH] Failed to fetch {url}: {e}")
        return ""


async def research_prospect(req: ScopingRequest) -> ResearchResult:
    """Run web research on a prospect using Claude with web search tool."""
    org = req.organization
    contact = req.contact

    # Try to fetch the company website directly for additional context
    website_text = ""
    if org.website_url:
        website_text = await fetch_page_text(org.website_url)
        if website_text:
            print(f"[RESEARCH] Fetched {len(website_text)} chars from {org.website_url}")

    client = Anthropic(api_key=config.ANTHROPIC_API_KEY)

    website_context = ""
    if website_text:
        website_context = f"\n\nContent from their website ({org.website_url}):\n{website_text[:3000]}"

    prompt = f"""You are a business research analyst preparing a briefing for a consulting scoping call.

Company: {org.name}
Industry: {org.industry}
Website: {org.website_url}
Description: {org.short_description}
Contact: {contact.full_name}, {contact.title}
Notes from sales team: {req.notes}
{website_context}

Please research this company using web search and provide a structured research brief with these sections:

1. COMPANY OVERVIEW: 2-3 sentences on what the company does, their size, and market position.

2. MISSION AND STRATEGIC PRIORITIES: 2-3 sentences on their mission and what they are focused on strategically.

3. RECENT NEWS: List 3-5 recent notable developments (if found). If none found, say "No recent news found."

4. TECHNOLOGY AND DATA LANDSCAPE: What is known or can be inferred about their technology stack, data infrastructure, and digital maturity.

5. LIKELY PAIN POINTS: Based on their industry, size, and available information, what problems could CFA (an agentic AI engineering firm) likely solve for them? List 3-5 specific pain points.

6. SUGGESTED SCOPING QUESTIONS: 5-8 tailored questions that CFA should ask during the scoping call, based on what we know and don't know about this prospect.

Format each section clearly with the section name as a header. Be specific and actionable."""

    # Use Claude with web search tool for live research
    try:
        response = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=4000,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 5}],
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response (may have multiple content blocks with tool use)
        synthesis = ""
        for block in response.content:
            if hasattr(block, "text"):
                synthesis += block.text
        print(f"[RESEARCH] Claude research complete ({len(synthesis)} chars)")

    except Exception as e:
        print(f"[RESEARCH] Claude web search failed: {e}")
        # Fallback: synthesis without web search via the provider adapter.
        # Picks up Azure OpenAI / Gemini if Anthropic is unavailable.
        print("[RESEARCH] Falling back to synthesis without web search (via wfdos_common.llm)")
        synthesis = llm_complete(
            messages=[{"role": "user", "content": prompt}],
            tier="synthesis",
            max_tokens=2000,
        )

    result = _parse_research_response(synthesis)
    return result


def _parse_research_response(text: str) -> ResearchResult:
    """Parse Claude's structured research output into a ResearchResult."""
    result = ResearchResult()
    sections = text.split("\n")
    current_section = ""
    current_content = []

    def flush():
        nonlocal current_section, current_content
        content = "\n".join(current_content).strip()
        upper = current_section.upper()
        if "COMPANY OVERVIEW" in upper:
            result.company_overview = content
        elif "MISSION" in upper or "STRATEGIC" in upper:
            result.mission_and_strategy = content
        elif "NEWS" in upper:
            result.recent_news = [line.lstrip("- *0123456789.").strip() for line in content.split("\n") if line.strip() and not line.strip().startswith("#")]
        elif "TECHNOLOGY" in upper or "DATA LANDSCAPE" in upper:
            result.tech_landscape = content
        elif "PAIN POINT" in upper:
            result.likely_pain_points = [line.lstrip("- *0123456789.").strip() for line in content.split("\n") if line.strip() and not line.strip().startswith("#")]
        elif "SCOPING QUESTION" in upper or "SUGGESTED" in upper:
            result.suggested_questions = [line.lstrip("- *0123456789.").strip() for line in content.split("\n") if line.strip() and not line.strip().startswith("#")]
        current_content = []

    for line in sections:
        # Detect section headers (plain text or markdown)
        cleaned = line.strip().lstrip("#").strip().replace("**", "")
        upper = cleaned.upper()
        if any(header in upper for header in [
            "COMPANY OVERVIEW", "MISSION AND", "STRATEGIC PRIORITIES",
            "RECENT NEWS", "TECHNOLOGY AND", "DATA LANDSCAPE",
            "LIKELY PAIN", "SUGGESTED SCOPING", "SCOPING QUESTION"
        ]):
            flush()
            current_section = upper
        else:
            current_content.append(line)

    flush()
    return result
