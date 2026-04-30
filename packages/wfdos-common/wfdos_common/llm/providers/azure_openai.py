"""Azure OpenAI provider — default per CLAUDE.md `llm-provider.mdc`.

Tier-to-deployment mapping:
  default    -> chat-gpt41mini (Haiku-class, fast + cheap)
  synthesis  -> chat-gpt41      (Sonnet-class, reasoning)

Reads credentials + deployment names from
`wfdos_common.config.settings.azure_openai` and `settings.llm`.
"""

from __future__ import annotations

from typing import Optional

from wfdos_common.llm.base import CompletionProvider, Message, ProviderError, Tier


class AzureOpenAIProvider(CompletionProvider):
    name = "azure_openai"

    def is_configured(self) -> bool:
        from wfdos_common.config import settings

        return bool(settings.azure_openai.endpoint and settings.azure_openai.key)

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
            # Late import so environments without the SDK can still use
            # other providers.
            from openai import AzureOpenAI
        except ImportError as e:
            raise ProviderError(
                "openai SDK not installed. "
                "pip install 'openai>=1.30' or switch LLM_PROVIDER."
            ) from e

        from wfdos_common.config import settings

        if not settings.azure_openai.endpoint or not settings.azure_openai.key:
            raise ProviderError(
                "Azure OpenAI not configured: set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_KEY."
            )

        model = (
            settings.llm.default_tier_model
            if tier == "default"
            else settings.llm.synthesis_tier_model
        )

        # Build the OpenAI-style messages list (system first, then history)
        payload: list[dict[str, str]] = []
        if system:
            payload.append({"role": "system", "content": system})
        payload.extend(messages)

        client = AzureOpenAI(
            api_key=settings.azure_openai.key,
            azure_endpoint=settings.azure_openai.endpoint,
            api_version="2024-10-21",
        )

        try:
            response = client.chat.completions.create(
                model=model,  # deployment name for Azure
                messages=payload,
                max_tokens=max_tokens,
                temperature=temperature,
            )
        except Exception as e:
            raise ProviderError(f"Azure OpenAI call failed: {type(e).__name__}: {e}") from e

        return response.choices[0].message.content or ""
