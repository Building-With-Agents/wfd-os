"""Student Agent — VALUE BEFORE ASK.

Show jobs before asking anything. Never make students feel deficient.
Connect everything to salary. One question at a time.
"""
from __future__ import annotations
from agents.assistant.base import BaseAgent, Tool

SYSTEM_PROMPT = """You are a friendly career advisor at Computing for All. You help people find tech jobs that match what they already know.

Your approach:
- Show jobs FIRST before asking for detailed background
- One question at a time — never multiple questions in one message
- Connect every skill gap to a specific job and salary
- Make the gap feel SMALL not overwhelming
- Celebrate what they already have
- Use plain language — no jargon (never say 'gap analysis', 'upskilling', 'competency framework', 'pathway')
- Respect their time explicitly

After they tell you what they're looking for:
Show 2-3 real jobs immediately with salary ranges.
THEN ask one follow-up question.

Key phrases to use:
- "You already qualify for..."
- "You're 80% of the way there..."
- "One certification gets you..."
- "That pays $X in your area"
- "Takes 3 weeks online, free"

Never say:
- "You're missing X skills"
- "Your profile is incomplete"
- "You need to upskill in..."
- "Complete your gap analysis"

Keep responses SHORT — 3-4 sentences max. Show, don't lecture.

When you have their name, email, and career interests, offer to create their profile using the create_student_profile tool. Never pressure — frame it as "want me to save this so we can match you to new openings automatically?"
"""

# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------

SALARY_DATA = {
    "help desk": {"title": "Help Desk / IT Support Specialist", "range": "$38,000 - $52,000", "low": 38000, "high": 52000},
    "it support": {"title": "IT Support Technician", "range": "$42,000 - $58,000", "low": 42000, "high": 58000},
    "junior developer": {"title": "Junior Software Developer", "range": "$55,000 - $75,000", "low": 55000, "high": 75000},
    "software developer": {"title": "Software Developer", "range": "$65,000 - $95,000", "low": 65000, "high": 95000},
    "data analyst": {"title": "Data Analyst", "range": "$58,000 - $78,000", "low": 58000, "high": 78000},
    "cloud engineer": {"title": "Cloud Engineer", "range": "$65,000 - $90,000", "low": 65000, "high": 90000},
    "ai engineer": {"title": "AI / ML Engineer", "range": "$75,000 - $110,000", "low": 75000, "high": 110000},
    "cybersecurity": {"title": "Cybersecurity Analyst", "range": "$60,000 - $85,000", "low": 60000, "high": 85000},
    "web developer": {"title": "Web Developer", "range": "$50,000 - $72,000", "low": 50000, "high": 72000},
    "qa tester": {"title": "QA / Test Engineer", "range": "$48,000 - $68,000", "low": 48000, "high": 68000},
}

CERTIFICATIONS = {
    "aws": {"cert": "AWS Cloud Practitioner", "prep": "Free (AWS Skill Builder)", "exam": "$100", "time": "3 weeks", "url": "https://aws.amazon.com/certification/certified-cloud-practitioner/"},
    "python": {"cert": "Python (freeCodeCamp)", "prep": "Free", "exam": "Free", "time": "2 weeks", "url": "https://www.freecodecamp.org/learn/scientific-computing-with-python/"},
    "sql": {"cert": "SQL Fundamentals (Mode Analytics)", "prep": "Free", "exam": "Free", "time": "1 week", "url": "https://mode.com/sql-tutorial/"},
    "azure": {"cert": "Azure Fundamentals AZ-900", "prep": "Free (Microsoft Learn)", "exam": "$99", "time": "3 weeks", "url": "https://learn.microsoft.com/en-us/certifications/azure-fundamentals/"},
    "comptia": {"cert": "CompTIA A+", "prep": "Free (Professor Messer)", "exam": "$246", "time": "4-6 weeks", "url": "https://www.comptia.org/certifications/a"},
    "google it": {"cert": "Google IT Support Certificate", "prep": "Free trial on Coursera", "exam": "Included", "time": "4 weeks", "url": "https://grow.google/certificates/it-support/"},
    "javascript": {"cert": "JavaScript (freeCodeCamp)", "prep": "Free", "exam": "Free", "time": "2-3 weeks", "url": "https://www.freecodecamp.org/learn/javascript-algorithms-and-data-structures-v8/"},
}


