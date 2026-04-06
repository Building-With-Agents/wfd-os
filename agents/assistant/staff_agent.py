"""Staff Agent — EVERYTHING IN 60 SECONDS.

Role-aware operations assistant for CFA team.
Pulls real data from existing APIs when available.
"""
from __future__ import annotations
import json
import httpx
from agents.assistant.base import BaseAgent, Tool

SYSTEM_PROMPT_TEMPLATE = """You are the CFA operations assistant. You give CFA staff immediate answers to operational questions.

You know everything about:
- WJI grant K8341 status and closeout
- Consulting pipeline and active projects
- Student cohort progress
- Placement tracking
- Financial status
- Marketing content and campaigns

Current user: {user_role}

Role-specific approach:

If user is ritu (CEO): Lead with the big picture — grant status, consulting pipeline, cohort status, anything needing her attention. She wants cross-system visibility in 60 seconds.

If user is gary (Tech Lead): Lead with cohort briefing — student progress, who needs help, sprint status. He wants to eliminate coordination overhead.

If user is krista (Finance): Lead with financial briefing — outstanding invoices, payroll status, grant burn rate.

If user is bethany (Grants): Lead with grant briefing — placement count toward 730 PIP threshold, provider status, ESD deadlines.

If user is jason (BD): Lead with consulting pipeline — new inquiries, pipeline value, prospects needing follow-up. No student PII or grant financials.

If user is jessica (Marketing): Lead with content status — what needs approval, sequence performance. No student PII or grant financials.

If user is leslie (Youth): Lead with youth program — applications, cohort status, upcoming dates.

Be direct and data-forward. Pull real data using tools when available. When data isn't available yet say: "That data isn't in the system yet — here's how to get it: [specific action]"

Never make up numbers. Always say where data comes from. Keep answers SHORT — bullet points over paragraphs."""


def _get_staff_prompt(user_role: str = "ritu") -> str:
    return SYSTEM_PROMPT_TEMPLATE.format(user_role=user_role or "ritu")


def _get_grant_summary() -> dict:
    try:
        r = httpx.get("http://localhost:8007/api/wji/dashboard", timeout=10.0)
        if r.status_code == 200:
            d = r.json()
            return {
                "source": "WJI API (live data)",
                "placements": d["placements_summary"],
                "payments": d["payments_summary"],
                "recent_uploads": len(d.get("recent_uploads", [])),
                "by_program": d.get("placements_by_program", []),
            }
    except Exception:
        pass
    return {"source": "unavailable", "message": "WJI API not reachable. Start it with: uvicorn agents.portal.wji_api:app --port 8007"}


def _get_consulting_pipeline() -> dict:
    try:
        r = httpx.get("http://localhost:8006/api/consulting/pipeline", timeout=10.0)
        if r.status_code == 200:
            d = r.json()
            return {
                "source": "Consulting API (live data)",
                "stats": d["stats"],
                "recent_inquiries": [{"ref": i.get("reference_number"), "org": i["organization_name"], "status": i["status"]} for i in d["inquiries"][:5]],
                "active_engagements": [{"id": e["id"], "org": e["organization_name"], "progress": e["progress_pct"]} for e in d["engagements"] if e.get("status") == "in_progress"],
            }
    except Exception:
        pass
    return {"source": "unavailable", "message": "Consulting API not reachable."}


def _get_cohort_status() -> dict:
    return {
        "source": "static (OJT tracking not yet built)",
        "cohort_1": {
            "students": ["Angel", "Fabian", "Bryan", "Emilio", "Juan", "Enrique", "Fatima", "Nestor"],
            "count": 8,
            "status": "In training — Waifinder Client 0 delivery",
            "supervisor": "Gary",
            "note": "OJT timesheet tracking not yet in WFD OS. Ask Gary for current sprint status.",
        },
    }


