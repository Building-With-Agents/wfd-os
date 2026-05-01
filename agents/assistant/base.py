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
import traceback
import uuid
from typing import Any, Callable

import google.generativeai as genai
import psycopg2
import psycopg2.extras

# wfdos_common.config auto-loads the repo .env via python-dotenv find_dotenv.
# Importing settings here ensures env is loaded before we reach for Gemini creds.
# Pre-#27 this file had sys.path.insert hacks; the monorepo root pyproject.toml
# (#27) now exposes `agents.*` as a namespace package.
from wfdos_common.config import PG_CONFIG, settings
from wfdos_common.logging import get_logger

log = get_logger(__name__)

# Configure Gemini once at module level (replaced by wfdos_common.llm in #20).
genai.configure(api_key=settings.llm.gemini_api_key)

DEFAULT_MODEL = settings.llm.gemini_model
MAX_TOOL_ROUNDS = 5  # safety limit on consecutive tool calls


# ---------------------------------------------------------------------------
# Drill-scope enforcement — used by the Finance Cockpit drill chat surface.
# See agents/finance/design/chat_spec.md §"Scope enforcement".
# ---------------------------------------------------------------------------

_DRILL_SCOPE_INSTRUCTION_TEMPLATE = """

--- DRILL SCOPE ENFORCEMENT ---

You are currently answering questions about the '{drill_title}' drill in the
Finance Cockpit. The user's message is preceded by a [Context: {drill_title}]
block containing the full drill payload as JSON. Answer only questions that
can be answered from that payload.

If the user asks about something outside this drill (other providers, other
categories, general compliance questions, anything not in the payload),
set out_of_scope=true in your response and say exactly:
"That's outside this drill's scope. Try the broader chat panel for cross-cutting questions."
Do not guess or draw on general knowledge beyond the drill's data.

When you cite a fact, include the section id(s) in `sources` (the `id` field
from the payload's sections array). If your answer spans multiple sections,
list all relevant ids. If no specific section supports your answer, return an
empty array.

You MUST respond as JSON with this exact shape — no prose outside the JSON:
{{"response": "<your plain-English answer>", "out_of_scope": <true|false>, "sources": ["<section_id>", ...]}}
"""


