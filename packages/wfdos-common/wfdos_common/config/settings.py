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
from typing import Annotated, Optional

from dotenv import find_dotenv, load_dotenv
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


# Auto-load the repo-root .env. find_dotenv walks up from CWD.
_dotenv_path = find_dotenv(usecwd=True)
if _dotenv_path:
    load_dotenv(_dotenv_path, override=False)


def _find_repo_root() -> Path:
    """Walk up from this file looking for a `.git` directory. Used by
    path-based defaults (resume storage, .env) so the module stays
    portable — returns the right directory whether this file lives at
    packages/wfdos-common/... or is pip-installed into site-packages.

    Falls back to three-levels-up from this file if .git isn't found.
    """
    cur = Path(__file__).resolve().parent
    for _ in range(6):
        if (cur / ".git").exists() or (cur / "pyproject.toml").exists() and (cur / "agents").exists():
            return cur
        cur = cur.parent
    # Fallback — last-resort default. Assumes pre-migration layout.
    return Path(__file__).resolve().parents[4]


class PgSettings(BaseSettings):
    """PostgreSQL connection parameters.

    PG_PASSWORD is sourced from scripts/pgconfig.py at runtime by existing
    code; we do not require it here so services importing this settings
    module do not fail-start if the password is still being fetched via
    the existing mechanism.

    `env_prefix="PG_"` restricts env-var lookup to `PG_HOST` / `PG_USER`
    / etc. Without it, pydantic-settings' default behaviour (combined
    with `populate_by_name=True`) also reads the bare field name as a
    fallback — e.g. `USER=runner` on GitHub Actions or `USER=www-data`
    on a deploy target would silently shadow the `postgres` default.
    Aliases are retained so existing dict-style construction
    (`PgSettings(PG_USER="foo")`) still works.
    """

    host: str = Field(default="localhost", alias="PG_HOST")
    port: int = Field(default=5432, alias="PG_PORT")
    user: str = Field(default="postgres", alias="PG_USER")
    database: str = Field(default="wfdos", alias="PG_DATABASE")
    password: Optional[str] = Field(default=None, alias="PG_PASSWORD")

    model_config = SettingsConfigDict(
        populate_by_name=True,
        extra="ignore",
        env_prefix="PG_",
    )


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
        default_factory=lambda: _find_repo_root() / "scripts",
        alias="PROFILE_RESUME_STORAGE_PATH",
    )
    env_path: Path = Field(
        default_factory=lambda: _find_repo_root() / ".env",
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


class PlatformSettings(BaseSettings):
    """Platform-facing URLs consumed by services (magic-link templates, email
    CTAs, OAuth redirects, etc.)."""

    portal_base_url: str = Field(
        default="http://localhost:3000",
        alias="CLIENT_PORTAL_BASE_URL",
    )
    # Comma-separated list of origins permitted by the CORSMiddleware on
    # every FastAPI service. Defaults cover local dev (Next.js on 3000/3001)
    # plus the two production hostnames behind the edge proxy. Override via
    # WFDOS_ALLOWED_ORIGINS for a tenant-specific deployment. NoDecode keeps
    # pydantic-settings from JSON-parsing the env value before the validator
    # below runs — that's how plain CSV (the natural shell idiom) works.
    allowed_origins: Annotated[list[str], NoDecode] = Field(
        default_factory=lambda: [
            "http://localhost:3000",
            "http://localhost:3001",
            "http://127.0.0.1:3000",
            "https://platform.thewaifinder.com",
            "https://talent.borderplexwfs.org",
        ],
        alias="WFDOS_ALLOWED_ORIGINS",
    )
    # Optional regex for auto-port localhost (e.g. when Next.js falls back
    # to 3001/3002 because 3000 is taken). None disables the regex match.
    allowed_origin_regex: Optional[str] = Field(
        default=r"http://(localhost|127\.0\.0\.1):\d+",
        alias="WFDOS_ALLOWED_ORIGIN_REGEX",
    )
    # Inter-service URL for the assistant API (Gemini-backed chat). Used
    # by student_api when proxying student-portal chat to the assistant
    # router on :8009. Override per deployment if the assistant is on a
    # different host.
    assistant_api_base_url: str = Field(
        default="http://127.0.0.1:8009",
        alias="WFDOS_ASSISTANT_API_BASE_URL",
    )

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_csv_origins(cls, v):
        """Accept either a JSON list or a comma-separated string from env.

        Pydantic-settings parses `list[str]` env values as JSON by
        default, which makes the natural shell idiom
        `WFDOS_ALLOWED_ORIGINS=https://a,https://b` raise. This
        validator splits the CSV form before the type coercion runs.
        """
        if isinstance(v, str):
            return [s.strip() for s in v.split(",") if s.strip()]
        return v

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class JieSettings(BaseSettings):
    """Job-Intelligence-Engine HTTP client config (LaborPulse proxy).

    LaborPulse (`agents/laborpulse/api.py`) forwards streaming Q&A
    requests to JIE's `POST /analytics/query`. All four settings have
    safe-empty defaults so the wfd-os stack boots without JIE creds;
    the proxy raises `ServiceUnavailableError` at call time if
    `base_url` is empty, matching the stripped-.env 503 posture set by
    the @llm_gated tier decorator (#25).
    """

    base_url: str = Field(default="", alias="JIE_BASE_URL")
    # API key header ("X-API-Key: ...") for JIE-side auth. Empty means JIE
    # is unauthenticated (dev / open-localhost).
    api_key: str = Field(default="", alias="JIE_API_KEY")
    # JSON-POST timeout (the non-streaming /feedback path and any quick
    # JIE pings). The streaming /query path uses streaming_read_timeout.
    timeout_seconds: int = Field(default=120, alias="JIE_TIMEOUT_SECONDS")
    # SSE stays open while JIE synthesizes. Generous to cover cold-start
    # + multi-step tool use.
    streaming_read_timeout_seconds: int = Field(
        default=300, alias="JIE_STREAMING_TIMEOUT"
    )

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class AuthSettings(BaseSettings):
    """Magic-link auth (#24) + role-based access settings.

    The `secret_key` signs session cookies + magic-link tokens; rotating
    it invalidates every active session, which is the intended emergency
    response to a secret compromise.

    The two allowlists are environment-driven for now; they'll migrate to
    a `users` table in the shared-infra DB once #22 tenant registry is
    enlarged. Items are comma-separated email addresses.
    """

    # Required — must be set in production. Dev default is safe-looking but
    # clearly-synthetic so it's obvious in logs if it leaks.
    secret_key: str = Field(
        default="dev-only-secret-replace-in-production-do-not-ship",
        alias="WFDOS_AUTH_SECRET_KEY",
    )
    # Token / session TTLs.
    magic_link_ttl_seconds: int = Field(
        default=15 * 60,  # 15 minutes
        alias="WFDOS_AUTH_MAGIC_LINK_TTL",
    )
    session_ttl_seconds: int = Field(
        default=7 * 24 * 60 * 60,  # 7 days
        alias="WFDOS_AUTH_SESSION_TTL",
    )
    # Cookie config.
    cookie_name: str = Field(default="wfdos_session", alias="WFDOS_AUTH_COOKIE_NAME")
    cookie_secure: bool = Field(default=True, alias="WFDOS_AUTH_COOKIE_SECURE")
    cookie_samesite: str = Field(default="lax", alias="WFDOS_AUTH_COOKIE_SAMESITE")
    # Allowlists — comma-separated emails. Empty = no one (deny-all by default).
    staff_allowlist: str = Field(default="", alias="WFDOS_AUTH_STAFF_ALLOWLIST")
    student_allowlist: str = Field(default="", alias="WFDOS_AUTH_STUDENT_ALLOWLIST")
    admin_allowlist: str = Field(default="", alias="WFDOS_AUTH_ADMIN_ALLOWLIST")
    # External customer users on a Waifinder deployment — e.g. Borderplex
    # WFD directors using LaborPulse. Distinct from staff so audit logs +
    # qa_feedback attribution stay separable (#59).
    workforce_development_allowlist: str = Field(
        default="", alias="WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST"
    )
    # Rate limits (requests per hour per role).
    rate_limit_student_per_hour: int = Field(default=100, alias="WFDOS_AUTH_RATE_STUDENT")
    rate_limit_staff_per_hour: int = Field(default=500, alias="WFDOS_AUTH_RATE_STAFF")
    rate_limit_admin_per_hour: int = Field(default=2000, alias="WFDOS_AUTH_RATE_ADMIN")
    # Directors burst-query during demos; same floor as staff (#59).
    rate_limit_workforce_development_per_hour: int = Field(
        default=500, alias="WFDOS_AUTH_RATE_WORKFORCE_DEVELOPMENT"
    )

    model_config = SettingsConfigDict(populate_by_name=True, extra="ignore")


class BotFrameworkSettings(BaseSettings):
    """Microsoft Bot Framework auth (grant bot, market-intelligence bot).

    MICROSOFT_APP_* is the Bot Framework convention used by BotFrameworkAdapter;
    services that need it read these fields rather than the WAIFINDER_APP_*
    aliases (which are the same credentials in a different naming scheme).
    """

    app_id: str = Field(default="", alias="MICROSOFT_APP_ID")
    app_password: str = Field(default="", alias="MICROSOFT_APP_PASSWORD")
    app_tenant_id: str = Field(default="", alias="MICROSOFT_APP_TENANT_ID")

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
    bot_framework: BotFrameworkSettings = Field(default_factory=BotFrameworkSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    apollo: ApolloSettings = Field(default_factory=ApolloSettings)
    profile: ProfileSettings = Field(default_factory=ProfileSettings)
    tenancy: TenancySettings = Field(default_factory=TenancySettings)
    platform: PlatformSettings = Field(default_factory=PlatformSettings)
    auth: AuthSettings = Field(default_factory=AuthSettings)
    jie: JieSettings = Field(default_factory=JieSettings)

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
