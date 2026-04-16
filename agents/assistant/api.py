"""
Conversational Agent API — serves all six WFD OS agents on port 8009.

Endpoints:
  POST /api/assistant/chat          — send a message, get a response
  GET  /api/assistant/session/{id}  — retrieve full conversation history
  GET  /api/health                  — service health check

Run: uvicorn agents.assistant.api:app --port 8009
"""
from __future__ import annotations

import uuid
from typing import Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# wfdos_common.config auto-loads the repo .env via python-dotenv find_dotenv.
# Pre-#27 this file had sys.path.insert hacks; the monorepo root pyproject.toml
# (#27) now exposes `agents.*` as a namespace package.
from agents.assistant.base import BaseAgent, _load_session
from agents.assistant.consulting_agent import consulting_agent
from agents.assistant.employer_agent import employer_agent
from agents.assistant.student_agent import student_agent
from agents.assistant.staff_agent import staff_agent
from agents.assistant.college_agent import college_agent
from agents.assistant.youth_agent import youth_agent

app = FastAPI(title="WFD OS Conversational Agent API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Agent registry — one BaseAgent instance per agent_type
# ---------------------------------------------------------------------------

# Default prompts for the base framework test. Each agent file will override
# these with rich, persona-specific prompts + tools when built.

_DEFAULT_PROMPTS = {
    "consulting": (
        "You are the Computing for All AI consulting intake assistant. "
        "Your principle is GUIDE DON'T PITCH. Your goal is to help prospects "
        "understand how CFA can build agentic AI systems for their organization. "
        "Ask clarifying questions about their problem, timeline, and budget. "
        "Never be pushy. Reference the Borderplex workforce project naturally "
        "when relevant. When you have enough information to scope a project, "
        "say INTAKE_COMPLETE. If the prospect needs to talk to a human, "
        "say HANDOFF_TO_HUMAN."
    ),
    "employer": (
        "You are the Computing for All employer assistant. "
        "Your principle is TRUST BEFORE ACTION. Help employers find qualified "
        "candidates from the CFA talent pipeline or explore consulting services. "
        "Show proof of work and verified skills, not just profiles."
    ),
    "student": (
        "You are the Computing for All career assistant. "
        "Your principle is VALUE BEFORE ASK. Help students find jobs, "
        "understand their skills gaps, and take the next step toward employment. "
        "Connect everything to salary outcomes. One question at a time."
    ),
    "staff": (
        "You are the CFA internal operations assistant. "
        "Your principle is EVERYTHING IN 60 SECONDS. Answer any operational "
        "question immediately using the available tools. You serve Ritu (CEO), "
        "Gary (Tech Lead), and the CFA team. Eliminate admin overhead."
    ),
    "college": (
        "You are the Computing for All college partner assistant. "
        "Your principle is DATA THAT CHANGES DECISIONS. Help college partners "
        "understand employer demand, curriculum gaps, and graduate placement outcomes."
    ),
    "youth": (
        "You are the Computing for All Tech Career Bridge assistant. "
        "Your principle is MAKE TECH FEEL ACCESSIBLE. Help young people "
        "understand tech career paths, the application process, and available "
        "financial assistance. Be warm, encouraging, and jargon-free."
    ),
}


_REGISTERED_AGENTS: dict[str, BaseAgent] = {
    "consulting": consulting_agent,
    "employer": employer_agent,
    "student": student_agent,
    "staff": staff_agent,
    "college": college_agent,
    "youth": youth_agent,
}


def _get_agent(agent_type: str) -> BaseAgent:
    """Return the agent for the given type.

    Uses a fully-configured agent if one has been registered (e.g. consulting_agent
    with its tools + persona prompt). Falls back to a default-prompt BaseAgent for
    agent types that haven't been built yet.
    """
    if agent_type in _REGISTERED_AGENTS:
        return _REGISTERED_AGENTS[agent_type]

    prompt = _DEFAULT_PROMPTS.get(agent_type)
    if not prompt:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown agent_type '{agent_type}'. "
                   f"Valid types: {', '.join(sorted(set(list(_REGISTERED_AGENTS.keys()) + list(_DEFAULT_PROMPTS.keys()))))}",
        )
    return BaseAgent(agent_type=agent_type, system_prompt=prompt)


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------

class ChatRequest(BaseModel):
    session_id: Optional[str] = None
    agent_type: str
    user_role: Optional[str] = None
    message: str
    user_id: Optional[str] = None
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str
    action: Optional[dict] = None
    signals: Optional[list] = None
    suggestions: Optional[list[str]] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/assistant/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """Send a message to a conversational agent and get a response."""
    agent = _get_agent(req.agent_type)

    # Generate session_id if not provided
    session_id = req.session_id or str(uuid.uuid4())

    result = await agent.chat(
        session_id=session_id,
        user_message=req.message,
        user_id=req.user_id,
        user_role=req.user_role,
        context=req.context,
    )

    return ChatResponse(
        response=result["response"],
        session_id=result["session_id"],
        action=result.get("action"),
        signals=result.get("signals"),
        suggestions=result.get("suggestions"),
    )


@app.get("/api/assistant/session/{session_id}")
def get_session(session_id: str):
    """Retrieve full conversation history for a session."""
    session = _load_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Serialize dates
    for key in ("created_at", "updated_at"):
        if session.get(key):
            session[key] = session[key].isoformat()
    session["id"] = str(session["id"])
    session["session_id"] = str(session["session_id"])

    return session


@app.get("/api/assistant/agents")
def list_agents():
    """List available agent types."""
    return {
        "agents": [
            {"type": k, "prompt_preview": v[:80] + "..."}
            for k, v in sorted(_DEFAULT_PROMPTS.items())
        ]
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "assistant-api", "port": 8009}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8009)
