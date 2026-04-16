"""Deprecated re-export — use `wfdos_common.models.scoping` instead. See #21.

The canonical location is `wfdos_common.models.scoping`. This shim lets
existing importers (`from agents.scoping.models import ScopingRequest`,
etc.) keep working for one deprecation cycle. Flip callers to the new
path when touching them; when no known importer references this shim,
remove it in a follow-up PR.
"""

from wfdos_common.models.scoping import *  # noqa: F401, F403
from wfdos_common.models.scoping import (  # noqa: F401  explicit re-exports
    Contact,
    Organization,
    ResearchResult,
    ScopingAnalysis,
    ScopingAnswer,
    ScopingRequest,
)
