"""Youth Agent — MAKE TECH FEEL ACCESSIBLE.

Warm, encouraging, simple language. Many visitors have zero tech background.
"""
from __future__ import annotations
from agents.assistant.base import BaseAgent, Tool

SYSTEM_PROMPT = """You are a friendly guide for the Computing for All Youth Program (Tech Career Bridge).

You help young people aged 16-24 in Washington State discover tech careers and apply to our free program.

Many visitors:
- Have never written code
- Don't think of themselves as "tech people"
- Are first-generation college students
- May be skeptical that tech is for them

Your job is to make tech feel possible and exciting for THEM — not for a stereotype of who "tech people" are.

Use simple language. No jargon. Short sentences. Warm tone.

Key facts about the program:
- Free for WA State residents aged 16-24
- Financial assistance available for transportation, childcare, supplies
- No experience required — we teach everything from scratch
- Full stack web development curriculum
- Leads to real jobs paying $45,000 - $75,000
- CFA helps with job placement after the program
- Classes are in person in the Seattle/Bellevue area
- Program runs 12 weeks

Never make them feel like they need to already know things. Celebrate curiosity over credentials.

Keep responses SHORT — 2-3 sentences max. Use bullet points for lists. Be encouraging without being cheesy.

If they seem nervous about applying, normalize it: "Most of our students felt the same way before starting. You don't need to know anything yet — that's literally what the program is for."
"""


def _get_program_info() -> dict:
    return {
        "name": "Tech Career Bridge",
        "organization": "Computing for All",
        "location": "Seattle/Bellevue, WA (in person)",
        "cost": "Free",
        "age_range": "16-24 years old",
        "residency": "Washington State residents",
        "experience_required": "None — we teach everything from scratch",
        "curriculum": ["HTML & CSS", "JavaScript", "React", "Node.js", "Databases (SQL)", "Git & GitHub", "Professional skills"],
        "duration": "12 weeks",
        "schedule": "Monday-Friday, daytime",
        "outcomes": {"job_placement_rate": "75%+", "average_starting_salary": "$45,000 - $75,000", "employer_partners": "50+ coalition employers"},
        "support": ["Financial assistance for transportation", "Childcare support", "Laptop provided during program", "Career coaching", "Job placement assistance"],
    }


def _get_application_steps() -> dict:
    return {
        "steps": [
            {"step": 1, "title": "Fill out the application", "description": "Basic info — name, age, location. Takes about 10 minutes.", "url": "/youth#apply"},
            {"step": 2, "title": "Short interview", "description": "A casual 15-minute conversation. We want to hear about YOU — your interests, your goals. No technical questions.", "url": None},
            {"step": 3, "title": "Acceptance", "description": "We'll let you know within 2 weeks. Most applicants are accepted.", "url": None},
            {"step": 4, "title": "Orientation", "description": "Meet your cohort, get your laptop, tour the space. The fun starts here!", "url": None},
        ],
        "deadlines": "Rolling admissions — apply anytime. Next cohort starts soon.",
        "what_we_look_for": "Curiosity and commitment. That's it. No grades, no test scores, no experience required.",
    }


def _get_career_paths() -> list[dict]:
    return [
        {"title": "Web Developer", "description": "Build websites and apps that people use every day. Think Instagram, Spotify, or your favorite online store.", "salary": "$50,000 - $72,000", "entry_path": "This is what our program teaches! You'll be job-ready in 12 weeks."},
        {"title": "Help Desk / IT Support", "description": "Help people solve computer problems. Every company needs this — great way to get your foot in the door.", "salary": "$38,000 - $52,000", "entry_path": "Some of our graduates start here and move into development within a year."},
        {"title": "Data Analyst", "description": "Turn numbers into answers. Help companies understand what's happening in their business.", "salary": "$58,000 - $78,000", "entry_path": "Our SQL and database training gives you a strong foundation for this path."},
        {"title": "QA / Software Tester", "description": "Find bugs before users do. You get paid to break things (on purpose).", "salary": "$48,000 - $68,000", "entry_path": "Great option if you're detail-oriented. Our program covers testing fundamentals."},
    ]


def _get_financial_assistance() -> dict:
    return {
        "program_cost": "Free — $0 tuition",
        "available_support": [
            {"type": "Transportation", "description": "Bus pass or gas stipend provided", "amount": "Up to $150/month"},
            {"type": "Childcare", "description": "Childcare assistance for parents in the program", "amount": "Case-by-case basis"},
            {"type": "Supplies", "description": "Laptop loaned for duration of program, plus supplies", "amount": "Included"},
            {"type": "Emergency fund", "description": "Small emergency fund available for unexpected needs during the program", "amount": "Up to $500"},
        ],
        "note": "We don't want money to be the reason you can't participate. Talk to us about your situation — we'll figure it out together.",
    }


TOOLS = [
    Tool(name="get_program_info", description="Get full details about the Tech Career Bridge program — cost, eligibility, curriculum, schedule, outcomes. Call when they ask about the program.",
         parameters={"type": "object", "properties": {}, "required": []}, fn=lambda **_: _get_program_info()),
    Tool(name="get_application_steps", description="Get step-by-step application instructions. Call when they ask how to apply.",
         parameters={"type": "object", "properties": {}, "required": []}, fn=lambda **_: _get_application_steps()),
    Tool(name="get_career_paths", description="Get beginner-friendly tech career descriptions with real salary ranges. Call when they ask about jobs or what they could do after.",
         parameters={"type": "object", "properties": {}, "required": []}, fn=lambda **_: _get_career_paths()),
    Tool(name="get_financial_assistance", description="Get available financial aid, stipends, and support programs. Call when they ask about cost, money, or whether they can afford it.",
         parameters={"type": "object", "properties": {}, "required": []}, fn=lambda **_: _get_financial_assistance()),
]


class YouthAgent(BaseAgent):
    def extract_suggestions(self, response_text: str, history: list[dict]) -> list[str] | None:
        text = response_text.lower()
        user_count = sum(1 for m in history if m.get("role") == "user")
        if user_count <= 1:
            return ["What does the program teach?", "How do I apply?", "What jobs can I get?", "Is it really free?"]
        if "apply" in text or "application" in text:
            return ["I want to apply!", "What do I need to prepare?", "When does the next one start?"]
        if "salary" in text or "$" in text or "pay" in text:
            return ["How do I get started?", "Do I need experience?", "Tell me about the program"]
        if "free" in text or "cost" in text or "financial" in text:
            return ["I need help with transportation", "I need childcare support", "I'm ready to apply"]
        if "experience" in text or "never coded" in text or "no background" in text:
            return ["That's reassuring!", "What will I learn?", "How long is the program?"]
        return None


youth_agent = YouthAgent(
    agent_type="youth",
    system_prompt=SYSTEM_PROMPT,
    tools=TOOLS,
)
