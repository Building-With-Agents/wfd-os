"""wfdos_common.agent — unified Agent ABC + tool registry.

STATUS: STUB — implementation lands in Building-With-Agents/wfd-os#26.

Target scope (from #26):
- wfdos_common.agent.Agent — ABC with process(), health_check(), agent_id
  (matches JIE agent pattern for cross-repo consistency).
- wfdos_common.agent.tools.ToolRegistry — register-once-use-anywhere tool
  declarations (generalized from the Tool pattern in
  agents/assistant/base.py).
- All LLM calls go through wfdos_common.llm (#20) — no direct SDK imports
  in agent code.
"""
