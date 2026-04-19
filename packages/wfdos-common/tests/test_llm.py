"""Tests for wfdos_common.llm (#20).

Mocked SDKs — no real API calls. Providers lazy-import their SDKs;
tests patch those imports via sys.modules so every branch is reachable
without network access.
"""

from __future__ import annotations

import sys
import types
from unittest.mock import MagicMock

import pytest

from wfdos_common.llm import ProviderError, complete, reset_provider
from wfdos_common.llm.adapter import _build_provider, _select_provider
from wfdos_common.llm.providers import (
    AnthropicProvider,
    AzureOpenAIProvider,
    GeminiProvider,
)


@pytest.fixture(autouse=True)
def _reset_between_tests():
    reset_provider()
    yield
    reset_provider()


@pytest.fixture
def _clear_llm_sdk_modules(monkeypatch):
    """Some tests check 'SDK not installed' behavior. Ensure the real SDKs
    are absent from sys.modules so the late-import inside the provider
    raises ImportError.
    """
    for modname in list(sys.modules):
        if modname.startswith(("openai", "anthropic", "google.generativeai", "google.ai")):
            monkeypatch.delitem(sys.modules, modname, raising=False)


# ---------------------------------------------------------------------------
# _build_provider
# ---------------------------------------------------------------------------

def test_build_provider_azure_openai():
    p = _build_provider("azure_openai")
    assert isinstance(p, AzureOpenAIProvider)
    assert p.name == "azure_openai"


def test_build_provider_anthropic():
    p = _build_provider("anthropic")
    assert isinstance(p, AnthropicProvider)


def test_build_provider_gemini():
    p = _build_provider("gemini")
    assert isinstance(p, GeminiProvider)


def test_build_provider_rejects_unknown():
    with pytest.raises(ValueError) as e:
        _build_provider("cohere")
    assert "cohere" in str(e.value).lower()


def test_build_provider_case_insensitive():
    p = _build_provider("AZURE_OPENAI")
    assert p.name == "azure_openai"


# ---------------------------------------------------------------------------
# is_configured() — drives the fallback chain
# ---------------------------------------------------------------------------

def test_azure_openai_configured_when_endpoint_and_key_set(monkeypatch):
    from wfdos_common.config import reset_settings
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "fake-key")
    reset_settings()
    assert AzureOpenAIProvider().is_configured() is True


def test_azure_openai_not_configured_when_key_missing(monkeypatch):
    from wfdos_common.config import reset_settings
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "")
    reset_settings()
    assert AzureOpenAIProvider().is_configured() is False


def test_anthropic_configured_via_settings(monkeypatch):
    from wfdos_common.config import reset_settings
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    reset_settings()
    assert AnthropicProvider().is_configured() is True


def test_gemini_configured_via_env(monkeypatch):
    from wfdos_common.config import reset_settings
    monkeypatch.setenv("GEMINI_API_KEY", "gm-test")
    reset_settings()
    assert GeminiProvider().is_configured() is True


# ---------------------------------------------------------------------------
# _select_provider — fallback chain
# ---------------------------------------------------------------------------

def test_selection_picks_configured_primary(monkeypatch):
    from wfdos_common.config import reset_settings
    monkeypatch.setenv("LLM_PROVIDER", "azure_openai")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "fake")
    reset_settings()
    p = _select_provider()
    assert p.name == "azure_openai"


def test_selection_falls_through_to_anthropic_when_azure_unconfigured(monkeypatch):
    from wfdos_common.config import reset_settings
    monkeypatch.setenv("LLM_PROVIDER", "azure_openai")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    reset_settings()
    p = _select_provider()
    assert p.name == "anthropic"


def test_selection_falls_through_to_gemini(monkeypatch):
    from wfdos_common.config import reset_settings
    monkeypatch.setenv("LLM_PROVIDER", "azure_openai")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("GEMINI_API_KEY", "gm-key")
    reset_settings()
    p = _select_provider()
    assert p.name == "gemini"


def test_selection_raises_when_nothing_configured(monkeypatch):
    from wfdos_common.config import reset_settings
    for v in ["AZURE_OPENAI_ENDPOINT", "AZURE_OPENAI_KEY",
              "ANTHROPIC_API_KEY", "GEMINI_API_KEY"]:
        monkeypatch.setenv(v, "")
    reset_settings()
    with pytest.raises(ProviderError) as e:
        _select_provider()
    assert "No LLM provider" in str(e.value)


def test_selection_honors_explicit_anthropic_primary(monkeypatch):
    """If LLM_PROVIDER=anthropic + ANTHROPIC_API_KEY set, we don't fall
    back to Azure even if Azure is also configured."""
    from wfdos_common.config import reset_settings
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "fake")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant")
    reset_settings()
    p = _select_provider()
    assert p.name == "anthropic"


