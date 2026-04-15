"""Deprecated re-export — use `wfdos_common.email` instead. See #17.

The canonical implementation lives at packages/wfdos-common/wfdos_common/email/.
This module remains as a star-import shim for one deprecation cycle so existing
importers (`from agents.portal.email import send_email`) keep working without
change.
"""

from wfdos_common.email import *  # noqa: F401, F403
from wfdos_common.email import (  # noqa: F401  explicit public API for clarity
    DEFAULT_SENDER,
    GRAPH_BASE,
    notify_internal,
    send_email,
)
