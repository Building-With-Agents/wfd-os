"""Agent ABC — unified contract for every conversational + background agent.

Every agent across wfd-os and the JIE repo ends up doing the same four things:

  1. **Receive an invocation** — user message, webhook event, cron tick.
  2. **Orchestrate LLM + tool calls** via `wfdos_common.llm.complete`
     and a `ToolRegistry`.
  3. **Persist session state** — conversation history, intermediate tool
     outputs, the last action signal.
  4. **Emit a structured result** — payload + action classification
     (`INTAKE_COMPLETE`, `HANDOFF_TO_HUMAN`, `continue`, etc.).

The `Agent` ABC formalizes that contract. Subclasses override
`system_prompt`, `tools`, and the two hooks (`on_intent` + `on_result`)
to specialize; the rest is shared.

The 6 conversational agents (student / employer / college / consulting /
staff / youth) in `agents/assistant/` are scheduled to migrate onto this
ABC — that's the big #26 follow-up, tracked in the PR description. This
module is the foundation that migration stands on.
"""

from __future__ import annotations

import abc
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Optional, Sequence

from wfdos_common.logging import get_logger

log = get_logger(__name__)


# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


@dataclass
class Tool:
    """One tool the model can invoke. Declaration + Python callable."""

    name: str
    description: str
    parameters: dict[str, Any]  # JSON-Schema (draft 7) for the tool input
    handler: Callable[..., Any]

    def invoke(self, **kwargs: Any) -> Any:
        return self.handler(**kwargs)


class ToolRegistry:
    """Register-once-use-anywhere tool store.

    Typical usage: service startup calls `.register(...)` for every tool
    the agents expose; agent instances hold a reference to the registry
    and call `.get(name)` when the LLM asks for a tool by name.
    """

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> Tool:
        if tool.name in self._tools:
            raise ValueError(f"tool '{tool.name}' already registered")
        self._tools[tool.name] = tool
        return tool

    def register_callable(
        self,
        *,
        name: str,
        description: str,
        parameters: dict[str, Any],
    ) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
        """Decorator form: `@registry.register_callable(name=..., ...)`."""

        def decorator(fn: Callable[..., Any]) -> Callable[..., Any]:
            self.register(
                Tool(
                    name=name,
                    description=description,
                    parameters=parameters,
                    handler=fn,
                )
            )
            return fn

        return decorator

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError as e:
            raise KeyError(f"tool '{name}' is not registered") from e

    def has(self, name: str) -> bool:
        return name in self._tools

    def list(self) -> list[Tool]:
        return list(self._tools.values())

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------


@dataclass
class AgentResult:
    """Standard envelope for an Agent.process() call.

    `action` lets orchestrators react to special signals without parsing
    the natural-language response. Known values:
      - `"continue"` — no special signal; normal conversational reply
      - `"intake_complete"` — consulting-intake kind
      - `"handoff_to_human"` — agent is out of depth
      - `"tool_call_exceeded"` — safety limit hit; aborted
    """

    response: str
    session_id: str
    action: str = "continue"
    metadata: dict[str, Any] = field(default_factory=dict)
    tool_invocations: list[dict[str, Any]] = field(default_factory=list)


# ---------------------------------------------------------------------------
# The ABC
# ---------------------------------------------------------------------------


