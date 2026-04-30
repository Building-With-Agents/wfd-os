"""Walk the stable URLs from docs/public-url-contract.md (#31) and
assert every one responds with an acceptable status.

Accepted: 200 / 301 / 302 / 307 / 308 / 401 / 405. Anything else means
a contract URL regressed.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import build_parser, fail, ok, resolve_base_url  # noqa: E402

PATHS = [
    "/",
    "/careers",
    "/showcase",
    "/for-employers",
    "/college",
    "/youth",
    "/pricing",
    "/cfa/ai-consulting",
    "/cfa/ai-consulting/chat",
    "/laborpulse",
    "/auth/login",
    "/auth/me",
    "/api/health",
]

ACCEPT = {200, 301, 302, 307, 308, 401, 405}


def main() -> None:
    parser = build_parser(__doc__ or "")
    args = parser.parse_args()
    base = resolve_base_url(args, "https://platform.thewaifinder.com")

    failures: list[tuple[str, int | str]] = []
    with httpx.Client(timeout=15, follow_redirects=False) as client:
        for path in PATHS:
            url = f"{base.rstrip('/')}{path}"
            try:
                resp = client.get(url)
                code = resp.status_code
            except httpx.RequestError as e:
                code = f"error: {type(e).__name__}"
            marker = "OK" if isinstance(code, int) and code in ACCEPT else "FAIL"
            print(f"  {path:<35} {code}  {marker}")
            if marker == "FAIL":
                failures.append((path, code))

    if failures:
        fail(f"{len(failures)} contract URL(s) returned unacceptable status: {failures}")
    ok(f"every contract URL on {base} responds")


if __name__ == "__main__":
    main()
