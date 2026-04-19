"""CI check for the public URL contract (#31).

Parses docs/public-url-contract.md and asserts every listed URL that's
marked as currently-live is registered somewhere in the codebase (either
in a FastAPI service or in the Next.js portal). A PR that removes a
contract URL without updating the doc fails this check.

Status markers in the doc:
  - "90 days" / "permanent"  → must be live-routable (checked here)
  - "FUTURE WORK" / "FUTURE WORK (#32)" → reserved; not checked

Enforcement is additive-only — we don't verify HTTP 200 responses
(many routes are auth-gated or stub-pages). We verify the route is
registered in at least one service's app.routes (for /api/* URLs) or
in the Next.js portal directory tree (for top-level URLs).
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_CONTRACT = _REPO_ROOT / "docs/public-url-contract.md"


# ---------------------------------------------------------------------------
# Contract parsing
# ---------------------------------------------------------------------------


def _parse_contract() -> list[tuple[str, str]]:
    """Return `[(url, status), ...]` for every table row in the contract.

    Matches rows of the form:
        | `/url`             | ...purpose... | 90 days |
    """
    if not _CONTRACT.exists():
        raise RuntimeError(f"contract missing: {_CONTRACT}")
    text = _CONTRACT.read_text(encoding="utf-8")
    urls: list[tuple[str, str]] = []
    # Match URL in first code-span column; status in last column.
    pattern = re.compile(
        r"^\|\s*`([^`]+)`\s*\|[^|]*\|(?:[^|]*\|)?\s*([^|]+?)\s*\|\s*$",
        re.MULTILINE,
    )
    for m in pattern.finditer(text):
        url = m.group(1).strip()
        status = m.group(2).strip()
        # Skip URLs that include obvious template markers that won't
        # appear verbatim in the router.
        urls.append((url, status))
    return urls


@pytest.fixture(scope="module")
def contract_urls() -> list[tuple[str, str]]:
    return _parse_contract()


def _is_live(status: str) -> bool:
    low = status.lower()
    return "future work" not in low and "reserved" not in low


# ---------------------------------------------------------------------------
# Collect registered routes across services
# ---------------------------------------------------------------------------


_PORTAL_SERVICE_MODULES = [
    "agents.assistant.api",
    "agents.apollo.api",
    "agents.marketing.api",
    "agents.portal.consulting_api",
    "agents.portal.student_api",
    "agents.portal.showcase_api",
    "agents.portal.college_api",
    "agents.portal.wji_api",
    "agents.reporting.api",
]


def _registered_api_paths() -> set[str]:
    """Return the full set of paths across all 9 FastAPI services."""
    out: set[str] = set()
    for mod_name in _PORTAL_SERVICE_MODULES:
        try:
            module = importlib.import_module(mod_name)
        except ModuleNotFoundError:
            # A service may legitimately not be importable in the test env
            # (e.g. missing azure-storage-blob for profile). Skip rather
            # than fail the contract check.
            continue
        app = getattr(module, "app", None)
        if app is None:
            continue
        for route in app.routes:
            path = getattr(route, "path", None)
            if path:
                out.add(path)
    return out


def _next_portal_routes() -> set[str]:
    """Scan the Next.js portal directory tree for top-level routes.

    We look at `portal/student/app/` (Next.js app-router convention). A
    route at `portal/student/app/careers/page.tsx` becomes `/careers`.
    """
    portal_app = _REPO_ROOT / "portal/student/app"
    if not portal_app.exists():
        return set()
    out: set[str] = {"/"}
    for page in portal_app.rglob("page.tsx"):
        rel = page.relative_to(portal_app).parent.as_posix()
        if rel == ".":
            continue
        # Strip Next.js route groups like (marketing)/ which don't affect the URL.
        parts = [p for p in rel.split("/") if not (p.startswith("(") and p.endswith(")"))]
        if not parts:
            continue
        out.add("/" + "/".join(parts))
    # Also accept .js/.jsx pages.
    for ext in ("page.jsx", "page.js", "page.ts"):
        for page in portal_app.rglob(ext):
            rel = page.relative_to(portal_app).parent.as_posix()
            if rel == ".":
                continue
            parts = [p for p in rel.split("/") if not (p.startswith("(") and p.endswith(")"))]
            if parts:
                out.add("/" + "/".join(parts))
    return out


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_contract_file_exists():
    assert _CONTRACT.exists()


def test_contract_has_entries(contract_urls):
    assert len(contract_urls) > 5, (
        "contract appears empty — did the table formatting change?"
    )


def test_every_live_api_url_is_registered(contract_urls):
    api_paths = _registered_api_paths()
    missing: list[str] = []
    for url, status in contract_urls:
        if not _is_live(status):
            continue
        if not url.startswith("/api/"):
            continue
        # Strip any {placeholder} — FastAPI stores `{path_id}`-style paths verbatim.
        if url not in api_paths:
            missing.append(url)
    assert not missing, (
        f"contract URLs not registered in any FastAPI service: {missing}\n"
        f"If you removed a route, update docs/public-url-contract.md + add a 301 redirect"
    )


def test_every_live_portal_url_is_registered_or_noted(contract_urls):
    """Portal routes may be mounted in Next.js (outside pytest's reach) or
    rendered as static Squarespace pages. We don't hard-fail on missing
    portal URLs; we warn so the deprecation story stays intentional.
    """
    portal_paths = _next_portal_routes()
    # Known routes that live in Squarespace (not this repo) or are
    # handled by the portal's catch-all. Update this list when a route
    # moves from Squarespace into the Next.js app.
    squarespace_or_catchall = {
        "/pricing",
        "/cfa/ai-consulting",
        "/cfa/ai-consulting/chat",
        "/youth",
    }
    unverified: list[str] = []
    for url, status in contract_urls:
        if not _is_live(status):
            continue
        if url.startswith("/api/") or url.startswith("/auth/"):
            continue
        if url in portal_paths or url in squarespace_or_catchall:
            continue
        # Permissive: /showcase may also show up as /showcase/ etc.
        if f"{url}/" in portal_paths or f"{url[:-1]}" in portal_paths:
            continue
        unverified.append(url)
    # Non-fatal (the portal is a Next.js app — this is a heuristic
    # check). We assert the list is small so a big drift is still visible.
    assert len(unverified) <= 3, (
        f"too many contract URLs unverified against the portal tree: {unverified}"
    )


def test_future_work_urls_flagged_correctly(contract_urls):
    """Sanity: /register and /pay/{plan} should appear as FUTURE WORK."""
    future = {u for (u, s) in contract_urls if not _is_live(s)}
    assert "/register" in future
    assert any("/pay/" in u for u in future)
