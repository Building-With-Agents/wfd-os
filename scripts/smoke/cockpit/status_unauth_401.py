"""Cockpit API auth gate — /cockpit/status MUST 401 without a session.

Catches a regression where the @read_only tier decorator gets removed
or SessionMiddleware is reordered. The pre-reconciliation cockpit
served this endpoint without any auth — confirming the gate stays in
place is the most important per-PR check on this service.

Usage:
    python scripts/smoke/cockpit/status_unauth_401.py
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
        resp = httpx.get(f"{base}/cockpit/status", timeout=5)
    except httpx.RequestError as e:
        fail(f"cockpit /cockpit/status unreachable at {base}", body=type(e).__name__)
        return

    if resp.status_code != 401:
        fail(
            f"expected 401, got {resp.status_code} — auth gate may have regressed",
            body=resp.text,
        )

    # Envelope shape from wfdos_common.errors — confirm the structured
    # error body so a caller can rely on error.code.
    body = resp.json()
    if body.get("error", {}).get("code") != "unauthorized":
        fail("envelope shape unexpected for 401 response", body=body)

    ok("cockpit /cockpit/status correctly 401s with structured envelope when unauthenticated")


if __name__ == "__main__":
    main()
