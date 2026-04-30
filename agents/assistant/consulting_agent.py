"""Consulting Intake Agent — guides prospects to clarity about their AI project.

Principle: GUIDE DON'T PITCH
Goal: Understand the prospect's problem, then trigger INTAKE_COMPLETE with structured data.
Tools: get_case_study, get_blog_post, check_budget_fit, submit_inquiry
"""
from __future__ import annotations


from agents.assistant.base import BaseAgent, Tool

# ---------------------------------------------------------------------------
# System prompt
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a specialist AI advisor at Computing for All (CFA). You have deep expertise in the operational challenges facing workforce development boards, healthcare organizations, professional services firms, and regional employers.

You are NOT a generalist. You know these industries deeply:

WORKFORCE DEVELOPMENT BOARDS:
Common pain points you've seen:
- Manual labor market intelligence: Staff spending 8-15 hours/week pulling job listings, building spreadsheets, analyzing demand signals that are weeks out of date by the time they're ready
- Participant-to-job matching: Case managers doing manual matching between job seekers, training programs, and employer openings — gut feel instead of data
- WIOA/ESD reporting burden: Quarterly reports taking 2 weeks, staff time consumed by data formatting instead of serving participants
- Disconnected systems: Case management, job boards, training providers, employer relationships all in separate systems with no intelligence layer connecting them
- Skills gap visibility: No real-time view of what employers need vs what participants have. Curriculum decisions based on anecdotal employer feedback

HEALTHCARE ORGANIZATIONS:
- Patient data in siloed EHRs that can't answer operational questions
- Manual referral tracking and follow-up coordination
- Scheduling inefficiencies costing revenue and patient satisfaction
- Compliance reporting burden

PROFESSIONAL SERVICES:
- Matter intelligence locked in document management systems
- Billing and engagement data that could predict client needs but doesn't
- Manual client reporting and updates

Your proof of concept:
Workforce Solutions Borderplex — Job Intelligence Engine (JIE)
- Problem: 8-10 hours/week manual labor market data collection
- Solution: 6-agent pipeline — ingestion, normalization, extraction, enrichment, analytics, query interface
- Outcome: Fully automated, processes thousands of job listings weekly, real-time intelligence, natural language query interface for staff
- Timeline: 12 weeks
- Cost: $25,500
- Still running in production today

CFA's model:
- Fixed price ($20-35K typical)
- 10-14 weeks
- Supervised apprentice team
- Try before you hire
- No surprises — scope approved before anything starts

YOUR CONVERSATION APPROACH:

Step 1: Show domain expertise first.
Don't ask them to describe their problem cold — offer them frameworks and options that demonstrate you know their world. Let them recognize themselves in what you describe.

Step 2: Guide with options not questions.
Instead of open-ended "what's your problem" — offer 3-4 specific pain points and ask "does any of this sound familiar?"

Step 3: Go deep on the one that resonates.
Once they pick a pain point go deep: "Tell me more about that — how many hours a week does this take? Who on your team is doing it? What does the data look like when you finally have it?"

Step 4: Paint the after picture.
"Imagine if instead of your team spending 10 hours on this every week you could just ask: what skills are Borderplex employers asking for right now? And get an answer in seconds from live data."

Step 5: Reference Borderplex naturally.
When relevant: "This is actually exactly what we built for Workforce Solutions Borderplex — [specific detail]." Never force it — only when it genuinely maps to their situation.

Step 6: Collect info for scoping.
Once the conversation has substance, naturally transition to: "This sounds like something we could scope. So I can get the right person to follow up — could I get your name, email, and the best way to reach you?"

Step 7: Submit and confirm.
When you have: org name, contact name, email, problem description, and at least rough timeline/budget — call the submit_inquiry tool. Then share the reference number and let them know Ritu will reach out within 24 hours.

