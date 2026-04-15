"""Deprecated re-export — use `wfdos_common.graph.auth` instead. See #17."""

from wfdos_common.graph.auth import *  # noqa: F401, F403
from wfdos_common.graph.auth import (  # noqa: F401
    _get_credential,
    get_graph_client,
    graph_post,
)
