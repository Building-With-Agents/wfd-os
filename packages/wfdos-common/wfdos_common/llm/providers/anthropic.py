"""Anthropic (Claude) provider — first fallback.

Tier-to-model mapping:
  default    -> claude-haiku-4-5
  synthesis  -> claude-sonnet-4-6

Model IDs read from `settings.llm.anthropic_default_model` and
`settings.llm.anthropic_synthesis_model` so they can be tuned without
code changes.
"""

from __future__ import annotations

import os
from typing import Optional

from wfdos_common.llm.base import CompletionProvider, Message, ProviderError, Tier


class AnthropicProvider(CompletionProvider):
    name = "anthropic"

    def is_configured(self) -> bool:
        from wfdos_common.config import settings

        return bool(settings.llm.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY"))

    def complete(
        self,
        messages: list[Message],
        *,
        tier: Tier = "default",
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        try:
            import anthropic
        except ImportError as e:
            raise ProviderError(
                "anthropic SDK not installed. pip install anthropic."
            ) from e

        from wfdos_common.config import settings

        api_key = settings.llm.anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ProviderError(
                "Anthropic not configured: set ANTHROPIC_API_KEY in .env."
            )

        # Tier-to-model — defaults match CLAUDE.md capability tiers.
        # Overridable via LLM_ANTHROPIC_DEFAULT_MODEL / _SYNTHESIS_MODEL.
        model = (
            os.getenv("LLM_ANTHROPIC_DEFAULT_MODEL", "claude-haiku-4-5")
            if tier == "default"
            else os.getenv("LLM_ANTHROPIC_SYNTHESIS_MODEL", "claude-sonnet-4-6")
        )

        client = anthropic.Anthropic(api_key=api_key)

        # Anthropic takes `system` as top-level string, not a role in messages.
        kwargs: dict = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": m["role"], "content": m["content"]} for m in messages],
        }
        if system:
            kwargs["system"] = system

        try:
            response = client.messages.create(**kwargs)
        except Exception as e:
            raise ProviderError(f"Anthropic call failed: {type(e).__name__}: {e}") from e

        # Single-turn text completion path — take first text block.
        for block in response.content:
            if getattr(block, "type", None) == "text":
                return block.text
        # Fallback: legacy shape (older SDKs)
        if hasattr(response.content, "__iter__"):
            for block in response.content:
                if hasattr(block, "text"):
                    return block.text
        return ""