OPENING MESSAGE STRATEGY:
On the first message, detect their industry or role from what they say and immediately demonstrate domain knowledge. If they just say "hi" or something vague, ask: "Are you with a workforce board, a healthcare organization, a professional services firm, or something else? That'll help me point you to the most relevant examples."

PRICING:
- Never list prices upfront
- If they ask about cost: "Typical engagements run $20-35K fixed price — but let me understand your situation first so I can tell you if that makes sense for your needs."
- Use the check_budget_fit tool when budget is mentioned

RESPONSE STYLE:
- Keep responses concise — 3-4 sentences maximum. Don't monologue.
- One question or one set of options per message.
- Be warm but not sycophantic.
- Sound like a consultant who has done this before, not a chatbot reciting features.

TOOL USAGE:
- Call get_case_study when the prospect asks about previous work or when Borderplex is relevant
- Call check_budget_fit when budget is mentioned
- Call submit_inquiry ONLY when you have org name, contact name, email, and problem description at minimum. Do NOT output raw JSON — the tool handles everything.

HONESTY:
- If someone is clearly not a fit (too small, wrong type of problem) be honest and helpful — suggest other resources rather than wasting their time.
- If you don't know something, say so rather than guessing."""

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

def _get_case_study() -> dict:
    """Returns the Borderplex JIE case study summary."""
    return {
        "client": "Workforce Solutions Borderplex",
        "location": "El Paso, TX (Borderplex region)",
        "problem": "Manual job market data collection — 8-10 hours/week of staff time compiling labor market intelligence from multiple sources",
        "solution": "6-agent AI pipeline — ingestion, normalization, skills extraction, enrichment, analytics, and natural language query interface",
        "outcome": "Fully automated. Processes thousands of job listings weekly. Real-time labor market intelligence for workforce planning. Staff time reduced from 8-10 hours/week to near zero.",
        "timeline": "12 weeks",
        "cost": "$25,500 fixed price",
        "tech_stack": "Python, PostgreSQL, pgvector, FastAPI, Claude API, Azure",
        "key_metrics": {
            "jobs_processed_weekly": "2,000+",
            "staff_hours_saved": "8-10 per week",
            "skill_extraction_accuracy": "92%+",
            "query_response_time": "under 500ms",
        },
    }


def _get_blog_post(topic: str) -> dict:
    """Returns relevant content based on topic."""
    content_map = {
        "workforce": {
            "title": "How AI Agents Are Transforming Workforce Development",
            "summary": "Workforce boards across the country spend hundreds of hours manually collecting and analyzing labor market data. AI agent pipelines can automate this entirely — from job listing ingestion to skills extraction to demand forecasting. CFA's Job Intelligence Engine for Borderplex is the proof point.",
            "cta": "Talk to us about your workforce data challenges.",
        },
        "healthcare": {
            "title": "Agentic AI for Healthcare Operations",
            "summary": "Healthcare organizations generate massive amounts of operational data that goes underutilized. AI agents can automate credentialing workflows, patient flow optimization, and compliance reporting — reducing admin burden while improving outcomes.",
            "cta": "We're exploring healthcare engagements — let's talk.",
        },
        "legal": {
            "title": "AI-Powered Document Intelligence for Legal Teams",
            "summary": "Law firms and legal departments spend 60-70% of associate time on document review. AI agents can handle contract analysis, due diligence document processing, and regulatory compliance checking at a fraction of the time and cost.",
            "cta": "Let's discuss how AI agents could work for your legal team.",
        },
        "talent": {
            "title": "Building Smarter Talent Pipelines with AI",
            "summary": "Traditional applicant tracking systems miss qualified candidates because they rely on keyword matching. AI-powered talent pipelines use semantic understanding to match candidates to roles based on actual skills and potential, not just resume keywords.",
            "cta": "See how our Talent Showcase works.",
        },
        "reporting": {
            "title": "Automated Grant Reporting with AI Agents",
            "summary": "Grant-funded organizations spend weeks every quarter compiling deliverable reports from multiple tracking systems. AI agents can pull data from disparate sources, reconcile records, and generate board-ready reports automatically.",
            "cta": "We built this for ourselves first — now we're offering it.",
        },
    }
    result = content_map.get(topic.lower().strip(), {
        "title": "How Computing for All Builds Agentic AI Systems",
        "summary": "CFA designs, builds, and operates custom AI agent systems for organizations. Each engagement is fixed-price, delivered in 10-14 weeks by a supervised apprentice team. The first deployment — a Job Intelligence Engine for Workforce Solutions Borderplex — is live and processing thousands of records weekly.",
        "cta": "Tell us about your data challenge.",
    })
    return result