# ---------------------------------------------------------------------------
# complete() — end-to-end with mocked provider
# ---------------------------------------------------------------------------

class _StubProvider:
    """Captures last call args + returns a fixed string."""
    name = "stub"

    def __init__(self, reply="hello from stub"):
        self.reply = reply
        self.last_call = None

    def is_configured(self):
        return True

    def complete(self, messages, *, tier="default", system=None, max_tokens=4096, temperature=0.7):
        self.last_call = {
            "messages": messages,
            "tier": tier,
            "system": system,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        return self.reply


def test_complete_round_trips_through_provider(monkeypatch):
    stub = _StubProvider(reply="OK")
    from wfdos_common.llm import adapter
    monkeypatch.setattr(adapter, "_active_provider", stub)

    out = complete([{"role": "user", "content": "ping"}], tier="synthesis", system="Be terse.")
    assert out == "OK"
    assert stub.last_call == {
        "messages": [{"role": "user", "content": "ping"}],
        "tier": "synthesis",
        "system": "Be terse.",
        "max_tokens": 4096,
        "temperature": 0.7,
    }


# ---------------------------------------------------------------------------
# Tier-to-model mapping
# ---------------------------------------------------------------------------

def test_azure_openai_uses_default_tier_model(monkeypatch):
    """Verify the provider picks the right deployment per tier. We stub
    the AzureOpenAI client so no real call happens.
    """
    from wfdos_common.config import reset_settings

    monkeypatch.setenv("AZURE_OPENAI_ENDPOINT", "https://example.openai.azure.com")
    monkeypatch.setenv("AZURE_OPENAI_KEY", "fake")
    monkeypatch.setenv("LLM_DEFAULT", "chat-gpt41mini")
    monkeypatch.setenv("LLM_SYNTHESIS", "chat-gpt41")
    reset_settings()

    captured = {}

    class _FakeClient:
        def __init__(self, **kw):
            pass

        class chat:
            class completions:
                @staticmethod
                def create(*, model, messages, max_tokens, temperature):
                    captured["model"] = model
                    r = MagicMock()
                    r.choices = [MagicMock(message=MagicMock(content="text"))]
                    return r

    # Install a fake openai module
    openai_module = types.ModuleType("openai")
    openai_module.AzureOpenAI = _FakeClient
    monkeypatch.setitem(sys.modules, "openai", openai_module)

    p = AzureOpenAIProvider()
    out = p.complete([{"role": "user", "content": "x"}], tier="default")
    assert out == "text"
    assert captured["model"] == "chat-gpt41mini"

    captured.clear()
    p.complete([{"role": "user", "content": "x"}], tier="synthesis")
    assert captured["model"] == "chat-gpt41"


def test_anthropic_uses_claude_haiku_for_default_tier(monkeypatch):
    """Verify Anthropic provider's tier-to-model mapping."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")

    captured = {}

    class _FakeMessages:
        @staticmethod
        def create(**kwargs):
            captured.update(kwargs)
            # Emulate the content-block response shape
            block = MagicMock()
            block.type = "text"
            block.text = "anthropic reply"
            r = MagicMock()
            r.content = [block]
            return r

    class _FakeClient:
        def __init__(self, *_a, **_k):
            self.messages = _FakeMessages()

    anthropic_module = types.ModuleType("anthropic")
    anthropic_module.Anthropic = _FakeClient
    monkeypatch.setitem(sys.modules, "anthropic", anthropic_module)

    p = AnthropicProvider()
    out = p.complete([{"role": "user", "content": "x"}], tier="default")
    assert out == "anthropic reply"
    assert captured["model"] == "claude-haiku-4-5"
    assert captured["messages"] == [{"role": "user", "content": "x"}]


def test_anthropic_system_is_top_level_not_role(monkeypatch):
    """Anthropic expects `system=...` as a kwarg, not a message with role='system'."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
    captured = {}

    class _FakeClient:
        class messages:
            @staticmethod
            def create(**kwargs):
                captured.update(kwargs)
                block = MagicMock(); block.type = "text"; block.text = "ok"
                r = MagicMock(); r.content = [block]
                return r

    anthropic_module = types.ModuleType("anthropic")
    anthropic_module.Anthropic = lambda **_: _FakeClient()
    monkeypatch.setitem(sys.modules, "anthropic", anthropic_module)

    AnthropicProvider().complete(
        [{"role": "user", "content": "hi"}],
        system="Be terse.",
    )
    assert captured["system"] == "Be terse."
    # system message not folded into messages list
    assert all(m["role"] != "system" for m in captured["messages"])
