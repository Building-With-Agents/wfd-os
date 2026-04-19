"""Provider base class + shared types for the LLM adapter."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Literal, Optional

Message = dict[str, str]  # {"role": "user"|"assistant"|"system", "content": str}
Tier = Literal["default", "synthesis"]


class ProviderError(RuntimeError):
    """Raised when a provider can't fulfill a request — usually missing
    credentials, invalid API key, or provider-specific errors surfaced
    so callers can decide whether to fall back."""

    pass


class CompletionProvider(ABC):
    """Provider contract. Each implementation reads its own credentials
    from `wfdos_common.config.settings` and translates the generic
    messages + tier into provider-specific API calls.

    Providers are LAZY — constructing one just records config; the real
    SDK import + auth happens on first complete() call so test envs
    without the SDK installed don't fail at import time.
    """

    #: Human-readable provider name used in logs.
    name: str

    @abstractmethod
    def is_configured(self) -> bool:
        """True iff this provider has the credentials needed to make a
        call. Drives the graceful-degradation chain: providers where
        is_configured() returns False are skipped without a trip through
        the underlying SDK.
        """
        ...

    @abstractmethod
    def complete(
        self,
        messages: list[Message],
        *,
        tier: Tier = "default",
        system: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        """Translate (messages, tier) into a provider API call and return
        the assistant text. Raises ProviderError on credential / network /
        rate-limit issues so the adapter can fall through.
        """
        ...