def _check_budget_fit(budget_range: str) -> dict:
    """Evaluates whether a stated budget fits CFA's engagement model."""
    b = budget_range.lower().strip()
    if any(x in b for x in ["under 10", "< 10", "5k", "5,000", "under $10"]):
        return {
            "fit": "below_minimum",
            "message": "That's below our typical engagement minimum. For smaller budgets, I'd suggest exploring grant funding to supplement, or we could scope a focused proof-of-concept that demonstrates value before a larger investment.",
            "suggestion": "Consider a $10-15K scoped POC or explore grant funding options.",
        }
    elif any(x in b for x in ["10k", "10,000", "15k", "15,000", "20k", "10-20", "10 to 20", "under 20", "under $20"]):
        return {
            "fit": "possible",
            "message": "That could work for a more focused engagement — maybe a single-agent proof of concept or a specific automation workflow. We'd scope it tightly to deliver clear value within that budget.",
            "suggestion": "Scope a focused POC around the highest-impact automation.",
        }
    elif any(x in b for x in ["20k", "25k", "30k", "35k", "40k", "50k", "20-", "25-", "30-", "20,000", "25,000", "30,000", "35,000", "40,000", "50,000", "20 to", "25 to"]):
        return {
            "fit": "perfect",
            "message": "That's right in the sweet spot for a full CFA engagement. Our typical projects run $20-35K fixed price and deliver a production-ready agentic system in 10-14 weeks.",
            "suggestion": "Full engagement — multi-agent system with production deployment.",
        }
    elif any(x in b for x in ["50k", "75k", "100k", "over 50", "50,000", "75,000", "100,000", "enterprise"]):
        return {
            "fit": "enterprise",
            "message": "For larger budgets, we can deliver a phased multi-system engagement — multiple agent pipelines, integrations, and ongoing managed services. Let's talk about what a phased roadmap would look like.",
            "suggestion": "Phased delivery — multiple systems over 6-12 months.",
        }
    else:
        return {
            "fit": "unknown",
            "message": "I'd be happy to discuss what's realistic for your situation. Our typical engagements run $20-35K fixed price for a full agentic system delivered in 10-14 weeks.",
            "suggestion": "Let's discuss scope and budget together.",
        }


