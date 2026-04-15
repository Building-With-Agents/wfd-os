"""wfdos_common.config — centralized Pydantic Settings for all services.

Single source of truth for environment-driven configuration. Each service
imports `settings` from here and reads its values instead of scattered
`os.getenv()` calls across the codebase (see #18 for the migration).

The settings object is lazy: loading is deferred until first access, so
importing this module does not read the environment. This lets tests
monkeypatch env vars before the first settings access.

Migration invariant (#18): every existing env var in `.env.example` is
represented here with the same name and case, so nothing breaks when
services migrate. New aliases (e.g. for CFA → Waifinder decoupling) are
added alongside old names with deprecation logging, not as renames.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import find_dotenv, load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Auto-load the repo-root .env. find_dotenv walks up from CWD.
_dotenv_path = find_dotenv(usecwd=True)
if _dotenv_path:
    load_dotenv(_dotenv_path, override=False)


class PgSettings(BaseSettings):
    """PostgreSQL connection parameters.

    PG_PASSWORD is sourced from scripts/pgconfig.py at runtime by existing
    code; we do not require it here so services importing this settings
    module do not fail-start if the password is still being fetched via
    the existing mechanism.
    """

    host: str = Field(default="localhost", alias="PG_HOST")
    port: int = Field(default=5432, alias="PG_PORT")
    user: str = Field(default="postgres", alias="PG_USER")
    database: str = Field(default="wfdos", alias="PG_DATABASE")
    password: Optional[str] = Field(default=None, alias="PG_PASSWORD")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class AzureSettings(BaseSettings):
    """Azure AD / WFD-OS app registration."""

    tenant_id: str = Field(default="", alias="AZURE_TENANT_ID")
    client_id: str = Field(default="", alias="AZURE_CLIENT_ID")
    client_secret: str = Field(default="", alias="AZURE_CLIENT_SECRET")
    subscription_primary: str = Field(default="", alias="AZURE_SUBSCRIPTION_PRIMARY")
    subscription_cfax: str = Field(default="", alias="AZURE_SUBSCRIPTION_CFAX")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class AzureOpenAISettings(BaseSettings):
    """Azure OpenAI endpoint + key. Default LLM provider per CLAUDE.md."""

    endpoint: str = Field(default="", alias="AZURE_OPENAI_ENDPOINT")
    key: str = Field(default="", alias="AZURE_OPENAI_KEY")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class BlobSettings(BaseSettings):
    connection_string: str = Field(default="", alias="BLOB_CONNECTION_STRING")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class AzureFunctionSettings(BaseSettings):
    """Legacy Azure Function matching endpoint."""

    app_url: str = Field(default="", alias="FUNCTION_APP_URL")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class DynamicsSettings(BaseSettings):
    dev_url: str = Field(default="", alias="DYNAMICS_DEV_URL")
    primary_url: str = Field(default="", alias="DYNAMICS_PRIMARY_URL")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class GraphSettings(BaseSettings):
    """Microsoft Graph API app registration (separate from WFD-OS app)."""

    tenant_id: str = Field(default="", alias="GRAPH_TENANT_ID")
    client_id: str = Field(default="", alias="GRAPH_CLIENT_ID")
    client_secret: str = Field(default="", alias="GRAPH_CLIENT_SECRET")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class SharePointSettings(BaseSettings):
    tenant_url: str = Field(
        default="https://computinforall.sharepoint.com",
        alias="SHAREPOINT_TENANT_URL",
    )
    internal_site_id: str = Field(default="", alias="INTERNAL_SITE_ID")
    # TODO(#18): CFA-specific identifier; flip to a neutral name + dual-read when
    # CFA→Waifinder migration happens. Keeping alias stable preserves current behavior.
    cfa_client_portal_site_id: str = Field(default="", alias="CFA_CLIENT_PORTAL_SITE_ID")
    grant_site_id: str = Field(default="", alias="GRANT_SHAREPOINT_SITE_ID")
    grant_site_url: str = Field(default="", alias="GRANT_SHAREPOINT_SITE_URL")
    grant_folder: str = Field(
        default="WJI-Grant-Agent/monthly-uploads",
        alias="GRANT_SHAREPOINT_FOLDER",
    )

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class TeamsSettings(BaseSettings):
    # TODO(#18): cfa_team_id — CFA-specific; move to tenancy config on CFA→Waifinder flip.
    cfa_team_id: str = Field(default="", alias="CFA_TEAM_ID")
    scoping_notify_channel_id: str = Field(default="", alias="SCOPING_NOTIFY_CHANNEL_ID")
    scoping_webhook_url: str = Field(default="", alias="SCOPING_WEBHOOK_URL")
    leadership_team_id: str = Field(default="", alias="TEAMS_LEADERSHIP_TEAM_ID")
    wsb_channel_id: str = Field(default="", alias="TEAMS_WSB_CHANNEL_ID")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class BotSettings(BaseSettings):
    """Waifinder Bot Framework app credentials."""

    waifinder_app_id: str = Field(default="", alias="WAIFINDER_APP_ID")
    waifinder_app_password: str = Field(default="", alias="WAIFINDER_APP_PASSWORD")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class LlmSettings(BaseSettings):
    """LLM provider configuration. Default: Azure OpenAI per CLAUDE.md.

    Fallback providers (Anthropic, Gemini) used when the configured provider
    has no valid credentials. The provider-routing logic lives in
    wfdos_common.llm (implemented in #20); this module only exposes the
    configured values.
    """

    # Provider selection
    provider: str = Field(default="azure_openai", alias="LLM_PROVIDER")
    default_tier_model: str = Field(default="chat-gpt41mini", alias="LLM_DEFAULT")
    synthesis_tier_model: str = Field(default="chat-gpt41", alias="LLM_SYNTHESIS")

    # Provider credentials (Azure OpenAI lives in its own class above; these
    # are the fallback-provider creds)
    anthropic_api_key: str = Field(default="", alias="ANTHROPIC_API_KEY")
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    # TODO(#20): gemini model string is legacy; LLM adapter will pick per tier.
    gemini_model: str = Field(default="gemini-2.5-flash", alias="GEMINI_MODEL")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class EmailSettings(BaseSettings):
    """Email dispatch defaults.

    TODO(#18): sender/notify defaults are CFA-specific ("ritu@computingforall.org").
    The CFA→Waifinder identity audit will move these to a neutral default set by
    the deploying tenant. Keeping literals in place preserves current behavior.
    """

    sender: str = Field(default="ritu@computingforall.org", alias="EMAIL_SENDER")
    notify: str = Field(default="ritu@computingforall.org", alias="NOTIFY_EMAIL")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class ApolloSettings(BaseSettings):
    api_key: str = Field(default="", alias="APOLLO_API_KEY")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class ProfileSettings(BaseSettings):
    """Profile agent paths. Fixes hardcoded C:/Users/ritub/ in earlier code
    by defaulting to a repo-relative path under scripts/.
    """

    resume_storage_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[3] / "scripts",
        alias="PROFILE_RESUME_STORAGE_PATH",
    )
    env_path: Path = Field(
        default_factory=lambda: Path(__file__).resolve().parents[3] / ".env",
        alias="PROFILE_ENV_PATH",
    )

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class TenancySettings(BaseSettings):
    """Multi-tenant configuration (used by #22 DB engine factory, #16 white-label).

    Waifinder-flagship is the default tenant. Client white-label deployments
    set their own tenant_id via env.
    """

    default_tenant_id: str = Field(default="waifinder-flagship", alias="WFDOS_DEFAULT_TENANT_ID")

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class Settings(BaseSettings):
    """Top-level settings aggregator. Services import this as `settings`.

    Usage:

        from wfdos_common.config import settings
        conn = psycopg2.connect(
            host=settings.pg.host, port=settings.pg.port,
            user=settings.pg.user, database=settings.pg.database,
            password=settings.pg.password,
        )
    """

    pg: PgSettings = Field(default_factory=PgSettings)
    azure: AzureSettings = Field(default_factory=AzureSettings)
    azure_openai: AzureOpenAISettings = Field(default_factory=AzureOpenAISettings)
    blob: BlobSettings = Field(default_factory=BlobSettings)
    azure_function: AzureFunctionSettings = Field(default_factory=AzureFunctionSettings)
    dynamics: DynamicsSettings = Field(default_factory=DynamicsSettings)
    graph: GraphSettings = Field(default_factory=GraphSettings)
    sharepoint: SharePointSettings = Field(default_factory=SharePointSettings)
    teams: TeamsSettings = Field(default_factory=TeamsSettings)
    bot: BotSettings = Field(default_factory=BotSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    apollo: ApolloSettings = Field(default_factory=ApolloSettings)
    profile: ProfileSettings = Field(default_factory=ProfileSettings)
    tenancy: TenancySettings = Field(default_factory=TenancySettings)

    model_config = SettingsConfigDict(extra="ignore")


@lru_cache(maxsize=1)
def _load_settings() -> Settings:
    """Lazily construct the settings singleton. Cached — constructed once
    per process. Use reset_settings() in tests to pick up env changes.
    """
    return Settings()


def reset_settings() -> None:
    """Test hook: clear the cached settings so the next access re-reads env."""
    _load_settings.cache_clear()


class _SettingsProxy:
    """Attribute-lookup proxy so `from wfdos_common.config import settings`
    gives callers a lazy-loaded singleton.
    """

    def __getattr__(self, name: str):
        return getattr(_load_settings(), name)

    def __repr__(self) -> str:
        return repr(_load_settings())


settings = _SettingsProxy()


def require(*paths: str) -> None:
    """Fail-fast validator — raise ConfigurationError if any required env var
    is missing (empty or None). Services call this at startup to surface
    misconfig early.

    Each `path` is a dot-separated setting access, e.g. "pg.host",
    "graph.client_secret".

    Usage:

        from wfdos_common.config import require
        require("pg.host", "pg.database", "graph.tenant_id", "graph.client_secret")
    """
    missing: list[str] = []
    for path in paths:
        cur = _load_settings()
        for part in path.split("."):
            cur = getattr(cur, part, None)
            if cur is None:
                missing.append(path)
                break
        else:
            if cur == "" or cur is None:
                missing.append(path)
    if missing:
        raise ConfigurationError(
            "Missing required configuration: " + ", ".join(missing)
            + ". Set these in your .env file or environment."
        )


class ConfigurationError(RuntimeError):
    """Raised when required configuration is missing at startup."""

    pass
