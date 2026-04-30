"""GET /api/health on the LaborPulse service. Confirms the port is up
and reports whether JIE is configured (false = mock mode).
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
    url = f"{base}/api/health"

    try:
        resp = httpx.get(url, timeout=10)
    except httpx.RequestError as e:
        fail(f"could not reach {url}: {e}")

    if resp.status_code != 200:
        fail(f"expected 200, got {resp.status_code}", body=resp.text)

    body = resp.json()
    if body.get("status") != "ok" or body.get("service") != "laborpulse":
        fail("expected {status: ok, service: laborpulse}", body=body)

    ok(f"laborpulse /api/health -> jie_configured={body.get('jie_configured')}")


if __name__ == "__main__":
    main()