def _get_workforce_pain_points() -> list[dict]:
    """Returns the 5 common workforce board pain points with CFA solutions."""
    return [
        {
            "pain_point": "Manual labor market intelligence",
            "description": "Staff spending 8-15 hours/week pulling job listings from multiple sources, building spreadsheets, analyzing demand signals that are weeks out of date by the time they reach decision-makers.",
            "how_cfa_solves_it": "We build automated ingestion pipelines that pull from job boards, government sources, and employer postings continuously. Data is normalized, enriched with skills taxonomy, and queryable in real time through a natural language interface.",
            "case_study": "Workforce Solutions Borderplex — reduced 8-10 hours/week of manual work to zero. Their team now asks questions like 'What skills are employers in logistics asking for this month?' and gets answers in seconds.",
        },
        {
            "pain_point": "Participant-to-job matching",
            "description": "Case managers manually reviewing participant profiles against job openings. Matching is based on gut feel and personal knowledge rather than systematic skills analysis. Good matches get missed. Bad matches waste employer and participant time.",
            "how_cfa_solves_it": "We build vector-based matching engines that compare participant skills profiles against job requirements using semantic similarity — not just keyword matching. Every participant gets a ranked match list updated automatically as new jobs come in.",
            "case_study": "Our internal talent pipeline uses this approach to match 100+ students to employer openings with 85%+ match quality scores.",
        },
        {
            "pain_point": "WIOA/ESD reporting burden",
            "description": "Quarterly reports taking 2+ weeks of staff time. Data pulled manually from multiple systems, formatted into templates, checked for accuracy. Staff time consumed by data formatting instead of serving participants.",
            "how_cfa_solves_it": "We build automated reporting agents that pull data from your existing systems, reconcile records, and generate board-ready reports on demand. What used to take 2 weeks takes minutes.",
            "case_study": "Our WJI grant reporting system auto-reconciles placement data against payment records and generates compliance reports from uploaded WSAC Excel files and QuickBooks exports.",
        },
        {
            "pain_point": "Disconnected systems",
            "description": "Case management in one system, job boards in another, training provider data in spreadsheets, employer relationships in email or CRM. No intelligence layer connecting them. Staff spend more time navigating between systems than using the data.",
            "how_cfa_solves_it": "We build an orchestration layer that sits on top of your existing systems — doesn't replace them, but connects them. AI agents pull from every source and provide a unified view through conversational interfaces and dashboards.",
            "case_study": "WFD OS connects PostgreSQL, Dynamics CRM, SharePoint, Azure Blob Storage, and external job APIs into a single intelligence layer with role-based access.",
        },
        {
            "pain_point": "Skills gap visibility",
            "description": "No real-time view of what employers need vs what participants have. Curriculum and training decisions based on anecdotal employer feedback or last year's data. By the time a skills gap is identified, employers have moved on.",
            "how_cfa_solves_it": "We build skills demand analysis pipelines that continuously extract and track what skills employers are asking for, compare against participant profiles, and surface actionable gaps. Training providers can see exactly which skills to prioritize.",
            "case_study": "The Borderplex JIE extracts skills from thousands of job postings weekly and maps them to standardized taxonomies, giving workforce planners real-time demand signals by industry and region.",
        },
    ]


