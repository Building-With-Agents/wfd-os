"""GET a nonexistent student; expect a 404 envelope with
error.code=not_found + request_id header AND body.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import build_parser, fail, ok, resolve_base_url  # noqa: E402


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.add_argument(
        "--request-id",
        default=f"smoke-notfound-{int(time.time())}",
        help="X-Request-Id header value to assert round-trip on.",
    )
    args = parser.parse_args()

    base = resolve_base_url(args, "http://localhost:8001")
    url = f"{base}/api/student/does-not-exist/profile"

    try:
        resp = httpx.get(
            url,
            headers={"X-Request-Id": args.request_id},
            timeout=10,
        )
    except httpx.RequestError as e:
        fail(f"could not reach {url}: {e}")

    if resp.status_code != 404:
        fail(f"expected 404, got {resp.status_code}", body=resp.text)

    header_id = resp.headers.get("X-Request-Id") or resp.headers.get("x-request-id")
    if header_id != args.request_id:
        fail(
            f"X-Request-Id not echoed in response headers (got: {header_id!r})",
        )

    body = resp.json()
    err = body.get("error") or {}
    if err.get("code") != "not_found":
        fail("error.code != not_found", body=body)

    ok(f"not-found envelope + X-Request-Id header ({args.request_id}) + body")


if __name__ == "__main__":
    main()
