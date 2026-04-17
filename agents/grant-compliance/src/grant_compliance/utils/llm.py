"""Anthropic SDK wrapper. All LLM calls in the system go through here.

Reasons to centralize:
  - Audit log integration (every call recorded with model, prompt hash, output)
  - Mock provider for offline development and tests
  - Single place to enforce timeouts, retries, rate limits
  - Single place to switch models or providers
"""

from __future__ import annotations

from dataclasses import dataclass

from grant_compliance.config import get_settings


@dataclass
class LLMResponse:
    text: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0


class LLMClient:
    def __init__(self) -> None:
        self.settings = get_settings()
        self._anthropic = None  # lazy

    def complete(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int = 1024,
        temperature: float = 0.0,
    ) -> LLMResponse:
        """Run a single-turn completion."""
        if self.settings.llm_provider == "mock":
            return self._mock_complete(system=system, user=user)
        return self._anthropic_complete(
            system=system, user=user, max_tokens=max_tokens, temperature=temperature
        )

    # -------------------------------------------------------------------
    # Anthropic
    # -------------------------------------------------------------------

    def _anthropic_complete(
        self, *, system: str, user: str, max_tokens: int, temperature: float
    ) -> LLMResponse:
        if not self.settings.anthropic_api_key:
            raise RuntimeError(
                "ANTHROPIC_API_KEY not set but LLM_PROVIDER=anthropic. "
                "Set the key or switch LLM_PROVIDER=mock."
            )
        if self._anthropic is None:
            from anthropic import Anthropic

            self._anthropic = Anthropic(api_key=self.settings.anthropic_api_key)

        msg = self._anthropic.messages.create(
            model=self.settings.anthropic_model,
            max_tokens=max_tokens,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        # Concatenate any text blocks
        text_parts = [
            block.text for block in msg.content if getattr(block, "type", "") == "text"
        ]
        return LLMResponse(
            text="".join(text_parts),
            model=msg.model,
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
        )

    # -------------------------------------------------------------------
    # Mock
    # -------------------------------------------------------------------

    def _mock_complete(self, *, system: str, user: str) -> LLMResponse:
        """Predictable canned responses for offline dev. Pattern-match on the
        user prompt to return something useful for the calling agent.
        """
        if "classify this transaction" in user.lower():
            text = (
                '{"grant_id": null, "confidence": 0.0, '
                '"rationale": "Mock LLM provider — set LLM_PROVIDER=anthropic for real classification."}'
            )
        elif "draft a time and effort" in user.lower():
            text = (
                '{"splits": {}, "rationale": "Mock LLM — populate manually or enable real provider."}'
            )
        elif "explain this compliance flag" in user.lower():
            text = "Mock explanation. Enable real LLM provider for plain-language explanations."
        else:
            text = "[mock LLM response]"
        return LLMResponse(text=text, model="mock-llm")


_client: LLMClient | None = None


def get_llm() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
