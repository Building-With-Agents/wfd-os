"""Gemini (Google Generative AI) provider — second fallback.

Tier-to-model mapping:
  default    -> gemini-2.5-flash   (Haiku-class)
  synthesis  -> gemini-2.5-pro     (Sonnet-class)
"""

from __future__ import annotations

import os
from typing import Optional

from wfdos_common.llm.base import CompletionProvider, Message, ProviderError, Tier


class GeminiProvider(CompletionProvider):
    name = "gemini"

    def is_configured(self) -> bool:
        from wfdos_common.config import settings

        return bool(settings.llm.gemini_api_key or os.getenv("GEMINI_API_KEY"))

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
            import google.generativeai as genai
        except ImportError as e:
            raise ProviderError(
                "google-generativeai SDK not installed. pip install google-generativeai."
            ) from e

        from wfdos_common.config import settings

        api_key = settings.llm.gemini_api_key or os.getenv("GEMINI_API_KEY")
        if not api_key:
            raise ProviderError(
                "Gemini not configured: set GEMINI_API_KEY in .env."
            )

        # Tier-to-model; overrides allowed per the same pattern as Anthropic.
        model_name = (
            os.getenv("LLM_GEMINI_DEFAULT_MODEL", "gemini-2.5-flash")
            if tier == "default"
            else os.getenv("LLM_GEMINI_SYNTHESIS_MODEL", "gemini-2.5-pro")
        )

        genai.configure(api_key=api_key)

        # Gemini's chat API takes system_instruction at model construction and
        # messages as content list. Map our {role,content} shape to Gemini's
        # `role` field where user→user, assistant→model, system folded into
        # the model constructor.
        system_instruction = system or None

        # Flatten messages, mapping roles
        gemini_history = []
        for m in messages:
            role = m["role"]
            if role == "system":
                # If multiple system messages, concatenate into system_instruction
                system_instruction = (
                    (system_instruction + "\n\n" + m["content"])
                    if system_instruction
                    else m["content"]
                )
                continue
            gemini_role = "model" if role == "assistant" else "user"
            gemini_history.append(
                {"role": gemini_role, "parts": [{"text": m["content"]}]}
            )

        try:
            model = genai.GenerativeModel(
                model_name=model_name,
                system_instruction=system_instruction,
            )
            response = model.generate_content(
                gemini_history,
                generation_config={
                    "max_output_tokens": max_tokens,
                    "temperature": temperature,
                },
            )
        except Exception as e:
            raise ProviderError(f"Gemini call failed: {type(e).__name__}: {e}") from e

        return getattr(response, "text", "") or ""
