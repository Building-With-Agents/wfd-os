"""Recruiting API liveness — /health on :8012.

Confirms agents/job_board boots cleanly. Service mounts at the root
(/health, /jobs, /students, /applications) — the portal-side
/api/recruiting/* prefix is stripped by next.config.mjs and nginx.

Usage:
    python scripts/smoke/recruiting/health.py
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
    base = resolve_base_url(args, "http://localhost:8012")

    try:
        resp = httpx.get(f"{base}/health", timeout=5)
    except httpx.RequestError as e:
        fail(f"recruiting /health unreachable at {base}", body=type(e).__name__)
        return

    if resp.status_code != 200:
        fail(f"recruiting /health returned {resp.status_code}", body=resp.text)
    body = resp.json()
    if not (body.get("ok") is True or body.get("status") == "ok"):
        fail("recruiting /health body unhealthy", body=body)
    ok("recruiting /health responded healthy")


if __name__ == "__main__":
    main()
