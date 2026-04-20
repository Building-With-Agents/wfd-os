"""Send a request with a specific Host header and assert the resolved
X-Tenant-Id comes back in the response header (#16).
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import build_parser, fail, ok, resolve_base_url  # noqa: E402


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.add_argument("host", help="Host header value, e.g. platform.thewaifinder.com")
    parser.add_argument(
        "expected_tenant",
        help="Expected tenant_id the Host should resolve to, e.g. waifinder-flagship",
    )
    args = parser.parse_args()

    base = resolve_base_url(args, "http://localhost:8001")
    url = f"{base}/api/health"

    try:
        resp = httpx.get(url, headers={"Host": args.host}, timeout=10)
    except httpx.RequestError as e:
        fail(f"could not reach {url}: {e}")

    tenant = resp.headers.get("X-Tenant-Id") or resp.headers.get("x-tenant-id")
    if tenant != args.expected_tenant:
        fail(
            f"Host {args.host} -> expected {args.expected_tenant}, got {tenant!r}"
        )

    ok(f"Host {args.host} -> X-Tenant-Id: {tenant}")


if __name__ == "__main__":
    main()
