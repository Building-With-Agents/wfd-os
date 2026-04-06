"""Shared configuration for WFD OS Graph API agents.

Reads GRAPH_* environment variables from wfd-os/.env and exposes them under
the canonical names used by the Scoping Agent / Grant Agent code.

Supports both GRAPH_* (WFD OS convention) and AZURE_* (legacy convention)
variable names so we can migrate old code without rewriting every file.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Walk up from this file to find wfd-os/.env
_ENV_PATH = Path(__file__).resolve().parents[2] / ".env"
load_dotenv(_ENV_PATH, override=True)


def _get(*keys: str, default: str = "") -> str:
    """Return the first env var that is set, checking multiple possible names."""
    for key in keys:
        val = os.getenv(key)
        if val:
            return val
    return default


# Microsoft Graph API — Scoping/Grant Agent credentials
# (Different from WFD-OS app registration; this one has Graph API permissions)
AZURE_TENANT_ID = _get("GRAPH_TENANT_ID", "AZURE_TENANT_ID")
AZURE_CLIENT_ID = _get("GRAPH_CLIENT_ID")
AZURE_CLIENT_SECRET = _get("GRAPH_CLIENT_SECRET")

# If the legacy AZURE_CLIENT_ID is actually the Scoping Agent one (60a49f2a...),
# fall back to it. But in wfd-os/.env the AZURE_CLIENT_ID is the WFD-OS app,
# so we only use GRAPH_* for Scoping/Grant operations.
if not AZURE_CLIENT_ID:
    AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")
if not AZURE_CLIENT_SECRET:
    AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")

# SharePoint
SHAREPOINT_TENANT_URL = _get(
    "SHAREPOINT_TENANT_URL",
    default="https://computinforall.sharepoint.com",
)
INTERNAL_SITE_ID = _get("INTERNAL_SITE_ID")
CFA_CLIENT_PORTAL_SITE_ID = _get("CFA_CLIENT_PORTAL_SITE_ID")

# Grant Agent SharePoint (CFAOperationsHRFinance)
GRANT_SHAREPOINT_SITE_URL = _get(
    "GRANT_SHAREPOINT_SITE_URL",
    "SHAREPOINT_SITE_URL",
)
GRANT_SHAREPOINT_SITE_ID = _get(
    "GRANT_SHAREPOINT_SITE_ID",
    "SHAREPOINT_SITE_ID",
)
GRANT_SHAREPOINT_FOLDER = _get(
    "GRANT_SHAREPOINT_FOLDER",
    "SHAREPOINT_FOLDER",
    default="WJI-Grant-Agent/monthly-uploads",
)

# Teams
CFA_TEAM_ID = _get("CFA_TEAM_ID")
SCOPING_NOTIFY_CHANNEL_ID = _get("SCOPING_NOTIFY_CHANNEL_ID")
SCOPING_WEBHOOK_URL = _get("SCOPING_WEBHOOK_URL")

# Web search (unused - Claude's built-in web_search is used instead)
BING_SEARCH_API_KEY = _get("BING_SEARCH_API_KEY")

# Anthropic (shared with rest of WFD OS)
ANTHROPIC_API_KEY = _get("ANTHROPIC_API_KEY")
CLAUDE_MODEL = _get("CLAUDE_MODEL", default="claude-sonnet-4-20250514")