def _get_industry_context(industry: str) -> dict:
    """Returns industry-specific talking points."""
    contexts = {
        "workforce": {
            "industry": "Workforce Development",
            "typical_org": "Regional workforce boards, WDBs, one-stop career centers, state workforce agencies",
            "key_challenges": [
                "Labor market intelligence is manual and stale",
                "Participant matching relies on case manager judgment",
                "WIOA reporting consumes weeks of staff time quarterly",
                "Systems are siloed — no unified intelligence layer",
                "Skills gap data is anecdotal, not real-time",
            ],
            "cfa_angle": "CFA built the Job Intelligence Engine for Workforce Solutions Borderplex — the exact technology that solves these problems. We know WIOA compliance, ESD reporting, and the dynamics of matching participants to employer needs.",
            "typical_engagement": "$20-30K, 12-14 weeks, focused on one or two of these pain points initially",
            "roi_framing": "If 3 staff members save 10 hours/week each, that's 1,560 hours/year recovered — worth far more than the engagement cost.",
        },
        "healthcare": {
            "industry": "Healthcare",
            "typical_org": "Hospitals, health systems, FQHCs, specialty practices, behavioral health organizations",
            "key_challenges": [
                "EHR data siloed — can't answer operational questions across systems",
                "Referral tracking and follow-up is manual and error-prone",
                "Scheduling inefficiencies cost revenue and patient satisfaction",
                "Compliance reporting (CMS, Joint Commission, state) consumes clinical admin time",
                "Population health data exists but isn't actionable",
            ],
            "cfa_angle": "Healthcare organizations have enormous amounts of structured and unstructured data that AI agents can make actionable — from referral routing to compliance reporting to patient flow optimization.",
            "typical_engagement": "$25-40K, 12-16 weeks, starting with the highest-impact operational bottleneck",
            "roi_framing": "A single scheduling optimization agent can recover 5-15% of lost appointment slots — typically tens of thousands in monthly revenue.",
        },
        "professional_services": {
            "industry": "Professional Services",
            "typical_org": "Law firms, consulting firms, accounting firms, engineering firms",
            "key_challenges": [
                "Matter intelligence locked in document management systems",
                "Billing data that could predict client needs but doesn't",
                "Manual client reporting consuming associate time",
                "Knowledge management — institutional knowledge in people's heads, not systems",
                "Client relationship intelligence — no unified view of engagement history",
            ],
            "cfa_angle": "Professional services firms sit on goldmines of structured data (billing, matter management, CRM) that AI agents can turn into client intelligence, efficiency gains, and predictive insights.",
            "typical_engagement": "$25-35K, 10-12 weeks, typically starting with document intelligence or automated reporting",
            "roi_framing": "Automating client reporting alone can save 5-10 associate hours per client per month.",
        },
        "employer": {
            "industry": "Regional Employers / HR",
            "typical_org": "Mid-size employers, HR departments, talent acquisition teams",
            "key_challenges": [
                "Talent pipeline visibility — no way to see qualified candidates before posting",
                "Skills-based hiring is talked about but not implemented",
                "Recruiting spend is high but quality of hire is inconsistent",
                "Workforce planning relies on lagging indicators",
            ],
            "cfa_angle": "CFA connects employers to a pre-vetted talent pipeline of trained candidates with verified skills. Our AI matching goes beyond resumes to actual demonstrated competencies.",
            "typical_engagement": "Talent Showcase access (free for qualified employers) or custom talent pipeline integration ($15-25K)",
            "roi_framing": "Reducing time-to-fill by even 2 weeks on a technical role saves $5-10K in lost productivity per hire.",
        },
    }
    key = industry.lower().strip().replace(" ", "_")
    for k in contexts:
        if k in key or key in k:
            return contexts[k]
    return contexts["workforce"]


def _get_similar_clients(industry: str = "workforce", problem_type: str = "") -> list[dict]:
    """Returns anonymized similar client descriptions."""
    examples = {
        "workforce": [
            {
                "description": "A workforce board in the Southwest was spending 12 hours a week across three staff members compiling labor market data from USAJobs, BLS, and local employer postings. Reports were always 2-3 weeks behind real demand.",
                "outcome": "We built an automated pipeline that ingests from all three sources continuously. Staff now query live data through a conversational interface. 12 hours/week reduced to near zero.",
                "engagement_size": "$25,500 over 12 weeks",
                "named": True,
                "name": "Workforce Solutions Borderplex",
            },
            {
                "description": "A state workforce agency needed to match 500+ program participants to training pathways based on employer demand signals in their region. Case managers were doing this manually with spreadsheets.",
                "outcome": "Built a skills-based matching engine using vector embeddings. Each participant gets auto-matched to the most relevant training programs and job openings. Updated weekly.",
                "engagement_size": "In scoping",
                "named": False,
            },
        ],
        "healthcare": [
            {
                "description": "A community health center network with 8 locations had patient referral data in three different systems. Follow-up coordination was manual and referral completion rates were below 60%.",
                "outcome": "Exploring: an AI orchestration layer that unifies referral data across systems and auto-generates follow-up sequences with status tracking.",
                "engagement_size": "In scoping",
                "named": False,
            },
        ],
        "professional_services": [
            {
                "description": "A regional law firm with 50 attorneys had 15 years of matter data in their DMS but no way to find relevant precedents or predict which clients were likely to need additional services.",
                "outcome": "Exploring: document intelligence agent that indexes matter files and surfaces relevant precedents and cross-sell signals automatically.",
                "engagement_size": "In scoping",
                "named": False,
            },
        ],
    }
    key = industry.lower().strip()
    for k in examples:
        if k in key or key in k:
            return examples[k]
    return examples["workforce"]


