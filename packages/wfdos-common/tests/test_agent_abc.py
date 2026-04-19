"""Tests for wfdos_common.agent — the Agent ABC + ToolRegistry (#26)."""

from __future__ import annotations

import pytest

from wfdos_common.agent import (
    Agent,
    AgentResult,
    EchoAgent,
    Tool,
    ToolRegistry,
)


# ---------------------------------------------------------------------------
# ToolRegistry
# ---------------------------------------------------------------------------


def _tool(name: str, handler=lambda **_: "ok") -> Tool:
    return Tool(
        name=name,
        description=f"test tool {name}",
        parameters={"type": "object", "properties": {}, "required": []},
        handler=handler,
    )


def test_registry_register_and_get():
    reg = ToolRegistry()
    reg.register(_tool("search"))
    got = reg.get("search")
    assert got.name == "search"


def test_registry_duplicate_registration_raises():
    reg = ToolRegistry()
    reg.register(_tool("search"))
    with pytest.raises(ValueError, match="already registered"):
        reg.register(_tool("search"))


def test_registry_unknown_tool_raises_keyerror():
    reg = ToolRegistry()
    with pytest.raises(KeyError, match="not registered"):
        reg.get("missing")


def test_registry_has_and_contains():
    reg = ToolRegistry()
    reg.register(_tool("x"))
    assert reg.has("x")
    assert "x" in reg
    assert not reg.has("y")
    assert "y" not in reg


def test_registry_list_returns_registered_tools():
    reg = ToolRegistry()
    reg.register(_tool("a"))
    reg.register(_tool("b"))
    names = {t.name for t in reg.list()}
    assert names == {"a", "b"}
    assert len(reg) == 2


def test_registry_register_callable_decorator():
    reg = ToolRegistry()

    @reg.register_callable(
        name="add",
        description="sum two numbers",
        parameters={
            "type": "object",
            "properties": {"a": {"type": "number"}, "b": {"type": "number"}},
            "required": ["a", "b"],
        },
    )
    def _add(a, b):
        return a + b

    tool = reg.get("add")
    assert tool.invoke(a=2, b=3) == 5


def test_tool_invoke_calls_handler():
    called = []
    tool = _tool("t", handler=lambda **kw: called.append(kw) or "done")
    assert tool.invoke(x=1) == "done"
    assert called == [{"x": 1}]


# ---------------------------------------------------------------------------
# Agent ABC — EchoAgent reference subclass
# ---------------------------------------------------------------------------


def test_echo_agent_process_returns_result():
    agent = EchoAgent()
    out = agent.process("hello")
    assert isinstance(out, AgentResult)
    assert out.response == "echo: hello"
    assert out.action == "continue"
    assert out.session_id  # auto-generated


def test_echo_agent_respects_provided_session_id():
    agent = EchoAgent()
    out = agent.process("hello", session_id="sess-42")
    assert out.session_id == "sess-42"


def test_echo_agent_detects_intake_complete_signal():
    agent = EchoAgent()
    out = agent.process("intake complete, thanks")
    assert out.action == "intake_complete"


def test_echo_agent_detects_handoff_signal():
    agent = EchoAgent()
    out = agent.process("handoff to a human please")
    assert out.action == "handoff_to_human"


def test_agent_result_carries_latency_ms():
    agent = EchoAgent()
    out = agent.process("hello")
    assert "latency_ms" in out.metadata
    assert out.metadata["latency_ms"] >= 0


def test_agent_metadata_passthrough():
    agent = EchoAgent()
    out = agent.process("hi", metadata={"tenant_id": "waifinder-flagship"})
    assert out.metadata["tenant_id"] == "waifinder-flagship"


def test_agent_health_check_default_shape():
    agent = EchoAgent()
    h = agent.health_check()
    assert h["agent_id"] == "echo"
    assert h["status"] == "ready"
    assert "tool_count" in h


# ---------------------------------------------------------------------------
# Hook overrides
# ---------------------------------------------------------------------------


class _CountingAgent(EchoAgent):
    """Exercises the on_intent / on_result hooks."""

    def __init__(self) -> None:
        super().__init__()
        self.intents: list[str] = []
        self.results: list[AgentResult] = []

    def on_intent(self, message: str, *, meta):
        self.intents.append(message)

    def on_result(self, result: AgentResult) -> None:
        self.results.append(result)


def test_on_intent_and_on_result_hooks_fire():
    agent = _CountingAgent()
    out = agent.process("ping")
    assert agent.intents == ["ping"]
    assert agent.results == [out]


# ---------------------------------------------------------------------------
# Subclass instantiation semantics
# ---------------------------------------------------------------------------


def test_agent_cannot_instantiate_abstract_class():
    with pytest.raises(TypeError):
        Agent(agent_id="x", system_prompt="y")  # type: ignore[abstract]


def test_instance_overrides_class_defaults():
    agent = EchoAgent(model_tier="synthesis", max_tool_rounds=2)
    assert agent.model_tier == "synthesis"
    assert agent.max_tool_rounds == 2
