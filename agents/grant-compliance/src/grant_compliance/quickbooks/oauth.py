"""QuickBooks Online OAuth2 flow.

Intuit uses OAuth2 with a slightly unusual flow: after authorization, you
get an `access_token` (1 hour TTL), `refresh_token` (100 day TTL), and a
`realmId` that identifies the QB company. Store all three encrypted.

Production setup:
  1. Create an app at https://developer.intuit.com/
  2. Set redirect URI to QB_REDIRECT_URI in your .env
  3. Copy Client ID + Secret into .env
  4. Visit /qb/connect to start the flow

This module is a SKELETON. Real implementation needs:
  - Encrypted token storage (use cryptography.Fernet with ENCRYPTION_KEY)
  - Token refresh on 401
  - Realm/tenant model if you ever support multiple QB files
"""

from __future__ import annotations

import secrets
from urllib.parse import urlencode

import httpx

from grant_compliance.config import get_settings

AUTH_URL = "https://appcenter.intuit.com/connect/oauth2"
TOKEN_URL = "https://oauth.platform.intuit.com/oauth2/v1/tokens/bearer"

SCOPES = "com.intuit.quickbooks.accounting"


def build_authorize_url(state: str | None = None) -> tuple[str, str]:
    """Return (url, state). Save state in the user's session and validate on callback."""
    settings = get_settings()
    state = state or secrets.token_urlsafe(24)
    params = {
        "client_id": settings.qb_client_id,
        "scope": SCOPES,
        "redirect_uri": settings.qb_redirect_uri,
        "response_type": "code",
        "state": state,
    }
    return f"{AUTH_URL}?{urlencode(params)}", state


def exchange_code(code: str) -> dict:
    """Exchange authorization code for tokens. Returns the raw token JSON."""
    settings = get_settings()
    response = httpx.post(
        TOKEN_URL,
        auth=(settings.qb_client_id, settings.qb_client_secret),
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": settings.qb_redirect_uri,
        },
        headers={"Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


def refresh_access_token(refresh_token: str) -> dict:
    settings = get_settings()
    response = httpx.post(
        TOKEN_URL,
        auth=(settings.qb_client_id, settings.qb_client_secret),
        data={"grant_type": "refresh_token", "refresh_token": refresh_token},
        headers={"Accept": "application/json"},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