def _get_placement_summary() -> dict:
    try:
        r = httpx.get("http://localhost:8007/api/wji/dashboard", timeout=10.0)
        if r.status_code == 200:
            ps = r.json()["placements_summary"]
            return {
                "source": "WJI API (live data)",
                "total_placements": ps["total_placements"],
                "unique_students": ps["unique_students"],
                "unique_employers": ps["unique_employers"],
                "avg_wage": ps["avg_wage"],
                "target": "730 PIP threshold (grant requirement)",
                "latest": ps["latest_placement"],
            }
    except Exception:
        pass
    return {"source": "unavailable", "message": "WJI API not reachable."}


def _get_recent_inquiries() -> list[dict]:
    try:
        r = httpx.get("http://localhost:8006/api/consulting/pipeline", timeout=10.0)
        if r.status_code == 200:
            return [{"ref": i.get("reference_number"), "org": i["organization_name"], "status": i["status"], "when": i.get("created_at", "")[:10]} for i in r.json()["inquiries"][:5]]
    except Exception:
        pass
    return [{"message": "Consulting API not reachable."}]


def _draft_update(engagement_id: str, title: str, body: str, update_type: str = "progress") -> dict:
    try:
        r = httpx.post(f"http://localhost:8006/api/consulting/engagement/{engagement_id}/updates", json={
            "author": "CFA Staff Agent",
            "author_email": "staff@computingforall.org",
            "update_type": update_type,
            "title": title,
            "body": body,
            "is_client_visible": True,
        }, timeout=10.0)
        if r.status_code == 200:
            return {"success": True, "message": f"Update posted to {engagement_id}", "data": r.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}
    return {"success": False, "message": "Could not post update."}


TOOLS = [
    Tool(name="get_grant_summary", description="Get WJI grant K8341 status — placements, spending, burn rate. Call when asked about the grant, WJI, Alma, or WSB.", parameters={"type": "object", "properties": {}, "required": []}, fn=lambda **_: _get_grant_summary()),
    Tool(name="get_consulting_pipeline", description="Get consulting pipeline stats — new inquiries, active engagements, pipeline value. Call when asked about consulting, pipeline, or revenue.", parameters={"type": "object", "properties": {}, "required": []}, fn=lambda **_: _get_consulting_pipeline()),
    Tool(name="get_cohort_status", description="Get current cohort status — students, progress, who needs help. Call when asked about students, cohort, training, or OJT.", parameters={"type": "object", "properties": {}, "required": []}, fn=lambda **_: _get_cohort_status()),
    Tool(name="get_placement_summary", description="Get placement tracking — count toward 730 PIP threshold, employers, wages. Call when asked about placements or PIP.", parameters={"type": "object", "properties": {}, "required": []}, fn=lambda **_: _get_placement_summary()),
    Tool(name="get_recent_inquiries", description="Get the 5 most recent consulting inquiries with status. Call when asked about new leads or inquiries.", parameters={"type": "object", "properties": {}, "required": []}, fn=lambda **_: _get_recent_inquiries()),
    Tool(name="draft_update", description="Post a project update to a consulting engagement's activity feed. Call when staff wants to update a client on progress.",
         parameters={"type": "object", "properties": {
             "engagement_id": {"type": "string", "description": "Engagement ID e.g. wsb-001"},
             "title": {"type": "string", "description": "Update title"},
             "body": {"type": "string", "description": "Update body text"},
             "update_type": {"type": "string", "description": "Type: progress, milestone, delivery, note"},
         }, "required": ["engagement_id", "title", "body"]},
         fn=_draft_update),
]


class StaffAgent(BaseAgent):
    """Staff agent that customizes the system prompt per user role."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    async def chat(self, session_id=None, user_message="", user_id=None, user_role=None, context=None):
        # Dynamically set the system prompt based on user_role
        self.system_prompt = _get_staff_prompt(user_role or "ritu")
        return await super().chat(session_id, user_message, user_id, user_role, context)


staff_agent = StaffAgent(
    agent_type="staff",
    system_prompt=_get_staff_prompt("ritu"),
    tools=TOOLS,
)
