"""GET /auth/me with a session cookie; expect {email, role, tenant_id}."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import build_parser, fail, ok, resolve_base_url  # noqa: E402


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.add_argument(
        "cookie",
        help="Value of the wfdos_session cookie (copy from browser devtools).",
    )
    args = parser.parse_args()

    base = resolve_base_url(args, "http://localhost:8003")
    url = f"{base}/auth/me"

    try:
        resp = httpx.get(
            url,
            cookies={"wfdos_session": args.cookie},
            timeout=10,
        )
    except httpx.RequestError as e:
        fail(f"could not reach {url}: {e}")

    if resp.status_code != 200:
        fail(f"expected 200, got {resp.status_code}", body=resp.text)

    body = resp.json()
    email = body.get("email")
    role = body.get("role")
    if not email or not role:
        fail("/auth/me didn't return {email, role}", body=body)

    ok(f"/auth/me -> {email} (role={role})")


if __name__ == "__main__":
    main()
