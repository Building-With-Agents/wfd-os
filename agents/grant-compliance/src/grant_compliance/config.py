"""Application settings loaded from environment / .env."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load order (later files override earlier):
    #   1. wfd-os repo root .env  (QB/Anthropic/MS Graph creds shared with other agents)
    #   2. agents/grant-compliance/.env  (DATABASE_URL + scaffold-specific overrides)
    # The scaffold's own .env wins for anything it sets; falls back to
    # wfd-os root for creds that are shared across the platform.
    # extra="ignore" → unrelated wfd-os env vars (GEMINI_API_KEY, PG_PASSWORD,
    # QB_COMPANY_ID if present, etc.) don't error; they're just ignored.
    model_config = SettingsConfigDict(
        env_file=("../../.env", ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

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

    # -----------------------------------------------------------------
    # ENFORCED STARTUP GUARD — production QB requires encryption key
    # -----------------------------------------------------------------
    # If QB_ENVIRONMENT=production and ENCRYPTION_KEY is empty, we refuse to
    # construct Settings at all. The first caller of get_settings() — which
    # happens during scaffold startup (FastAPI lifespan, Alembic env.py,
    # tests, CLI scripts) — raises RuntimeError with a clear message.
    #
    # Rationale: QuickBooks OAuth access/refresh tokens granted against a
    # production QB account grant read access to the org's real financial
    # ledger. Storing those in plaintext in the DB violates the rule in
    # CLAUDE.md "Things you should NOT do" ("Do not store API keys or
    # OAuth tokens in plaintext in the DB"). For sandbox, plaintext is
    # tolerable because sandbox data is synthetic and the tokens can't
    # reach real records. Production is strictly a different class of risk.
    #
    # This guard is architectural, not a policy check — like the QB
    # read-only enforcement in quickbooks/client.py, the goal is "cannot
    # happen by accident." See CLAUDE.md "Enforced constraints" section.
    @model_validator(mode="after")
    def _refuse_production_without_encryption_key(self) -> "Settings":
        if self.qb_environment == "production" and not self.encryption_key:
            raise RuntimeError(
                "REFUSING TO START: QB_ENVIRONMENT=production but "
                "ENCRYPTION_KEY is not set.\n\n"
                "Storing QuickBooks OAuth tokens in plaintext against a "
                "production QB account is a compliance violation per "
                "CLAUDE.md 'Things you should NOT do'.\n\n"
                "To proceed you must either:\n"
                "  (a) Set ENCRYPTION_KEY to a Fernet key. Generate one with:\n"
                "      python -c \"from cryptography.fernet import Fernet; "
                "print(Fernet.generate_key().decode())\"\n"
                "  (b) OR flip QB_ENVIRONMENT back to 'sandbox' for "
                "continued development.\n\n"
                "This guard is intentional and architectural. Do not bypass "
                "by commenting out this validator."
            )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
