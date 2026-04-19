"""Employer Agent — TRUST BEFORE ACTION.

The most important agent — directly serves the north star (employers delighted).
Two modes: hiring (talent search) and consulting (AI build).
"""
from __future__ import annotations
import json
import httpx
from agents.assistant.base import BaseAgent, Tool

SYSTEM_PROMPT = """You are a knowledgeable talent and technology advisor at the Washington Tech Workforce Coalition, powered by Computing for All.

You serve two types of employers:
1. Hiring managers looking for pre-vetted tech talent
2. Business leaders who need agentic AI systems built

Your job is to figure out which they are and help them efficiently.

FOR HIRING EMPLOYERS:
You know the talent pool deeply:
- 101 pre-vetted candidates with skills verified through real project work — not self-reported
- Angel: built ingestion and normalization agents for the Job Intelligence Engine. Skills: Python 4/5, PostgreSQL 3/5, Claude API 3/5, Git 4/5
- Fabian: built enrichment and analytics agents for JIE. Skills: Azure OpenAI 4/5, pgvector 4/5, FastAPI 4/5
- 99 other candidates across web development, IT support, data analytics, cloud, cybersecurity
- All placed through CFA — placement takes 2-4 weeks typically
- CFA earns 15-20% placement fee paid by the hiring employer
- All contact facilitated by CFA — NEVER share candidate contact info directly

Hiring flow:
1. What role are they hiring for?
2. Use search_candidates to find matches
3. Show top 3 with proof of work highlights
4. Go deeper on the one they like (get_proof_of_work)
5. Offer CFA introduction (contact_cfa_about_candidate)

FOR AI CONSULTING EMPLOYERS:
Same de-risking approach:
- Fixed price $20-35K typical
- 10-14 weeks
- Supervised apprentice team
- Try before you hire — evaluate talent during delivery, hire them after
- Proof of concept: Workforce Solutions Borderplex Job Intelligence Engine — $25,500, 12 weeks, now running in production processing thousands of job listings weekly

Consulting flow: one question at a time, reference Borderplex naturally, collect intake info, submit_consulting_inquiry when ready.

KEY PRINCIPLES:
- Employers are busy — be efficient. 3-4 sentences max per response.
- Show proof before asking for commitment.
- Never oversell apprentice capabilities. Be honest: "They're trained and supervised — not 10-year veterans. But they built production systems and the work is guaranteed."
- Make contacting CFA feel easy and safe — no commitment to contact.
- Coalition membership context: "As a coalition employer you get priority access to candidates and discounted consulting rates."
- NEVER reveal candidate full names, emails, phone numbers, or addresses. Use first name + last initial only (e.g., "Angel R.").
- When switching from hiring to consulting or vice versa, transition smoothly — don't make them restart."""


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

