"""Base conversational agent framework.

Every agent is a BaseAgent subclass (or just an instance with a custom system
prompt + tool list). The framework handles:

  1. Session persistence (agent_conversations table)
  2. Gemini chat with system prompt + history
  3. Tool calling loop (call tool -> feed result -> let LLM respond)
  4. Special signal detection (INTAKE_COMPLETE, HANDOFF_TO_HUMAN)
  5. Structured action extraction from responses

Usage:
    agent = BaseAgent(
        agent_type="consulting",
        system_prompt="You are the CFA consulting intake assistant...",
        tools=[submit_inquiry_tool, get_case_study_tool],
    )
    result = await agent.chat(
        session_id="abc-123",
        user_message="Hi, I need help building an AI system",
    )
    # result = {"response": "...", "session_id": "abc-123", "action": None}
"""
from __future__ import annotations

import json
import os
import sys
import traceback
import uuid
from datetime import datetime, timezone
from typing import Any, Callable, Optional

import google.generativeai as genai
import psycopg2
import psycopg2.extras

# Repo root on sys.path so agents.* imports resolve
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_REPO_ROOT, ".env"), override=False)

sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
from pgconfig import PG_CONFIG  # noqa: E402

# Configure Gemini once at module level
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

DEFAULT_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MAX_TOOL_ROUNDS = 5  # safety limit on consecutive tool calls


# ---------------------------------------------------------------------------
# Tool registry helpers
# ---------------------------------------------------------------------------

class Tool:
    """Wrapper that pairs a callable with its Gemini function declaration."""

    def __init__(
        self,
        name: str,
        description: str,
        parameters: dict,
        fn: Callable[..., Any],
    ):
        self.name = name
        self.description = description
        self.parameters = parameters  # JSON Schema for params
        self.fn = fn

    def to_gemini_declaration(self) -> dict:
        """Return the dict Gemini expects inside `tools=[...]`."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        }

    def execute(self, **kwargs) -> str:
        """Run the tool and return a JSON-serializable string result."""
        try:
            result = self.fn(**kwargs)
            if isinstance(result, str):
                return result
            return json.dumps(result, default=str)
        except Exception as e:
            return json.dumps({"error": f"{type(e).__name__}: {e}"})


def tool(name: str, description: str, parameters: dict):
    """Decorator to register a function as a Tool.

    Usage:
        @tool("search_jobs", "Search for job listings", {
            "type": "object",
            "properties": {"query": {"type": "string", "description": "Search query"}},
            "required": ["query"],
        })
        def search_jobs(query: str) -> dict:
            ...
    """
    def decorator(fn: Callable) -> Tool:
        return Tool(name=name, description=description, parameters=parameters, fn=fn)
    return decorator


# ---------------------------------------------------------------------------
# Special signals detected in LLM output
# ---------------------------------------------------------------------------

SIGNALS = {
    "INTAKE_COMPLETE": "submit_inquiry",
    "HANDOFF_TO_HUMAN": "notify_human",
}


def _detect_signals(text: str) -> list[dict]:
    """Scan LLM response text for special signal markers."""
    found = []
    for marker, action_type in SIGNALS.items():
        if marker in text:
            found.append({"type": action_type, "signal": marker})
    return found


# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def _get_conn():
    return psycopg2.connect(**PG_CONFIG)


def _load_session(session_id: str) -> dict | None:
    conn = _get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM agent_conversations WHERE session_id = %s", (session_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def _save_session(
    session_id: str,
    agent_type: str,
    messages: list[dict],
    user_id: str | None = None,
    user_role: str | None = None,
    outcome: str = "browsing",
    metadata: dict | None = None,
) -> None:
    conn = _get_conn()
    cur = conn.cursor()
    # Upsert on session_id
    cur.execute("""
        INSERT INTO agent_conversations
            (session_id, agent_type, messages, user_id, user_role, outcome, metadata)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (session_id) DO UPDATE SET
            messages = EXCLUDED.messages,
            outcome = EXCLUDED.outcome,
            metadata = EXCLUDED.metadata,
            updated_at = NOW()
    """, (
        session_id,
        agent_type,
        json.dumps(messages, default=str),
        user_id,
        user_role,
        outcome,
        json.dumps(metadata or {}),
    ))
    conn.commit()
    conn.close()


# ---------------------------------------------------------------------------
# Need a unique index on session_id for the upsert
# ---------------------------------------------------------------------------

def _ensure_unique_index():
    """Create unique index if missing (idempotent)."""
    try:
        conn = _get_conn()
        cur = conn.cursor()
        cur.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS ix_agent_conv_session_unique
            ON agent_conversations(session_id)
        """)
        conn.commit()
        conn.close()
    except Exception:
        pass

_ensure_unique_index()


# ---------------------------------------------------------------------------
# BaseAgent
# ---------------------------------------------------------------------------

