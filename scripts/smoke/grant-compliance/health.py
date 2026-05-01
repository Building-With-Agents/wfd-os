"""grant-compliance API liveness — /health on :8014.

Confirms the grant-compliance scaffold (separate src/ package) boots
cleanly with its own pyproject. If this fails, check that
`pip install -e agents/grant-compliance` was run after the last
dependency change.

Usage:
    python scripts/smoke/grant-compliance/health.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import build_parser, fail, ok, resolve_base_url  # noqa: E402


def main() -> None:
    parser = build_parser(__doc__ or "")
    args = parser.parse_args()
    base = resolve_base_url(args, "http://localhost:8014")

    try:
        resp = httpx.get(f"{base}/health", timeout=5)
    except httpx.RequestError as e:
        fail(f"grant-compliance /health unreachable at {base}", body=type(e).__name__)
        return

    if resp.status_code != 200:
        fail(f"grant-compliance /health returned {resp.status_code}", body=resp.text)

    ok(f"grant-compliance /health responded ({resp.status_code})")


if __name__ == "__main__":
    main()