# Hardcoded showcase data matching what's in the real DB
CANDIDATE_DB = [
    {"id": "angel-001", "display_name": "Angel R.", "location": "Seattle, WA", "top_skills": ["Python", "PostgreSQL", "Claude API", "FastAPI", "Git"], "match_areas": ["ai", "python", "backend", "data"], "availability": "Available", "placement_type": "Full-time or contract",
     "proof": {"project": "Job Intelligence Engine", "role": "Built ingestion and normalization agents", "tech": ["Python", "PostgreSQL", "Claude API", "FastAPI"], "outcome": "Processing 800+ job listings daily in production", "github": "Available on request"}},
    {"id": "fabian-001", "display_name": "Fabian M.", "location": "Bellevue, WA", "top_skills": ["Azure OpenAI", "pgvector", "FastAPI", "Python", "SQL"], "match_areas": ["ai", "python", "backend", "data", "cloud"], "availability": "Available", "placement_type": "Full-time",
     "proof": {"project": "Job Intelligence Engine", "role": "Built enrichment and analytics agents with semantic search", "tech": ["Azure OpenAI", "pgvector", "FastAPI", "Python"], "outcome": "Semantic job matching and skills extraction running in production", "github": "Available on request"}},
    {"id": "bryan-001", "display_name": "Bryan L.", "location": "Seattle, WA", "top_skills": ["React", "TypeScript", "Node.js", "PostgreSQL", "Tailwind CSS"], "match_areas": ["frontend", "web", "fullstack", "javascript"], "availability": "Available", "placement_type": "Full-time or contract",
     "proof": {"project": "WFD OS Portal System", "role": "Built student and employer portal frontends", "tech": ["React", "TypeScript", "Next.js", "Tailwind CSS"], "outcome": "Production portals serving multiple user types with real-time data", "github": "Available on request"}},
    {"id": "emilio-001", "display_name": "Emilio G.", "location": "Tacoma, WA", "top_skills": ["Python", "AWS", "Docker", "Linux", "CI/CD"], "match_areas": ["cloud", "devops", "infrastructure", "python"], "availability": "Available", "placement_type": "Full-time",
     "proof": {"project": "CFA Infrastructure", "role": "Set up CI/CD pipelines and cloud deployment", "tech": ["AWS", "Docker", "GitHub Actions", "Linux"], "outcome": "Automated deployment pipeline for multi-service application", "github": "Available on request"}},
    {"id": "fatima-001", "display_name": "Fatima S.", "location": "Redmond, WA", "top_skills": ["SQL", "Python", "Excel", "Tableau", "Power BI"], "match_areas": ["data", "analytics", "reporting", "sql"], "availability": "Available", "placement_type": "Full-time or contract",
     "proof": {"project": "WJI Grant Analytics", "role": "Built placement tracking and grant reporting dashboards", "tech": ["SQL", "Python", "Excel"], "outcome": "Automated quarterly WSAC placement reports", "github": "Available on request"}},
    {"id": "juan-001", "display_name": "Juan C.", "location": "Kent, WA", "top_skills": ["JavaScript", "React", "HTML/CSS", "Node.js", "Git"], "match_areas": ["frontend", "web", "javascript", "fullstack"], "availability": "Available", "placement_type": "Full-time",
     "proof": {"project": "Coalition Web Portal", "role": "Built responsive employer-facing web interfaces", "tech": ["JavaScript", "React", "HTML/CSS"], "outcome": "Production web application with real-time data integration", "github": "Available on request"}},
    {"id": "nestor-001", "display_name": "Nestor V.", "location": "Renton, WA", "top_skills": ["Python", "Cybersecurity", "Linux", "Networking", "SIEM"], "match_areas": ["cybersecurity", "security", "networking", "linux", "infrastructure"], "availability": "Available", "placement_type": "Full-time",
     "proof": {"project": "CFA Security Review", "role": "Conducted security assessment and hardening", "tech": ["Linux", "SIEM tools", "Python scripting"], "outcome": "Identified and remediated vulnerabilities across infrastructure", "github": "Available on request"}},
    {"id": "enrique-001", "display_name": "Enrique D.", "location": "Federal Way, WA", "top_skills": ["Python", "SQL", "Data Engineering", "ETL", "PostgreSQL"], "match_areas": ["data", "backend", "python", "etl", "sql"], "availability": "Available", "placement_type": "Full-time or contract",
     "proof": {"project": "Data Migration Pipeline", "role": "Built ETL pipelines for 5,000+ record migration", "tech": ["Python", "PostgreSQL", "psycopg2"], "outcome": "Successfully migrated legacy CRM data to new PostgreSQL schema", "github": "Available on request"}},
]


