"""wfdos_common.agent — unified Agent ABC + tool registry (#26).

Every conversational + background agent across wfd-os and the JIE repo
inherits from `Agent`, which codifies the four common steps:

  1. Receive an invocation
  2. Orchestrate LLM + tool calls (via wfdos_common.llm)
  3. Persist session state
  4. Emit a structured `AgentResult`

Subclasses override `system_prompt`, `tools`, and the two hooks
(`on_intent` + `on_result`) to specialize. `process()` is stable.

The 6 conversational agents in `agents/assistant/` are scheduled to
migrate onto this ABC (deferred cleanup per the #26 PR description).
"""

from wfdos_common.agent.base import (
    Agent,
    AgentResult,
    EchoAgent,
    Tool,
    ToolRegistry,
)

__all__ = [
    "Agent",
    "AgentResult",
    "EchoAgent",
    "Tool",
    "ToolRegistry",
]
