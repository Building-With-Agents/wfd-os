"""Microsoft Graph integration: Teams, SharePoint, Outlook, Dynamics."""

from grant_compliance.integrations.msgraph.client import GraphClient
from grant_compliance.integrations.msgraph.oauth import (
    build_authorize_url,
    exchange_code,
    refresh_access_token,
)

__all__ = [
    "GraphClient",
    "build_authorize_url",
    "exchange_code",
    "refresh_access_token",
]