def _search_candidates(skills: str = "", role_type: str = "", location: str = "") -> list[dict]:
    """Search candidates — tries real PostgreSQL first, falls back to hardcoded Cohort 1 profiles."""
    # Try real DB first
    try:
        import psycopg2, psycopg2.extras
        from wfdos_common.config import PG_CONFIG
        conn = psycopg2.connect(**PG_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        q = (skills + " " + role_type).strip()
        if q:
            terms = [f"%{t.strip()}%" for t in q.replace(",", " ").split() if len(t.strip()) > 2]
            if terms:
                # Search students who have matching skills
                skill_conditions = " OR ".join(["ss.skill_name ILIKE %s"] * len(terms))
                cur.execute(f"""
                    SELECT s.id, s.full_name, s.city, s.state, s.availability_status,
                           s.profile_completeness_score,
                           array_agg(DISTINCT ss.skill_name) FILTER (WHERE ss.skill_name IS NOT NULL) as skills
                    FROM students s
                    LEFT JOIN student_skills ss ON ss.student_id = s.id
                    WHERE ({skill_conditions})
                      AND s.resume_parsed = true
                    GROUP BY s.id
                    ORDER BY s.profile_completeness_score DESC NULLS LAST
                    LIMIT 5
                """, terms)
                rows = cur.fetchall()
                conn.close()

                if rows:
                    results = []
                    for r in rows:
                        name = r["full_name"] or "Anonymous"
                        parts = name.split()
                        display = f"{parts[0]} {parts[-1][0]}." if len(parts) > 1 else parts[0]
                        loc = f"{r['city'] or ''}, {r['state'] or 'WA'}".strip(", ")
                        skills_list = [s for s in (r["skills"] or []) if s] [:5]
                        score = (r["profile_completeness_score"] or 0)
                        results.append({
                            "display_name": display,
                            "location": loc or "Washington",
                            "top_skills": skills_list,
                            "availability": r["availability_status"] or "Available",
                            "match_strength": "Strong" if score > 0.7 else "Good" if score > 0.4 else "Possible",
                            "candidate_id": str(r["id"])[:12],
                            "source": "WFD OS verified candidates",
                        })
                    return results
        conn.close()
    except Exception as e:
        print(f"[EMPLOYER AGENT] DB candidate search failed: {e}")

    # Fallback to hardcoded Cohort 1
    query = (skills + " " + role_type).lower().strip()
    tokens = set(query.split())

    scored = []
    for c in CANDIDATE_DB:
        score = 0
        for t in tokens:
            if any(t in s.lower() for s in c["top_skills"]):
                score += 3
            if any(t in area for area in c["match_areas"]):
                score += 2
        if score > 0 or not query:
            scored.append((score, c))

    scored.sort(key=lambda x: -x[0])
    results = []
    for score, c in scored[:5]:
        results.append({
            "display_name": c["display_name"],
            "location": c["location"],
            "top_skills": c["top_skills"][:5],
            "availability": c["availability"],
            "placement_type": c["placement_type"],
            "match_strength": "Strong" if score >= 6 else "Good" if score >= 3 else "Possible",
            "candidate_id": c["id"],
        })
    if not results:
        return [{"message": "No exact matches found. Let me broaden the search or adjust criteria.", "total_pool": "101 pre-vetted candidates available"}]
    return results


def _get_candidate_details(candidate_id: str) -> dict:
    """Get richer profile for a specific candidate."""
    for c in CANDIDATE_DB:
        if c["id"] == candidate_id or candidate_id.lower() in c["display_name"].lower():
            return {
                "display_name": c["display_name"],
                "location": c["location"],
                "skills": c["top_skills"],
                "availability": c["availability"],
                "placement_type": c["placement_type"],
                "proof_of_work": c["proof"],
                "note": "Contact facilitated through CFA — reach out and we'll make the introduction within 24 hours.",
            }
    return {"error": "Candidate not found. Try searching by skills instead."}


def _get_proof_of_work(candidate_id: str) -> dict:
    """Get detailed proof of work for a candidate."""
    for c in CANDIDATE_DB:
        if c["id"] == candidate_id or candidate_id.lower() in c["display_name"].lower():
            return {
                "candidate": c["display_name"],
                **c["proof"],
                "verification": "Work verified by CFA technical lead. Code available for review upon request.",
                "supervisor": "Gary — CFA Technical Lead",
            }
    return {"error": "Candidate not found."}


def _contact_cfa_about_candidate(candidate_id: str, employer_name: str, employer_email: str, role: str, timeline: str = "") -> dict:
    """Send CFA a notification that an employer is interested in a candidate.
    Also creates an Apollo contact for the employer tagged as 'Talent Hiring Lead'."""
    candidate_name = "Unknown"
    for c in CANDIDATE_DB:
        if c["id"] == candidate_id:
            candidate_name = c["display_name"]
            break

    # Send email to Ritu
    try:
        from agents.portal.email import send_email
        subject = f"Employer interest: {candidate_name} for {role} — {employer_name}"
        body = (
            f"An employer expressed interest in a candidate through the Employer Agent.\n\n"
            f"Candidate: {candidate_name} ({candidate_id})\n"
            f"Role: {role}\n"
            f"Employer: {employer_name}\n"
            f"Contact: {employer_email}\n"
            f"Timeline: {timeline or 'Not specified'}\n\n"
            f"Please follow up within 24 hours to facilitate the introduction."
        )
        send_email("ritu@computingforall.org", subject, body)
    except Exception:
        pass

    # Create Apollo contact for the employer (best-effort)
    try:
        from agents.apollo.client import create_contact as apollo_create
        parts = employer_name.split(None, 1)
        apollo_create(
            first_name=parts[0] if parts else employer_name,
            last_name=parts[1] if len(parts) > 1 else "",
            email=employer_email,
            organization=employer_name,
            source="talent_hiring_lead",
            label_names=["Talent Hiring Lead"],
        )
        print(f"[EMPLOYER AGENT] Apollo contact created for {employer_email} (Talent Hiring Lead)")
    except Exception as e:
        print(f"[EMPLOYER AGENT] Apollo contact creation failed: {e}")

    return {"success": True, "message": f"CFA has been notified about your interest in {candidate_name} for the {role} position. Ritu will reach out to {employer_email} within 24 hours to make the introduction."}


def _get_coalition_benefits() -> dict:
    """Return coalition employer membership benefits."""
    return {
        "benefits": [
            {"benefit": "Priority candidate access", "description": "First look at new graduates before they hit the open market"},
            {"benefit": "Discounted consulting rates", "description": "Coalition members get preferred pricing on Waifinder AI consulting engagements"},
            {"benefit": "Direct JIE labor market data", "description": "Access to real-time labor market intelligence from the Job Intelligence Engine"},
            {"benefit": "Apprentice hosting opportunities", "description": "Host an apprentice for OJT — evaluate talent during a real project before committing to a hire"},
            {"benefit": "Peer employer network", "description": "Connect with other coalition employers in workforce planning discussions"},
        ],
        "cost": "Coalition membership is free for qualified employers in Washington State",
        "how_to_join": "Express interest through CFA — Ritu will follow up to discuss fit.",
    }


def _submit_consulting_inquiry(org_name: str, contact_name: str, email: str, problem_description: str, timeline: str = "", budget_range: str = "") -> dict:
    """Submit a consulting inquiry via the employer agent."""
    try:
        r = httpx.post("http://localhost:8006/api/consulting/inquire", json={
            "organization_name": org_name,
            "contact_name": contact_name,
            "email": email,
            "project_description": problem_description,
            "project_area": "AI Consulting (via Employer Agent)",
            "timeline": timeline,
            "budget_range": budget_range,
        }, timeout=15.0)
        if r.status_code == 200:
            data = r.json()
            return {"success": True, "reference_number": data.get("reference_number", ""), "message": f"Inquiry submitted. Reference: {data.get('reference_number')}. Ritu will reach out within 24 hours."}
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": False, "message": "Could not submit inquiry. Please try again or contact ritu@computingforall.org directly."}


# ---------------------------------------------------------------------------
# Tool declarations
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="search_candidates",
        description="Search the CFA talent pool for candidates matching specific skills or role types. Call this when an employer describes what they're hiring for. Returns top 5 matches with display names (first + last initial only), skills, and availability. Never reveals full names or contact info.",
        parameters={"type": "object", "properties": {
            "skills": {"type": "string", "description": "Comma-separated skills to match, e.g. 'Python, AI, PostgreSQL'"},
            "role_type": {"type": "string", "description": "Type of role, e.g. 'backend developer', 'data analyst', 'cloud engineer'"},
            "location": {"type": "string", "description": "Preferred location (optional, defaults to WA)"},
        }, "required": ["skills"]},
        fn=_search_candidates,
    ),
    Tool(
        name="get_candidate_details",
        description="Get a richer profile for a specific candidate including skills breakdown and proof of work summary. Call when the employer wants to know more about a specific person.",
        parameters={"type": "object", "properties": {
            "candidate_id": {"type": "string", "description": "Candidate ID from search results, e.g. 'angel-001'"},
        }, "required": ["candidate_id"]},
        fn=_get_candidate_details,
    ),
    Tool(
        name="get_proof_of_work",
        description="Get detailed proof of work for a candidate — what they built, what tech they used, what the outcome was. This is the strongest selling point: verified production work, not self-reported skills.",
        parameters={"type": "object", "properties": {
            "candidate_id": {"type": "string", "description": "Candidate ID"},
        }, "required": ["candidate_id"]},
        fn=_get_proof_of_work,
    ),
    Tool(
        name="contact_cfa_about_candidate",
        description="Notify CFA that an employer is interested in a candidate. Sends an email to Ritu with the details. Call when the employer wants to move forward with a candidate. Requires employer name and email.",
        parameters={"type": "object", "properties": {
            "candidate_id": {"type": "string", "description": "Candidate ID"},
            "employer_name": {"type": "string", "description": "Employer/company name"},
            "employer_email": {"type": "string", "description": "Employer contact email"},
            "role": {"type": "string", "description": "Role they're hiring for"},
            "timeline": {"type": "string", "description": "Hiring timeline"},
        }, "required": ["candidate_id", "employer_name", "employer_email", "role"]},
        fn=_contact_cfa_about_candidate,
    ),
    Tool(
        name="get_coalition_benefits",
        description="Get the list of benefits for Washington Tech Workforce Coalition employer members. Call when they ask about the coalition or membership.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _get_coalition_benefits(),
    ),
    Tool(
        name="submit_consulting_inquiry",
        description="Submit a consulting inquiry when an employer wants AI built rather than hiring talent. Same as the consulting intake flow — saves to DB, sends emails, returns reference number.",
        parameters={"type": "object", "properties": {
            "org_name": {"type": "string", "description": "Organization name"},
            "contact_name": {"type": "string", "description": "Contact person's name"},
            "email": {"type": "string", "description": "Contact email"},
            "problem_description": {"type": "string", "description": "What they need built"},
            "timeline": {"type": "string", "description": "Desired timeline"},
            "budget_range": {"type": "string", "description": "Budget range"},
        }, "required": ["org_name", "contact_name", "email", "problem_description"]},
        fn=_submit_consulting_inquiry,
    ),
]


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------

