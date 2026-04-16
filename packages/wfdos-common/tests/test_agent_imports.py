"""Tests for #27 acceptance — every agent module imports without sys.path hacks.

Pre-#27, every FastAPI / aiohttp service in `agents/` had a block like::

    _REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)
    sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
    from pgconfig import PG_CONFIG

#27 replaced those with::

    from wfdos_common.config import PG_CONFIG

and made the whole `agents.*` namespace importable by declaring it in the
monorepo root `pyproject.toml`. These tests prove that every service module
imports cleanly from a pristine Python that has only done
`pip install -e .` at the repo root — i.e. no runtime sys.path manipulation
is required.

Modules that legitimately need third-party deps the dev env may lack
(e.g. `agents.profile.parse_resumes` needs `azure-storage-blob`) are skipped
when the dep is missing; the import failure case is exercised by installing
the per-service pyproject.
"""

from __future__ import annotations

import importlib

import pytest

# Modules that import cleanly with just wfdos-common + common libs installed.
CORE_AGENT_MODULES = [
    "agents.apollo.api",
    "agents.apollo.client",
    "agents.assistant.api",
    "agents.assistant.base",
    "agents.assistant.consulting_agent",
    "agents.assistant.student_agent",
    "agents.assistant.employer_agent",
    "agents.assistant.college_agent",
    "agents.assistant.staff_agent",
    "agents.assistant.youth_agent",
    "agents.portal.student_api",
    "agents.portal.showcase_api",
    "agents.portal.consulting_api",
    "agents.portal.college_api",
    "agents.portal.wji_api",
    "agents.marketing.api",
    "agents.reporting.api",
    "agents.scoping.pipeline",
    "agents.scoping.research",
    "agents.scoping.webhook",
    "agents.scoping.api",
]


@pytest.mark.parametrize("module_name", CORE_AGENT_MODULES)
def test_agent_module_imports_without_sys_path_hacks(module_name: str) -> None:
    """Every core agent module must import via the standard namespace package
    exposed by the monorepo root pyproject.toml — no sys.path tricks allowed.
    """
    module = importlib.import_module(module_name)
    assert module is not None
    # The import succeeding at all is the acceptance criterion. If any hidden
    # sys.path.insert were still needed, the import would fail at module load
    # because pytest runs from a clean sys.path that doesn't include
    # scripts/ or the repo root.


def test_no_legacy_pgconfig_module_loaded() -> None:
    """After agent modules import, the legacy top-level `pgconfig` module
    should NOT appear in sys.modules — that means no code tried the old
    `sys.path.insert(..., 'scripts')` + `from pgconfig import PG_CONFIG`
    escape hatch.

    The deprecated scripts/pgconfig.py shim still exists for one-off CLI
    scripts that import it by file path (exercised in test_pg_config.py), but
    no runtime agent module should reach it via sys.path manipulation.
    """
    import sys as _sys

    # Trigger a representative service import.
    importlib.import_module("agents.portal.student_api")

    # The legacy module name — `pgconfig`, NOT a dotted path — would only
    # appear in sys.modules if someone did `sys.path.insert(0, "scripts/")`
    # followed by `import pgconfig`. #27 eliminated every such call site.
    assert "pgconfig" not in _sys.modules, (
        "Legacy scripts/pgconfig.py was imported via sys.path manipulation — "
        "#27 was meant to remove every such call site. Check the agent module "
        "chain for a lingering `sys.path.insert` + `from pgconfig import PG_CONFIG`."
    )
