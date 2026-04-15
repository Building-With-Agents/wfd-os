"""wfdos_common.llm — provider-agnostic LLM adapter.

STATUS: STUB — implementation lands in Building-With-Agents/wfd-os#20.

Target scope (from #20):
- complete(messages, tier) -> str  — single entry point
- Tier values: "default" (Haiku-class), "synthesis" (Sonnet-class)
- Default provider: Azure OpenAI (chat-gpt41mini / chat-gpt41) per CLAUDE.md
  llm-provider.mdc.
- Fallback providers: Anthropic, Gemini (via LLM_PROVIDER env override).
- Graceful-degradation: if configured provider creds fail, fall through to
  next working provider and log a warning.

Replaces direct SDK imports (google.generativeai, anthropic) in assistants,
scoping, market-intelligence, and profile parsing.
"""