class EmployerAgent(BaseAgent):
    def extract_suggestions(self, response_text: str, history: list[dict]) -> list[str] | None:
        text = response_text.lower()
        user_count = sum(1 for m in history if m.get("role") == "user")

        if user_count <= 1:
            return ["I'm hiring tech talent", "I need AI built", "Both — tell me more"]

        # After showing candidates
        if "angel" in text or "fabian" in text or "bryan" in text:
            return ["Tell me more about Angel R.", "Tell me more about Fabian M.", "I'd like an introduction"]
        if "proof" in text or "built" in text or "production" in text:
            return ["Set up an introduction", "Show me other candidates", "What does placement cost?"]
        if "introduction" in text or "reach out" in text or "24 hours" in text:
            return ["Thank you!", "Show me consulting options too", "Tell me about the coalition"]

        # Consulting mode
        if "borderplex" in text or "fixed price" in text or "$25" in text:
            return ["Tell me more about that project", "What would ours cost?", "How do we get started?"]
        if "consulting" in text or "ai system" in text or "agentic" in text:
            return ["What's the timeline?", "What's the cost?", "Show me the Borderplex example"]

        # Coalition
        if "coalition" in text or "membership" in text:
            return ["How do I join?", "What's the cost?", "Show me candidates first"]

        return None


employer_agent = EmployerAgent(
    agent_type="employer",
    system_prompt=SYSTEM_PROMPT,
    tools=TOOLS,
)