def _submit_inquiry(
    org_name: str,
    contact_name: str,
    email: str,
    phone: str = "",
    problem_description: str = "",
    success_criteria: str = "",
    timeline: str = "",
    budget_range: str = "",
    project_type: str = "",
    full_transcript: str = "",
    data_sources: str = "",
) -> dict:
    """Submit the inquiry to the consulting API — saves to DB, sends emails, returns reference number."""
    import httpx

    # Call the real consulting API endpoint
    payload = {
        "organization_name": org_name,
        "contact_name": contact_name,
        "email": email,
        "phone": phone or "",
        "is_coalition_member": False,
        "project_description": problem_description,
        "problem_statement": problem_description,
        "success_criteria": success_criteria,
        "project_area": project_type or "AI Consulting",
        "timeline": timeline,
        "budget_range": budget_range,
    }

    try:
        r = httpx.post(
            "http://localhost:8006/api/consulting/inquire",
            json=payload,
            timeout=15.0,
        )
        if r.status_code == 200:
            data = r.json()
            return {
                "success": True,
                "reference_number": data.get("reference_number", ""),
                "message": f"Inquiry submitted successfully. Reference number: {data.get('reference_number', 'N/A')}. Confirmation email sent to {email}. Ritu will reach out within 24 hours.",
            }
        else:
            return {
                "success": False,
                "error": f"API returned {r.status_code}",
                "message": "I wasn't able to save your inquiry automatically. Let me make sure Ritu gets your information directly.",
            }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "message": "I wasn't able to save your inquiry automatically, but don't worry — I'll make sure Ritu gets your information.",
        }


# ---------------------------------------------------------------------------
# Tool declarations (Gemini function calling format)
# ---------------------------------------------------------------------------

TOOLS = [
    Tool(
        name="get_case_study",
        description="Get the Borderplex JIE case study details to reference in conversation. Call this when the prospect asks about previous work, proof of concept, or examples.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _get_case_study(),
    ),
    Tool(
        name="get_blog_post",
        description="Get relevant content about a specific industry or topic. Use to share relevant insights with the prospect.",
        parameters={
            "type": "object",
            "properties": {
                "topic": {
                    "type": "string",
                    "description": "Topic to get content about: workforce, healthcare, legal, talent, reporting, or general",
                },
            },
            "required": ["topic"],
        },
        fn=lambda topic="general", **_: _get_blog_post(topic),
    ),
    Tool(
        name="get_workforce_pain_points",
        description="Get detailed information about the 5 most common workforce board pain points, how CFA solves each, and relevant case studies. Use this early in the conversation when talking to a workforce board prospect to show domain expertise.",
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _get_workforce_pain_points(),
    ),
    Tool(
        name="get_industry_context",
        description="Get industry-specific talking points including typical organizations, key challenges, CFA's angle, typical engagement size, and ROI framing. Use this when you know the prospect's industry to calibrate your conversation.",
        parameters={
            "type": "object",
            "properties": {
                "industry": {
                    "type": "string",
                    "description": "Industry: workforce, healthcare, professional_services, or employer",
                },
            },
            "required": ["industry"],
        },
        fn=lambda industry="workforce", **_: _get_industry_context(industry),
    ),
    Tool(
        name="get_similar_clients",
        description="Get anonymized descriptions of similar client engagements by industry and problem type. Use to show the prospect that CFA has relevant experience without revealing confidential client details (except Borderplex which is a named case study).",
        parameters={
            "type": "object",
            "properties": {
                "industry": {
                    "type": "string",
                    "description": "Industry: workforce, healthcare, or professional_services",
                },
                "problem_type": {
                    "type": "string",
                    "description": "Type of problem: labor_market, matching, reporting, systems, skills_gap",
                },
            },
            "required": ["industry"],
        },
        fn=lambda industry="workforce", problem_type="", **_: _get_similar_clients(industry, problem_type),
    ),
    Tool(
        name="check_budget_fit",
        description="Check whether the prospect's stated budget range fits CFA's engagement model. Call this when budget is mentioned to calibrate your response.",
        parameters={
            "type": "object",
            "properties": {
                "budget_range": {
                    "type": "string",
                    "description": "The budget range stated by the prospect, e.g. '$25K-$50K' or 'under $10K'",
                },
            },
            "required": ["budget_range"],
        },
        fn=lambda budget_range="", **_: _check_budget_fit(budget_range),
    ),
    Tool(
        name="submit_inquiry",
        description="Submit the consulting inquiry to the CFA system. Call this ONLY when you have gathered: organization name, contact name, email, problem description, and at least a rough timeline and budget. This saves the inquiry, sends confirmation emails, and returns a reference number.",
        parameters={
            "type": "object",
            "properties": {
                "org_name": {"type": "string", "description": "Organization name"},
                "contact_name": {"type": "string", "description": "Contact person's full name"},
                "email": {"type": "string", "description": "Contact email address"},
                "phone": {"type": "string", "description": "Phone number (optional)"},
                "problem_description": {"type": "string", "description": "What they need built — the core problem and desired solution"},
                "success_criteria": {"type": "string", "description": "What success looks like to them"},
                "timeline": {"type": "string", "description": "Desired timeline"},
                "budget_range": {"type": "string", "description": "Budget range"},
                "project_type": {"type": "string", "description": "Type of project (e.g., workforce intelligence, document automation, talent matching)"},
                "data_sources": {"type": "string", "description": "Data sources they mentioned having available"},
            },
            "required": ["org_name", "contact_name", "email", "problem_description"],
        },
        fn=_submit_inquiry,
    ),
]


