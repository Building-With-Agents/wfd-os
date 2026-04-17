"""Microsoft Graph OAuth2 (Azure AD / Microsoft Entra) flow.

Setup:
  1. Register an app at https://entra.microsoft.com → App registrations
  2. Add a redirect URI matching MSGRAPH_REDIRECT_URI in your .env
  3. Add API permissions (delegated) for the resources you need:
        - Chat.Read, ChannelMessage.Read.All           (Teams)
        - Sites.Read.All, Files.Read.All               (SharePoint)
        - Mail.Read                                    (Outlook)
        - User.Read, offline_access                    (token refresh)
     Then grant admin consent for the org.
  4. Create a client secret; copy it into MSGRAPH_CLIENT_SECRET
  5. Visit /msgraph/connect to start the user flow

Tokens:
  - access_token: ~1 hour TTL
  - refresh_token: long-lived (delivered when `offline_access` is in scopes)
Encrypt both at rest using cryptography.Fernet with ENCRYPTION_KEY.

For unattended/service-account use cases (e.g. nightly sync), use the
client-credentials flow instead — see `client_credentials_token()`.
That requires *application* permissions, not delegated, and is a separate
admin-consent process.
"""

from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx

from grant_compliance.config import get_settings

# Tenant-specific endpoints; substitute MSGRAPH_TENANT_ID at runtime
AUTH_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/authorize"
TOKEN_URL_TEMPLATE = "https://login.microsoftonline.com/{tenant}/oauth2/v2.0/token"

# Default delegated scopes for the grant compliance system. Add/remove as needed.
DEFAULT_SCOPES = (
    "openid",
    "profile",
    "offline_access",
    "User.Read",
    "Chat.Read",
    "ChannelMessage.Read.All",
    "Sites.Read.All",
    "Files.Read.All",
    "Mail.Read",
)


def build_authorize_url(
    state: str | None = None, scopes: tuple[str, ...] = DEFAULT_SCOPES
) -> tuple[str, str]:
    """Return (url, state). Save state in the session and validate on callback."""
    settings = get_settings()
    state = state or secrets.token_urlsafe(24)
    auth_url = AUTH_URL_TEMPLATE.format(tenant=settings.msgraph_tenant_id or "common")
    params = {
        "client_id": settings.msgraph_client_id,
        "response_type": "code",
        "redirect_uri": settings.msgraph_redirect_uri,
        "response_mode": "query",
        "scope": " ".join(scopes),
        "state": state,
    }
    return f"{auth_url}?{urlencode(params)}", state


def exchange_code(code: str, scopes: tuple[str, ...] = DEFAULT_SCOPES) -> dict:
    settings = get_settings()
    token_url = TOKEN_URL_TEMPLATE.format(tenant=settings.msgraph_tenant_id or "common")
    response = httpx.post(
        token_url,
        data={
            "client_id": settings.msgraph_client_id,
            "scope": " ".join(scopes),
            "code": code,
            "redirect_uri": settings.msgraph_redirect_uri,
            "grant_type": "authorization_code",
            "client_secret": settings.msgraph_client_secret,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def refresh_access_token(refresh_token: str, scopes: tuple[str, ...] = DEFAULT_SCOPES) -> dict:
    settings = get_settings()
    token_url = TOKEN_URL_TEMPLATE.format(tenant=settings.msgraph_tenant_id or "common")
    response = httpx.post(
        token_url,
        data={
            "client_id": settings.msgraph_client_id,
            "scope": " ".join(scopes),
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
            "client_secret": settings.msgraph_client_secret,
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def client_credentials_token() -> dict:
    """Service-account / unattended flow. Requires application permissions
    (not delegated) on the Azure AD app, with admin consent granted.

    Use this for nightly sync jobs, not for interactive user actions.
    """
    settings = get_settings()
    if not settings.msgraph_tenant_id:
        raise RuntimeError(
            "MSGRAPH_TENANT_ID is required for client_credentials flow "
            "(cannot use 'common')."
        )
    token_url = TOKEN_URL_TEMPLATE.format(tenant=settings.msgraph_tenant_id)
    response = httpx.post(
        token_url,
        data={
            "client_id": settings.msgraph_client_id,
            "scope": "https://graph.microsoft.com/.default",
            "client_secret": settings.msgraph_client_secret,
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
