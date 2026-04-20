"""Smoke the JIE-unreachable path.

Prerequisite: the LaborPulse service was started with JIE_BASE_URL
pointing at an unreachable host (e.g. JIE_BASE_URL=http://127.0.0.1:1).
Expects a 503 envelope with error.details.upstream == "jie".
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import build_parser, fail, ok, resolve_base_url  # noqa: E402


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.add_argument("cookie", help="wfdos_session cookie value")
    args = parser.parse_args()

    base = resolve_base_url(args, "http://localhost:8012")
    url = f"{base}/api/laborpulse/query"

    try:
        resp = httpx.post(
            url,
            json={"question": "anything"},
            cookies={"wfdos_session": args.cookie},
            timeout=30,
        )
    except httpx.RequestError as e:
        fail(f"could not reach {url}: {e}")

    if resp.status_code != 503:
        fail(f"expected 503, got {resp.status_code}", body=resp.text)

    body = resp.json()
    err = body.get("error") or {}
    if err.get("code") != "service_unavailable":
        fail("error.code != service_unavailable", body=body)
    if (err.get("details") or {}).get("upstream") != "jie":
        fail("error.details.upstream != jie", body=body)

    ok("JIE-unreachable returns 503 envelope with upstream=jie")


if __name__ == "__main__":
    main()
