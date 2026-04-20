"""POST a malformed body to the consulting intake endpoint; expect a
structured 422 envelope with code=validation_error (#29).
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
        default=f"smoke-validation-{int(time.time())}",
        help="X-Request-Id header value to assert round-trip on.",
    )
    args = parser.parse_args()

    base = resolve_base_url(args, "http://localhost:8003")
    url = f"{base}/api/consulting/inquire"

    try:
        resp = httpx.post(
            url,
            json={},
            headers={"X-Request-Id": args.request_id},
            timeout=10,
        )
    except httpx.RequestError as e:
        fail(f"could not reach {url}: {e}")

    if resp.status_code != 422:
        fail(f"expected 422, got {resp.status_code}", body=resp.text)

    body = resp.json()
    err = body.get("error") or {}
    if err.get("code") != "validation_error":
        fail("error.code != validation_error", body=body)
    if (err.get("details") or {}).get("request_id") != args.request_id:
        fail(
            "X-Request-Id not echoed into error.details.request_id",
            body=body,
        )

    ok(f"validation envelope with request_id echo (X-Request-Id={args.request_id})")


if __name__ == "__main__":
    main()
