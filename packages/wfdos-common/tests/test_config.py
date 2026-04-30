"""Tests for wfdos_common.config — Pydantic Settings + pluggable backends (#18)."""

import os

import pytest

from wfdos_common.config import (
    ConfigurationError,
    EnvBackend,
    Settings,
    get_secret_backend,
    require,
    reset_settings,
    settings,
)


def test_settings_loads_from_env(monkeypatch):
    """Values come from the process environment via Pydantic Settings."""
    monkeypatch.setenv("PG_HOST", "test-db.example.com")
    monkeypatch.setenv("PG_PORT", "5433")
    reset_settings()

    assert settings.pg.host == "test-db.example.com"
    assert settings.pg.port == 5433


def test_settings_has_sensible_defaults(monkeypatch):
    """Unset env vars get their declared defaults rather than crashing."""
    for var in [
        "PG_HOST", "PG_PORT", "PG_USER", "PG_DATABASE",
        "AZURE_TENANT_ID", "SHAREPOINT_TENANT_URL", "LLM_PROVIDER",
        "WFDOS_DEFAULT_TENANT_ID",
    ]:
        monkeypatch.delenv(var, raising=False)
    reset_settings()

    assert settings.pg.host == "localhost"
    assert settings.pg.port == 5432
    assert settings.pg.user == "postgres"
    assert settings.pg.database == "wfdos"
    assert settings.sharepoint.tenant_url == "https://computinforall.sharepoint.com"
    assert settings.llm.provider == "azure_openai"
    assert settings.tenancy.default_tenant_id == "waifinder-flagship"


def test_require_passes_when_vars_set(monkeypatch):
    monkeypatch.setenv("PG_HOST", "present")
    monkeypatch.setenv("PG_DATABASE", "present")
    reset_settings()
    # Should not raise
    require("pg.host", "pg.database")


def test_require_raises_on_missing(monkeypatch):
    """require() lists every missing key in one error message."""
    monkeypatch.setenv("PG_HOST", "")
    monkeypatch.setenv("AZURE_TENANT_ID", "")
    reset_settings()

    with pytest.raises(ConfigurationError) as excinfo:
        require("pg.host", "azure.tenant_id")

    msg = str(excinfo.value)
    assert "pg.host" in msg
    assert "azure.tenant_id" in msg


def test_env_backend_reads_process_env(monkeypatch):
    monkeypatch.setenv("SOME_SECRET", "hunter2")
    backend = EnvBackend()
    assert backend.get("SOME_SECRET") == "hunter2"
    assert backend.get("DOES_NOT_EXIST") is None


def test_backend_selector_defaults_to_env(monkeypatch):
    monkeypatch.delenv("WFDOS_SECRET_BACKEND", raising=False)
    backend = get_secret_backend()
    assert isinstance(backend, EnvBackend)


def test_backend_selector_env_explicit(monkeypatch):
    monkeypatch.setenv("WFDOS_SECRET_BACKEND", "env")
    backend = get_secret_backend()
    assert isinstance(backend, EnvBackend)


def test_backend_selector_unknown_raises(monkeypatch):
    monkeypatch.setenv("WFDOS_SECRET_BACKEND", "nonexistent")
    with pytest.raises(ValueError) as excinfo:
        get_secret_backend()
    assert "nonexistent" in str(excinfo.value)


def test_backend_selector_plugin_not_installed(monkeypatch):
    """Requesting a backend whose extras aren't installed raises a clear ImportError."""
    monkeypatch.setenv("WFDOS_SECRET_BACKEND", "keyvault")
    with pytest.raises(ImportError) as excinfo:
        get_secret_backend()
    assert "keyvault" in str(excinfo.value).lower()


def test_llm_provider_defaults_azure_openai(monkeypatch):
    """Azure OpenAI is the default LLM provider per CLAUDE.md llm-provider.mdc."""
    monkeypatch.delenv("LLM_PROVIDER", raising=False)
    reset_settings()
    assert settings.llm.provider == "azure_openai"
    assert settings.llm.default_tier_model == "chat-gpt41mini"
    assert settings.llm.synthesis_tier_model == "chat-gpt41"


def test_settings_repr_does_not_crash():
    """Proxy object repr exercises settings loading."""
    # Just verifies it doesn't raise — contents depend on env.
    _ = repr(settings)