class Agent(abc.ABC):
    """Base class every concrete agent inherits.

    Subclasses must set:
      - `agent_id`: stable identifier, e.g. "consulting-intake".
      - `system_prompt`: the system message fed to the LLM.
      - `tools`: iterable of `Tool` instances available this agent.

    Subclasses can override:
      - `model_tier`: "default" (cheap) or "synthesis" (reasoning). Default "default".
      - `max_tool_rounds`: safety limit on recursive tool calls. Default 5.
      - `on_result(AgentResult)`: post-invocation hook (log + persist).
      - `on_intent(message)`: pre-invocation hook (routing + guards).

    Subclasses should NOT override `process()` unless they really mean it.
    """

    agent_id: str
    system_prompt: str
    tools: Sequence[Tool] = ()
    model_tier: str = "default"
    max_tool_rounds: int = 5

    def __init__(
        self,
        *,
        agent_id: Optional[str] = None,
        system_prompt: Optional[str] = None,
        tools: Optional[Sequence[Tool]] = None,
        model_tier: Optional[str] = None,
        max_tool_rounds: Optional[int] = None,
        registry: Optional[ToolRegistry] = None,
    ) -> None:
        # Allow instance-level overrides of class-level defaults.
        if agent_id is not None:
            self.agent_id = agent_id
        if system_prompt is not None:
            self.system_prompt = system_prompt
        if tools is not None:
            self.tools = tuple(tools)
        if model_tier is not None:
            self.model_tier = model_tier
        if max_tool_rounds is not None:
            self.max_tool_rounds = max_tool_rounds
        self.registry = registry

    # ---- public surface --------------------------------------------------

    def health_check(self) -> dict[str, Any]:
        """Return a JSON-able dict describing this agent's readiness.

        Services combine `health_check()` from every agent into their own
        `/api/health` response. Default implementation returns
        structural info; subclasses override to add integration-liveness
        checks (`graph_reachable`, `db_ok`, etc.).
        """
        return {
            "agent_id": self.agent_id,
            "model_tier": self.model_tier,
            "tool_count": len(self.tools),
            "status": "ready",
        }

    def process(
        self,
        message: str,
        *,
        session_id: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> AgentResult:
        """Run one turn. The LLM call + tool-invocation loop is delegated
        to `_run_turn` (which subclasses may swap out); `process`
        orchestrates the session lifecycle around it."""
        sid = session_id or str(uuid.uuid4())
        meta = dict(metadata or {})

        # Hooks so subclasses can do routing, rate-limit checks, etc.
        # without touching the LLM orchestration.
        self.on_intent(message, meta=meta)

        start = datetime.now(timezone.utc)
        result = self._run_turn(message=message, session_id=sid, metadata=meta)
        result.metadata.setdefault("latency_ms", int(
            (datetime.now(timezone.utc) - start).total_seconds() * 1000
        ))

        self.on_result(result)
        log.info(
            "agent.process.complete",
            agent_id=self.agent_id,
            session_id=sid,
            action=result.action,
            latency_ms=result.metadata["latency_ms"],
        )
        return result

    # ---- hooks (overridable) --------------------------------------------

    def on_intent(self, message: str, *, meta: dict[str, Any]) -> None:
        """Pre-LLM hook. Default no-op."""

    def on_result(self, result: AgentResult) -> None:
        """Post-LLM hook. Default: structured log."""
        log.info(
            "agent.result",
            agent_id=self.agent_id,
            session_id=result.session_id,
            action=result.action,
            response_preview=result.response[:200],
        )

    # ---- subclass must implement ----------------------------------------

    @abc.abstractmethod
    def _run_turn(
        self,
        *,
        message: str,
        session_id: str,
        metadata: dict[str, Any],
    ) -> AgentResult:
        """Execute one LLM turn. Concrete subclasses call
        `wfdos_common.llm.complete(...)` + their ToolRegistry here.

        Abstract so unit tests can provide a minimal subclass without
        wiring the full LLM pipeline.
        """


# ---------------------------------------------------------------------------
# Reference implementation — simplest possible concrete subclass
# ---------------------------------------------------------------------------


class EchoAgent(Agent):
    """Reference subclass for tests + examples. Answers with a canned
    echo + whatever metadata was passed in. Never calls an LLM."""

    agent_id = "echo"
    system_prompt = "You are a test echo agent."

    def _run_turn(
        self,
        *,
        message: str,
        session_id: str,
        metadata: dict[str, Any],
    ) -> AgentResult:
        action = "continue"
        # Simple signal detection to exercise the machinery.
        lower = message.lower()
        if "intake complete" in lower:
            action = "intake_complete"
        elif "handoff" in lower:
            action = "handoff_to_human"
        return AgentResult(
            response=f"echo: {message}",
            session_id=session_id,
            action=action,
            metadata={"agent_id": self.agent_id, **metadata},
        )


__all__ = [
    "Agent",
    "AgentResult",
    "EchoAgent",
    "Tool",
    "ToolRegistry",
]
