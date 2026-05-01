"""Assistant API agent registry — confirms the new agents are reachable.

The bd-command-center / finance-cockpit reconciliation added three
agents to agents/assistant/api.py: bd_agent, marketing_agent, and
finance_agent. The /api/assistant/agents endpoint enumerates the
registered agents — a regression that drops one of these from the
registry would break the corresponding /internal/<name> portal page.

Usage:
    python scripts/smoke/assistant/agent_registry.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import build_parser, fail, ok, resolve_base_url  # noqa: E402


REQUIRED_AGENTS = {
    # Original six.
    "student",
    "employer",
    "college",
    "consulting",
    "youth",
    "staff",
    # Reconciliation additions.
    "bd",
    "marketing",
    "finance",
}


def main() -> None:
    parser = build_parser(__doc__ or "")
    args = parser.parse_args()
    base = resolve_base_url(args, "http://localhost:8009")

    try:
        resp = httpx.get(f"{base}/api/assistant/agents", timeout=5)
    except httpx.RequestError as e:
        fail(f"assistant /api/assistant/agents unreachable at {base}", body=type(e).__name__)
        return

    if resp.status_code != 200:
        fail(f"agent registry returned {resp.status_code}", body=resp.text)

    body = resp.json()
    # Tolerate either {"agents": [...]} or a bare list — the assistant
    # API has wavered between both shapes during the reconciliation.
    raw = body.get("agents", body) if isinstance(body, dict) else body
    if not isinstance(raw, list):
        fail("agent registry response shape unexpected", body=body)

    registered = {entry.get("type") if isinstance(entry, dict) else entry for entry in raw}
    missing = REQUIRED_AGENTS - registered
    if missing:
        fail(f"missing agents in registry: {sorted(missing)}", body=body)

    ok(f"every required agent present in registry (n={len(REQUIRED_AGENTS)})")


if __name__ == "__main__":
    main()
