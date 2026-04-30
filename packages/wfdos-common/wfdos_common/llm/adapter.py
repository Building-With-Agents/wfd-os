"""Top-level adapter — provider selection + graceful-degradation chain."""

from __future__ import annotations

import logging
from threading import Lock
from typing import Optional

from wfdos_common.llm.base import CompletionProvider, Message, ProviderError, Tier

log = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Provider cache
# ---------------------------------------------------------------------------

_active_provider: Optional[CompletionProvider] = None
_selection_lock = Lock()


# Chain of candidates, ordered by preference AFTER the configured primary.
# The primary is inserted at the head; if it isn't configured or construction
# fails, we fall through to the rest.
_FALLBACK_ORDER = ["azure_openai", "anthropic", "gemini"]


def _build_provider(name: str) -> CompletionProvider:
    """Instantiate a provider by name. Imports its module lazily."""
    name = name.strip().lower()
    if name == "azure_openai":
        from wfdos_common.llm.providers import AzureOpenAIProvider
        return AzureOpenAIProvider()
    if name == "anthropic":
        from wfdos_common.llm.providers import AnthropicProvider
        return AnthropicProvider()
    if name == "gemini":
        from wfdos_common.llm.providers import GeminiProvider
        return GeminiProvider()
    raise ValueError(
        f"Unknown LLM provider: {name!r}. "
        "Valid: azure_openai, anthropic, gemini."
    )


def _select_provider() -> CompletionProvider:
    """Pick the first working provider from [configured, ...fallbacks].

    Called once per process + cached. Use reset_provider() in tests or
    after credential changes.
    """
    from wfdos_common.config import settings

    configured = (settings.llm.provider or "azure_openai").strip().lower()

    # Build the chain: configured primary first, then fallbacks excluding
    # the primary to avoid repeating.
    candidates = [configured] + [p for p in _FALLBACK_ORDER if p != configured]

    errors: list[tuple[str, str]] = []
    for name in candidates:
        try:
            provider = _build_provider(name)
        except ValueError as e:
            # Unknown provider name — report and skip rather than error out
            errors.append((name, str(e)))
            continue

        if provider.is_configured():
            if name != configured:
                log.warning(
                    "LLM configured provider %r unavailable; falling back to %r",
                    configured, name,
                )
            return provider
        errors.append((name, "not configured (credentials missing)"))

    detail = "; ".join(f"{n}: {e}" for n, e in errors)
    raise ProviderError(
        f"No LLM provider could be selected. Tried: {detail}. "
        "Set AZURE_OPENAI_KEY, ANTHROPIC_API_KEY, or GEMINI_API_KEY."
    )


def _get_provider() -> CompletionProvider:
    """Return cached provider; select on first call."""
    global _active_provider
    with _selection_lock:
        if _active_provider is None:
            _active_provider = _select_provider()
        return _active_provider


def reset_provider() -> None:
    """Force re-selection on next complete() call. Test hook; also useful
    after credential rotation.
    """
    global _active_provider
    with _selection_lock:
        _active_provider = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def complete(
    messages: list[Message],
    *,
    tier: Tier = "default",
    system: Optional[str] = None,
    max_tokens: int = 4096,
    temperature: float = 0.7,
) -> str:
    """Simple text completion — messages in, assistant text out.

    `tier` selects the model capability class:
      - "default"   — fast + cheap (Haiku-class: chat-gpt41mini / claude-haiku / gemini-flash)
      - "synthesis" — reasoning-heavy (Sonnet-class: chat-gpt41 / claude-sonnet / gemini-pro)

    Provider chosen by wfdos_common.config.settings.llm.provider
    (default: "azure_openai" per CLAUDE.md llm-provider.mdc), with
    graceful degradation to Anthropic → Gemini if the primary is
    unconfigured.

    Not for tool-calling / agentic flows — those call provider SDKs
    directly until #26 wires them to the Agent ABC.
    """
    provider = _get_provider()
    return provider.complete(
        messages,
        tier=tier,
        system=system,
        max_tokens=max_tokens,
        temperature=temperature,
    )
