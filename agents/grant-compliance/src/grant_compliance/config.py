"""Application settings loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Core
    app_env: Literal["development", "staging", "production"] = "development"
    database_url: str = "sqlite:///./grant_compliance.db"

    # LLM
    llm_provider: Literal["anthropic", "mock"] = "mock"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-opus-4-7"
    llm_confidence_threshold: float = 0.75

    # QuickBooks
    qb_client_id: str = ""
    qb_client_secret: str = ""
    qb_redirect_uri: str = "http://localhost:8000/qb/callback"
    qb_environment: Literal["sandbox", "production"] = "sandbox"

    # Microsoft Graph (Azure AD / Entra)
    msgraph_tenant_id: str = ""  # Azure AD tenant; "common" allowed for dev
    msgraph_client_id: str = ""
    msgraph_client_secret: str = ""
    msgraph_redirect_uri: str = "http://localhost:8000/msgraph/callback"

    # Encryption
    encryption_key: str = ""

    # Dev auth
    dev_user_email: str = "dev@example.org"
    dev_user_name: str = "Dev User"


@lru_cache
def get_settings() -> Settings:
    return Settings()
