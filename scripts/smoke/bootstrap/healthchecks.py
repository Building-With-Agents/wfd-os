"""Hit /api/health on every wfd-os service port and confirm the
response shape. Catches a service that failed to boot.

Ports match the Procfile layout:
    8000 reporting-api
    8001 student-api
    8002 showcase-api
    8003 consulting-api
    8004 college-api
    8007 wji-api
    8008 marketing-api
    8009 assistant-api
    8010 apollo-api
    8012 laborpulse-api
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import build_parser, fail, ok  # noqa: E402


SERVICES = [
    ("reporting", 8000),
    ("student", 8001),
    ("showcase", 8002),
    ("consulting", 8003),
    ("college", 8004),
    ("wji", 8007),
    ("marketing", 8008),
    ("assistant", 8009),
    ("apollo", 8010),
    ("laborpulse", 8012),
]


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.add_argument(
        "--host",
        default="localhost",
        help="Host to hit (localhost for dev; the VM for prod smoke).",
    )
    parser.add_argument(
        "--only",
        default=None,
        help="Comma-separated service names to check (default: all).",
    )
    args = parser.parse_args()

    only = {s.strip() for s in args.only.split(",")} if args.only else None
    failures: list[tuple[str, int, str]] = []
    passes = 0

    with httpx.Client(timeout=5, follow_redirects=False) as client:
        for name, port in SERVICES:
            if only is not None and name not in only:
                continue
            url = f"http://{args.host}:{port}/api/health"
            try:
                resp = client.get(url)
                if resp.status_code != 200:
                    failures.append((name, port, f"status {resp.status_code}"))
                    print(f"  {name:<12} :{port}  FAIL ({resp.status_code})")
                    continue
                body = resp.json()
                if body.get("status") != "ok":
                    failures.append((name, port, f"status != ok: {body}"))
                    print(f"  {name:<12} :{port}  FAIL (body)")
                    continue
                passes += 1
                print(f"  {name:<12} :{port}  OK")
            except httpx.RequestError as e:
                failures.append((name, port, type(e).__name__))
                print(f"  {name:<12} :{port}  FAIL ({type(e).__name__})")

    if failures:
        fail(f"{len(failures)} service(s) unhealthy: {failures}")
    ok(f"every /api/health responded (n={passes})")


if __name__ == "__main__":
    main()
