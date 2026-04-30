"""wfdos_common.llm — provider-agnostic LLM adapter (#20).

Public API:

    from wfdos_common.llm import complete

    text = complete(
        messages=[{"role": "user", "content": "hello"}],
        tier="default",             # or "synthesis"
        system="You are helpful.",
        max_tokens=1024,
        temperature=0.7,
    )

Selects a provider via `settings.llm.provider` (default `"azure_openai"`
per CLAUDE.md llm-provider.mdc). Gracefully degrades on missing or
invalid credentials: the active provider is re-selected from the
fallback chain if the configured primary can't be constructed.

Fallback chain (first working wins):
  configured provider → anthropic → gemini

Tool-calling / agentic flows (e.g. market-intelligence/agent.py,
assistant/base.py) stay on their direct SDK calls for now — they land
in #26 when the Agent ABC gets wired to this adapter. #20's scope is
the simple messages → text completion path used by scoping research,
transcript analysis, grant-bot Q&A, and resume-parse extraction.
"""

from wfdos_common.llm.adapter import ProviderError, complete, reset_provider
from wfdos_common.llm.base import CompletionProvider

__all__ = [
    "complete",
    "CompletionProvider",
    "ProviderError",
    "reset_provider",
]
