"""Import-smoke every wfdos_common surface + every agent service module.

Catches stale sys.path hacks or namespace drift. No HTTP — just imports.
"""

from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(_REPO_ROOT / "scripts" / "smoke"))

from _common import fail, ok  # noqa: E402

try:
    from wfdos_common.config import settings, PG_CONFIG  # noqa: F401
    from wfdos_common.auth import (  # noqa: F401
        build_auth_router,
        require_role,
        SessionMiddleware,
    )
    from wfdos_common.tenancy import (  # noqa: F401
        get_brand,
        TenantResolutionMiddleware,
    )
    from wfdos_common.agent import Agent, EchoAgent  # noqa: F401
    from wfdos_common.errors import install_error_handlers  # noqa: F401
    from wfdos_common.logging import configure, get_logger  # noqa: F401
    from wfdos_common.llm import complete  # noqa: F401
    from wfdos_common.models import APIEnvelope, ErrorDetail  # noqa: F401

    import agents.laborpulse.api  # noqa: F401
    import agents.laborpulse.client  # noqa: F401
    import agents.portal.consulting_api  # noqa: F401
    import agents.assistant.api  # noqa: F401
    import agents.apollo.api  # noqa: F401
except Exception as e:
    fail(f"import failed: {type(e).__name__}: {e}")

ok("wfdos_common + agents.* import")
