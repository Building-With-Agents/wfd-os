"""Cockpit API liveness — /health on :8013.

Public route (no auth). Confirms the service booted and the
DataSource (default = ExcelDataSource over the K8341 fixtures) loaded
without raising. If this fails, /cockpit/* won't work either; check
the cockpit-api log for an Excel-parse traceback.

Usage:
    python scripts/smoke/cockpit/health.py
    python scripts/smoke/cockpit/health.py --base-url http://prod-host
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
    base = resolve_base_url(args, "http://localhost:8013")

    try:
        resp = httpx.get(f"{base}/health", timeout=5)
    except httpx.RequestError as e:
        fail(f"cockpit /health unreachable at {base}", body=type(e).__name__)
        return

    if resp.status_code != 200:
        fail(f"cockpit /health returned {resp.status_code}", body=resp.text)
    body = resp.json()
    if body.get("ok") is not True or body.get("service") != "cockpit_api":
        fail("cockpit /health body unexpected", body=body)
    ok(f"cockpit /health responded with {body.get('version')}")


if __name__ == "__main__":
    main()