_DRILL_RESPONSE_SCHEMA = {
    "type": "object",
    "properties": {
        "response": {"type": "string"},
        "out_of_scope": {"type": "boolean"},
        "sources": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["response", "out_of_scope"],
}


def _build_drill_context_block(drill_title: str | None, drill_payload: Any) -> str:
    """Render a drill-payload block to prepend to the user message."""
    title = drill_title or "drill"
    return (
        f"[Context: {title}]\n"
        f"{json.dumps(drill_payload, indent=2, default=str)}\n\n"
    )


def _build_session_metadata(ctx: dict | None) -> dict | None:
    """Build the `metadata` JSONB to store on agent_conversations.

    Promotes well-known chat-surface keys (scope, drill_key, drill_title,
    user) to top-level fields so the row is filterable in SQL. The raw
    drill_payload is intentionally NOT persisted — it's large, it's
    reconstructible from the cockpit API, and it would bloat the row on
    every turn.
    """
    if not ctx:
        return None
    meta: dict[str, Any] = {}
    for key in ("scope", "drill_key", "drill_title", "user"):
        val = ctx.get(key)
        if val is not None:
            meta[key] = val
    return meta or None


def _parse_drill_response(raw_text: str) -> tuple[str, bool, list[str]]:
    """Parse a drill-chat JSON response. Fall back to raw text if malformed."""
    try:
        parsed = json.loads(raw_text)
    except (json.JSONDecodeError, TypeError):
        return raw_text, False, []
    if not isinstance(parsed, dict):
        return raw_text, False, []
    response = parsed.get("response")
    if not isinstance(response, str):
        response = raw_text
    out_of_scope = bool(parsed.get("out_of_scope", False))
    sources_raw = parsed.get("sources") or []
    sources = [s for s in sources_raw if isinstance(s, str)] if isinstance(sources_raw, list) else []
    return response, out_of_scope, sources


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
    """Create unique index if missing (idempotent).

    A failure here means agent_conversations upserts will go through
    the slower fallback path — the agent still works, but session-id
    collisions become possible. Log so the error is visible without
    breaking module import.
    """
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
        log.warning(
            "agents.assistant.base.ensure_unique_index_failed",
            exc_info=True,
        )

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

        The optional `context` dict enables drill-scoped chat for the Finance
        Cockpit (see agents/finance/design/chat_spec.md). Recognized keys:
          - scope: "drill" activates drill-scope enforcement (structured JSON
            response, tools disabled, scope-guard appended to system prompt).
          - drill_title: displayed in the context block.
          - drill_payload: rendered as a [Context: ...] block prepended to
            the user message.
          - drill_key, user: forwarded to session metadata for filterability.

        Returns:
            {
                "response": str,         # the text reply
                "session_id": str,        # for continuity
                "action": dict | None,    # structured action if any
                "signals": list[dict],    # special signals detected
                "suggestions": list[str] | None,
                "out_of_scope": bool,     # drill chat only; false otherwise
                "sources": list[str],     # drill chat only; [] otherwise
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

        # 2. Drill-scope handling — decide up front whether this turn runs
        #    under scope enforcement. Tools are disabled under drill scope
        #    because Gemini can't combine tool-calling with structured
        #    output in the same response.
        ctx = context or {}
        is_drill = ctx.get("scope") == "drill"
        drill_title = ctx.get("drill_title")
        drill_payload = ctx.get("drill_payload")

        # What the model actually sees for this turn. Drill payload is
        # prepended; the user's raw text follows.
        if drill_payload is not None:
            model_user_message = (
                _build_drill_context_block(drill_title, drill_payload) + user_message
            )
        else:
            model_user_message = user_message

        # What we store in history is the raw user text, not the injected
        # context. The payload can be reconstructed from the source; we keep
        # history human-readable.
        history.append({"role": "user", "content": user_message})

        # 3. Build Gemini model + chat
        effective_system_prompt = self.system_prompt
        if is_drill:
            effective_system_prompt = (
                self.system_prompt
                + _DRILL_SCOPE_INSTRUCTION_TEMPLATE.format(
                    drill_title=drill_title or "this drill"
                )
            )

        if is_drill:
            gemini_tools = None  # tools incompatible with structured output
            generation_config = {
                "response_mime_type": "application/json",
                "response_schema": _DRILL_RESPONSE_SCHEMA,
            }
        else:
            gemini_tools = self._build_gemini_tools()
            generation_config = None

        model_kwargs: dict[str, Any] = {
            "model_name": self.model_name,
            "system_instruction": effective_system_prompt,
            "tools": gemini_tools,
        }
        if generation_config is not None:
            model_kwargs["generation_config"] = generation_config
        model = genai.GenerativeModel(**model_kwargs)

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
            response = chat.send_message(model_user_message)
        except Exception as e:
            traceback.print_exc()
            error_msg = f"I'm having trouble connecting right now. Please try again in a moment. ({type(e).__name__})"
            history.append({"role": "assistant", "content": error_msg})
            _save_session(
                session_id, self.agent_type, history, user_id, user_role,
                metadata=_build_session_metadata(ctx),
            )
            return {
                "response": error_msg,
                "session_id": session_id,
                "action": None,
                "signals": [],
                "suggestions": None,
                "out_of_scope": False,
                "sources": [],
            }

        # 4. Tool calling loop — skipped under drill scope (tools are off)
        rounds = 0
        while rounds < MAX_TOOL_ROUNDS and not is_drill:
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
                log.info(
                    "agents.assistant.tool_call",
                    agent_type=self.agent_type,
                    tool_name=tool_name,
                    tool_args=tool_args,
                )

                if tool_name in self._tool_map:
                    result_str = self._tool_map[tool_name].execute(**tool_args)
                else:
                    result_str = json.dumps({"error": f"Unknown tool: {tool_name}"})

                log.info(
                    "agents.assistant.tool_result",
                    agent_type=self.agent_type,
                    tool_name=tool_name,
                    result_preview=result_str[:200],
                )
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

        # 5b. Under drill scope, parse the structured JSON envelope and
        #     extract response/out_of_scope/sources. Broad chat leaves these
        #     at their defaults.
        out_of_scope = False
        sources: list[str] = []
        if is_drill:
            response_text, out_of_scope, sources = _parse_drill_response(response_text)

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
            metadata=_build_session_metadata(ctx),
        )

        return {
            "response": response_text,
            "session_id": session_id,
            "action": action,
            "signals": signals,
            "suggestions": suggestions,
            "out_of_scope": out_of_scope,
            "sources": sources,
        }

    def extract_suggestions(self, response_text: str, history: list[dict]) -> list[str] | None:
        """Extract suggested reply pills from the agent's response.

        Override in subclasses for agent-specific logic. Default returns None.
        """
        return None
