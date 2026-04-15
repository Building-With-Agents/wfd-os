"""Deprecated re-export — use `wfdos_common.graph.config` instead. See #17."""

from wfdos_common.graph.config import *  # noqa: F401, F403
from wfdos_common.graph.config import (  # noqa: F401  explicit re-exports for module-level constants
    ANTHROPIC_API_KEY,
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    AZURE_TENANT_ID,
    BING_SEARCH_API_KEY,
    CFA_CLIENT_PORTAL_SITE_ID,
    CFA_TEAM_ID,
    CLAUDE_MODEL,
    GRANT_SHAREPOINT_FOLDER,
    GRANT_SHAREPOINT_SITE_ID,
    GRANT_SHAREPOINT_SITE_URL,
    INTERNAL_SITE_ID,
    SCOPING_NOTIFY_CHANNEL_ID,
    SCOPING_WEBHOOK_URL,
    SHAREPOINT_TENANT_URL,
)
