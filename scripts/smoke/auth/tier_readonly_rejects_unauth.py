"""Anonymous request to a @read_only endpoint; expect 401 envelope (#25)."""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import build_parser, fail, ok, resolve_base_url  # noqa: E402


def main() -> None:
    parser = build_parser(__doc__ or "")
    args = parser.parse_args()

    base = resolve_base_url(args, "http://localhost:8001")
    url = f"{base}/api/student/me"

    try:
        resp = httpx.get(url, timeout=10)
    except httpx.RequestError as e:
        fail(f"could not reach {url}: {e}")

    if resp.status_code != 401:
        fail(
            f"expected 401 on unauth @read_only, got {resp.status_code}",
            body=resp.text,
        )

    ok("read_only tier rejects unauth")


if __name__ == "__main__":
    main()