class BaseAgent:
    """Core conversational agent powered by Gemini Flash."""

    def __init__(
        self,
        agent_type: str,
        system_prompt: str,
        tools: list[Tool] | None = None,
        model: str | None = None,
    ):
        self.agent_type = agent_type
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.model_name = model or DEFAULT_MODEL
        self._tool_map = {t.name: t for t in self.tools}

    def _build_gemini_tools(self) -> list | None:
        """Build the Gemini tools parameter."""
        if not self.tools:
            return None
        declarations = [t.to_gemini_declaration() for t in self.tools]
        return [genai.protos.Tool(function_declarations=[
            genai.protos.FunctionDeclaration(
                name=d["name"],
                description=d["description"],
                parameters=genai.protos.Schema(**self._schema_to_proto(d["parameters"])),
            )
            for d in declarations
        ])]

    def _schema_to_proto(self, schema: dict) -> dict:
        """Convert a JSON Schema dict to Gemini proto-compatible dict."""
        type_map = {
            "string": genai.protos.Type.STRING,
            "number": genai.protos.Type.NUMBER,
            "integer": genai.protos.Type.INTEGER,
            "boolean": genai.protos.Type.BOOLEAN,
            "array": genai.protos.Type.ARRAY,
            "object": genai.protos.Type.OBJECT,
        }
        result: dict[str, Any] = {}
        if "type" in schema:
            result["type"] = type_map.get(schema["type"], genai.protos.Type.STRING)
        if "description" in schema:
            result["description"] = schema["description"]
        if "properties" in schema:
            result["properties"] = {
                k: genai.protos.Schema(**self._schema_to_proto(v))
                for k, v in schema["properties"].items()
            }
        if "required" in schema:
            result["required"] = schema["required"]
        if "items" in schema:
            result["items"] = genai.protos.Schema(**self._schema_to_proto(schema["items"]))
        return result

    async def chat(
        self,
        session_id: str | None,
        user_message: str,
        user_id: str | None = None,
        user_role: str | None = None,
        context: dict | None = None,
    ) -> dict:
        """Process one user message and return the agent's response.

        Returns:
            {
                "response": str,         # the text reply
                "session_id": str,        # for continuity
                "action": dict | None,    # structured action if any
                "signals": list[dict],    # special signals detected
            }
        """
        # 1. Session management
        if not session_id:
            session_id = str(uuid.uuid4())

        existing = _load_session(session_id)
        if existing:
            history = existing.get("messages") or []
            if isinstance(history, str):
                history = json.loads(history)
        else:
            history = []

        # 2. Add user message
        history.append({"role": "user", "content": user_message})

        # 3. Build Gemini model + chat
        gemini_tools = self._build_gemini_tools()
        model = genai.GenerativeModel(
            model_name=self.model_name,
            system_instruction=self.system_prompt,
            tools=gemini_tools,
        )

        # Convert history to Gemini format
        gemini_history = []
        for msg in history[:-1]:  # all except the latest user message
            role = msg["role"]
            if role == "assistant":
                role = "model"
            if role in ("user", "model"):
                gemini_history.append({
                    "role": role,
                    "parts": [msg["content"]],
                })

        try:
            chat = model.start_chat(history=gemini_history)
            response = chat.send_message(user_message)
        except Exception as e:
            traceback.print_exc()
            error_msg = f"I'm having trouble connecting right now. Please try again in a moment. ({type(e).__name__})"
            history.append({"role": "assistant", "content": error_msg})
            _save_session(session_id, self.agent_type, history, user_id, user_role)
            return {
                "response": error_msg,
                "session_id": session_id,
                "action": None,
                "signals": [],
            }

        # 4. Tool calling loop
        rounds = 0
        while rounds < MAX_TOOL_ROUNDS:
            # Check if the response contains a function call
            candidate = response.candidates[0] if response.candidates else None
            if not candidate:
                break

            # Check for function calls in any part
            function_calls = []
            for part in candidate.content.parts:
                if hasattr(part, "function_call") and part.function_call.name:
                    function_calls.append(part.function_call)

            if not function_calls:
                break  # No tool calls — we have a text response

            # Execute each tool call
            tool_responses = []
            for fc in function_calls:
                tool_name = fc.name
                tool_args = dict(fc.args) if fc.args else {}
                print(f"[AGENT:{self.agent_type}] Tool call: {tool_name}({tool_args})")

                if tool_name in self._tool_map:
                    result_str = self._tool_map[tool_name].execute(**tool_args)
                else:
                    result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})

                print(f"[AGENT:{self.agent_type}] Tool result: {result_str[:200]}...")
                tool_responses.append(
                    genai.protos.Part(
                        function_response=genai.protos.FunctionResponse(
                            name=tool_name,
                            response={"result": result_str},
                        )
                    )
                )

                # Record tool call + result in our history
                history.append({
                    "role": "assistant",
                    "content": f"[Tool call: {tool_name}({json.dumps(tool_args, default=str)})]",
                    "tool_call": {"name": tool_name, "args": tool_args},
                })
                history.append({
                    "role": "tool",
                    "content": result_str,
                    "tool_name": tool_name,
                })

            # Send tool results back to Gemini
            try:
                response = chat.send_message(tool_responses)
            except Exception as e:
                traceback.print_exc()
                break

            rounds += 1

        # 5. Extract final text response
        try:
            response_text = response.text
        except Exception:
            # Sometimes response.text fails if the response is all function calls
            response_text = ""
            for part in (response.candidates[0].content.parts if response.candidates else []):
                if hasattr(part, "text") and part.text:
                    response_text += part.text

        if not response_text:
            response_text = "I'm here to help. Could you tell me more about what you need?"

        # 6. Detect special signals
        signals = _detect_signals(response_text)
        action = signals[0] if signals else None

        # 6b. Extract suggested replies (agent subclasses can override)
        suggestions = self.extract_suggestions(response_text, history)

        # 7. Save to history
        history.append({"role": "assistant", "content": response_text})

        # Determine outcome
        outcome = "browsing"
        if any(s["type"] == "submit_inquiry" for s in signals):
            outcome = "inquired"
        elif any(s["type"] == "notify_human" for s in signals):
            outcome = "handed_off"

        _save_session(
            session_id, self.agent_type, history,
            user_id, user_role, outcome,
            metadata={"context": context} if context else None,
        )

        return {
            "response": response_text,
            "session_id": session_id,
            "action": action,
            "signals": signals,
            "suggestions": suggestions,
        }

    def extract_suggestions(self, response_text: str, history: list[dict]) -> list[str] | None:
        """Extract suggested reply pills from the agent's response.

        Override in subclasses for agent-specific logic. Default returns None.
        """
        return None