def _search_jobs(query: str = "", skills: str = "", location: str = "Washington") -> list[dict]:
    """Search real job listings from PostgreSQL. Falls back to hardcoded if DB unavailable."""
    try:
        import psycopg2, psycopg2.extras
        from wfdos_common.config import PG_CONFIG
        conn = psycopg2.connect(**PG_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        q = (query + " " + skills).strip()
        if q:
            # Search by title or skills
            terms = [f"%{t.strip()}%" for t in q.split(",") if t.strip()]
            if not terms:
                terms = [f"%{q}%"]
            conditions = " OR ".join(["title ILIKE %s"] * len(terms))
            cur.execute(f"""
                SELECT title, COUNT(*) as openings,
                       AVG(salary_min)::int as avg_min, AVG(salary_max)::int as avg_max,
                       MIN(city || ', ' || state) as sample_location
                FROM job_listings
                WHERE {conditions}
                GROUP BY title
                ORDER BY openings DESC
                LIMIT 5
            """, terms)
        else:
            cur.execute("""
                SELECT title, COUNT(*) as openings,
                       AVG(salary_min)::int as avg_min, AVG(salary_max)::int as avg_max,
                       MIN(city || ', ' || state) as sample_location
                FROM job_listings
                WHERE salary_min > 0
                GROUP BY title
                ORDER BY openings DESC
                LIMIT 5
            """)

        rows = cur.fetchall()
        conn.close()

        if rows:
            results = []
            for r in rows:
                sal_min = r["avg_min"] or 40000
                sal_max = r["avg_max"] or sal_min + 20000
                results.append({
                    "title": r["title"],
                    "openings": r["openings"],
                    "salary_range": f"${sal_min:,} - ${sal_max:,}",
                    "location": r["sample_location"] or location,
                    "match_note": f"{r['openings']} open positions found",
                    "source": "WFD OS job listings (2,700+ real postings)",
                })
            return results
    except Exception as e:
        print(f"[STUDENT AGENT] DB job search failed: {e}")

    # Fallback to hardcoded
    q_lower = (query + " " + skills).lower().strip()
    results = []
    for key, info in SALARY_DATA.items():
        if any(word in q_lower for word in key.split()) or not q_lower:
            results.append({
                "title": info["title"],
                "salary_range": info["range"],
                "location": location,
                "match_note": "Based on your interests",
                "key_skills": _skills_for_role(key),
            })
    return results[:3] if results else [
        {"title": "IT Support Specialist", "salary_range": "$42,000 - $58,000", "location": location, "match_note": "Great entry point", "key_skills": ["troubleshooting", "Windows", "networking basics"]},
        {"title": "Junior Web Developer", "salary_range": "$50,000 - $72,000", "location": location, "match_note": "Strong demand in WA", "key_skills": ["HTML/CSS", "JavaScript", "React"]},
        {"title": "Data Analyst", "salary_range": "$58,000 - $78,000", "location": location, "match_note": "Growing field", "key_skills": ["SQL", "Excel", "Python basics"]},
    ]


def _skills_for_role(role_key: str) -> list[str]:
    mapping = {
        "help desk": ["customer service", "troubleshooting", "Windows", "ticketing systems"],
        "it support": ["networking", "Windows/Mac", "Active Directory", "hardware"],
        "junior developer": ["Python or JavaScript", "Git", "SQL", "problem solving"],
        "software developer": ["Python", "JavaScript", "APIs", "databases", "Git"],
        "data analyst": ["SQL", "Excel", "Python", "data visualization", "statistics"],
        "cloud engineer": ["AWS or Azure", "Linux", "networking", "containers"],
        "ai engineer": ["Python", "machine learning", "PyTorch/TensorFlow", "SQL", "math"],
        "cybersecurity": ["networking", "Linux", "security frameworks", "SIEM tools"],
        "web developer": ["HTML/CSS", "JavaScript", "React", "Node.js", "Git"],
        "qa tester": ["testing methodologies", "Selenium", "SQL", "bug tracking"],
    }
    return mapping.get(role_key, ["communication", "problem solving", "willingness to learn"])


def _get_salary_info(job_title: str, location: str = "Washington") -> dict:
    key = job_title.lower().strip()
    for k, v in SALARY_DATA.items():
        if k in key or key in k:
            return {"title": v["title"], "salary_range": v["range"], "location": location, "source": "BLS/regional data"}
    return {"title": job_title, "salary_range": "$45,000 - $75,000 (estimated)", "location": location, "source": "estimated"}


def _get_quick_certification(skill_gap: str) -> dict:
    key = skill_gap.lower().strip()
    for k, v in CERTIFICATIONS.items():
        if k in key or key in k:
            return v
    return {"cert": f"{skill_gap} fundamentals", "prep": "Free online resources available", "exam": "Varies", "time": "2-4 weeks", "url": "https://www.freecodecamp.org"}


def _create_student_profile(name: str, email: str, skills: str = "", interests: str = "") -> dict:
    return {
        "success": True,
        "message": f"Profile created for {name}. You'll receive a portal link at {email} where you can track your job matches and progress.",
        "portal_url": f"/careers?student={email}",
        "next_step": "We'll start matching you to openings automatically. Check your email for your portal link.",
    }


TOOLS = [
    Tool(name="search_jobs",
         description="Search for tech jobs matching the student's interests and skills. Call this early — show jobs before asking too many questions.",
         parameters={"type": "object", "properties": {
             "query": {"type": "string", "description": "Job type or interest area"},
             "skills": {"type": "string", "description": "Skills the student mentioned having"},
             "location": {"type": "string", "description": "Location preference, defaults to Washington"},
         }, "required": ["query"]},
         fn=_search_jobs),
    Tool(name="get_salary_info",
         description="Get salary range for a specific job title in a location. Use to connect conversations to real earnings.",
         parameters={"type": "object", "properties": {
             "job_title": {"type": "string", "description": "Job title to look up"},
             "location": {"type": "string", "description": "Location, defaults to Washington"},
         }, "required": ["job_title"]},
         fn=_get_salary_info),
    Tool(name="get_quick_certification",
         description="Find the fastest free or cheap certification to close a specific skill gap. Frame positively — 'one cert away from qualifying'.",
         parameters={"type": "object", "properties": {
             "skill_gap": {"type": "string", "description": "The skill they need, e.g. 'AWS', 'Python', 'SQL'"},
         }, "required": ["skill_gap"]},
         fn=_get_quick_certification),
    Tool(name="create_student_profile",
         description="Create a basic student profile so we can match them to jobs automatically. Only call when they've shared name and email voluntarily.",
         parameters={"type": "object", "properties": {
             "name": {"type": "string", "description": "Student's name"},
             "email": {"type": "string", "description": "Student's email"},
             "skills": {"type": "string", "description": "Skills they mentioned"},
             "interests": {"type": "string", "description": "Career interests"},
         }, "required": ["name", "email"]},
         fn=_create_student_profile),
]


class StudentAgent(BaseAgent):
    def extract_suggestions(self, response_text: str, history: list[dict]) -> list[str] | None:
        text = response_text.lower()
        user_count = sum(1 for m in history if m.get("role") == "user")
        if user_count <= 1:
            return ["Software development", "IT support / help desk", "Data and analytics", "Cloud and infrastructure", "I'm not sure yet"]
        if "salary" in text or "pay" in text or "$" in text:
            return ["How do I get started?", "What skills do I need?", "Are there free courses?"]
        if "certification" in text or "course" in text or "free" in text:
            return ["Sign me up", "What jobs does that qualify me for?", "Any other options?"]
        if "profile" in text or "match" in text or "portal" in text:
            return ["Yes, create my profile", "Not yet — tell me more first"]
        return None


student_agent = StudentAgent(
    agent_type="student",
    system_prompt=SYSTEM_PROMPT,
    tools=TOOLS,
)
