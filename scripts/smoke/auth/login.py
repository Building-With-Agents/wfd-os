"""Fire a magic-link request. DOES NOT verify email delivery — that's
a live-integration check Gary runs manually.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import build_parser, fail, ok, resolve_base_url  # noqa: E402


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.add_argument(
        "email", help="Email to request a magic link for."
    )
    args = parser.parse_args()

    base = resolve_base_url(args, "http://localhost:8003")
    url = f"{base}/auth/login"

    try:
        resp = httpx.post(url, json={"email": args.email}, timeout=15)
    except httpx.RequestError as e:
        fail(f"could not reach {url}: {e}")

    if resp.status_code != 200:
        fail(f"expected 200, got {resp.status_code}", body=resp.text)

    body = resp.json()
    if body.get("status") != "ok":
        fail("/auth/login didn't return {status: ok}", body=body)

    ok(f"/auth/login accepted {args.email} (check inbox for the magic link)")


if __name__ == "__main__":
    main()