# ---------------------------------------------------------------------------
# Agent instance
# ---------------------------------------------------------------------------

class ConsultingAgent(BaseAgent):
    """Consulting intake agent with contextual suggested replies."""

    def extract_suggestions(self, response_text: str, history: list[dict]) -> list[str] | None:
        """Return suggested reply pills based on where the conversation is."""
        text_lower = response_text.lower()
        user_count = sum(1 for m in history if m.get("role") == "user")

        # After intake complete — no suggestions needed
        if "INQ-" in response_text and "reference" in text_lower:
            return None

        # Opening / first exchange — offer industry or pain point options
        if user_count <= 1:
            if "workforce" in text_lower and "healthcare" in text_lower:
                return ["Workforce board", "Healthcare organization", "Professional services firm", "Something else"]
            if any(x in text_lower for x in ["labor market", "participant matching", "reporting", "disconnected", "skills gap"]):
                return ["Labor market intelligence", "Participant matching", "Reporting burden", "Something different"]

        # If agent just asked about timeline or budget
        if "timeline" in text_lower or "when" in text_lower and "start" in text_lower:
            return ["Within 3 months", "3-6 months", "Just exploring for now"]
        if "budget" in text_lower or "invest" in text_lower:
            return ["$10-20K range", "$20-35K range", "$35K+", "Not sure yet"]

        # If agent asked for contact info
        if "email" in text_lower and ("follow up" in text_lower or "reach" in text_lower or "contact" in text_lower):
            return None  # Let them type naturally

        # If agent offered to show case study or examples
        if "borderplex" in text_lower or "case study" in text_lower or "example" in text_lower:
            return ["Tell me more about that", "How long did it take?", "What did it cost?"]

        # If agent just painted an after picture
        if "imagine" in text_lower:
            return ["That sounds great", "How would that work for us?", "What would it cost?"]

        # Default — no suggestions
        return None


consulting_agent = ConsultingAgent(
    agent_type="consulting",
    system_prompt=SYSTEM_PROMPT,
    tools=TOOLS,
)
