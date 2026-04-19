"""Fire a query against LaborPulse in mock mode (JIE_BASE_URL must be
empty in .env). Asserts:

    - status 200
    - JSON body with conversation_id starting "mock-"
    - confidence == "mock"
    - answer contains "[MOCK]"
    - evidence has >= 1 item
    - follow_up_questions has >= 1 item
    - wall-clock wait is 8-14 seconds (8-12s target + slack)

Prints the conversation_id on the last line of stdout so you can pipe
it into feedback.py.
"""

from __future__ import annotations

import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import build_parser, fail, resolve_base_url  # noqa: E402


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.add_argument("cookie", help="wfdos_session cookie value")
    parser.add_argument(
        "question",
        nargs="?",
        default="which sectors gained the most postings in Doña Ana in Q1?",
    )
    parser.add_argument(
        "--host",
        default="talent.borderplexwfs.org",
        help="Host header so TenantResolutionMiddleware picks the right tenant.",
    )
    args = parser.parse_args()

    base = resolve_base_url(args, "http://localhost:8012")
    url = f"{base}/api/laborpulse/query"

    start = time.monotonic()
    try:
        resp = httpx.post(
            url,
            json={"question": args.question},
            cookies={"wfdos_session": args.cookie},
            headers={"Host": args.host},
            timeout=30,
        )
    except httpx.RequestError as e:
        fail(f"could not reach {url}: {e}")
    elapsed = time.monotonic() - start

    if resp.status_code != 200:
        fail(f"expected 200, got {resp.status_code}", body=resp.text)

    body = resp.json()
    conv = body.get("conversation_id") or ""
    confidence = body.get("confidence")
    answer = body.get("answer") or ""
    evidence = body.get("evidence") or []
    followups = body.get("follow_up_questions") or []

    if not conv.startswith("mock-"):
        fail(f"conversation_id doesn't start with 'mock-': {conv!r}", body=body)
    if confidence != "mock":
        fail(f"confidence != mock (got {confidence!r})", body=body)
    if "[MOCK]" not in answer:
        fail("answer missing [MOCK] marker", body=body)
    if len(evidence) < 1:
        fail("evidence list is empty", body=body)
    if len(followups) < 1:
        fail("follow_up_questions is empty", body=body)

    if elapsed < 7:
        fail(f"wall-clock {elapsed:.1f}s < 8s -- mock sleep not firing?")
    if elapsed > 14:
        fail(f"wall-clock {elapsed:.1f}s > 14s (allowing 2s slack)")

    print(f"OK: mock query took {elapsed:.1f}s, conversation_id={conv}")
    # Last line = conversation_id (so callers can pipe into feedback.py).
    print(conv)


if __name__ == "__main__":
    main()
