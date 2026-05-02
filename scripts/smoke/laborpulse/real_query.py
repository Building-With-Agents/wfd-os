"""Fire a real query against LaborPulse with JIE wired up (JIE_BASE_URL must
be set in .env AND JIE FastAPI must be running on that URL). Asserts:

    - status 200
    - JSON body with conversation_id NOT starting "mock-"
    - confidence != "mock"
    - answer does NOT contain "[MOCK]"
    - evidence has >= 1 item
    - follow_up_questions has >= 1 item
    - wall-clock between 1s (something happened) and 60s (didn't time out)

Auth: uses the dev-mode test-headers bypass in `wfdos_common.auth.middleware`
(SessionMiddleware lines 58-84). Pass any role from the LaborPulse allow-list
(`workforce-development`, `staff`, `admin`); default is `workforce-development`.
No session cookie required.

Prints the conversation_id on the last line of stdout so you can pipe
it into feedback.py for follow-up flow testing.

Usage:

    python scripts/smoke/laborpulse/real_query.py
    python scripts/smoke/laborpulse/real_query.py --question "Show all El Paso DevOps postings"
    python scripts/smoke/laborpulse/real_query.py --role admin --user-id gary

Failure modes:

    - "could not reach ..." — wfd-os laborpulse-api is down (Step 6).
    - 503 with upstream=jie — JIE FastAPI is not running on JIE_BASE_URL (Step 8).
    - confidence == "mock" — JIE_BASE_URL is empty in .env; you're in mock mode (Step 5).
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
    parser.add_argument(
        "--question",
        default="How has the data analyst role changed in the Borderplex over the last year?",
        help="The question to send. Default is the canonical Borderplex demo prompt.",
    )
    parser.add_argument(
        "--role",
        default="workforce-development",
        choices=("workforce-development", "staff", "admin"),
        help="Test-user role for the @llm_gated bypass (must be in LaborPulse allow-list).",
    )
    parser.add_argument(
        "--user-id",
        default="smoke",
        help="Test-user id (becomes <user-id>@example.com via the auth middleware).",
    )
    parser.add_argument(
        "--host",
        default="talent.borderplexwfs.org",
        help="Host header so TenantResolutionMiddleware picks the Borderplex tenant.",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=60,
        help="HTTP timeout in seconds. Real-mode synthesis can take 3-15s; 60s is generous.",
    )
    args = parser.parse_args()

    base = resolve_base_url(args, "http://localhost:8012")
    url = f"{base}/api/laborpulse/query"

    headers = {
        "Host": args.host,
        # Dev-mode auth bypass — the middleware only honors these when no
        # cookie is present, and production proxies strip them.
        "x-test-user-role": args.role,
        "x-test-user-id": args.user_id,
    }

    start = time.monotonic()
    try:
        resp = httpx.post(
            url,
            json={"question": args.question},
            headers=headers,
            timeout=args.timeout,
        )
    except httpx.RequestError as e:
        fail(f"could not reach {url}: {e}")
    elapsed = time.monotonic() - start

    if resp.status_code != 200:
        # Surface the upstream marker if JIE itself was unreachable so the
        # caller can tell "wfd-os down" from "JIE down".
        fail(
            f"expected 200, got {resp.status_code}",
            body=resp.text,
        )

    body = resp.json()
    conv = body.get("conversation_id") or ""
    confidence = body.get("confidence")
    answer = body.get("answer") or ""
    evidence = body.get("evidence") or []
    followups = body.get("follow_up_questions") or []

    # Mock-mode discriminators — any one of these means JIE_BASE_URL is empty
    # and the laborpulse-api is serving canned content.
    if conv.startswith("mock-"):
        fail(
            f"conversation_id starts with 'mock-' ({conv!r}) — JIE_BASE_URL is "
            "empty in .env; you're in mock mode (Step 5).",
            body=body,
        )
    if confidence == "mock":
        fail(
            "confidence == 'mock' — JIE_BASE_URL is empty in .env; you're in "
            "mock mode (Step 5).",
            body=body,
        )
    if "[MOCK]" in answer:
        fail(
            "answer contains '[MOCK]' marker — JIE_BASE_URL is empty in .env; "
            "you're in mock mode (Step 5).",
            body=body,
        )

    # Real-mode shape assertions.
    if not answer.strip():
        fail("answer is empty", body=body)
    if len(evidence) < 1:
        fail("evidence list is empty — JIE returned no citations", body=body)
    if len(followups) < 1:
        fail("follow_up_questions is empty", body=body)

    # Latency sanity. Real-mode synthesis usually takes 3-15s; mock has a
    # hardcoded 8-12s delay. We don't gate on the upper bound (some hard
    # queries can run longer); we only confirm something actually happened.
    if elapsed < 0.5:
        fail(f"wall-clock {elapsed:.2f}s < 0.5s — response was suspiciously fast", body=body)

    print(f"OK: real query took {elapsed:.1f}s, conversation_id={conv}, "
          f"confidence={confidence!r}, evidence_count={len(evidence)}, "
          f"followups={len(followups)}")
    # Last line = conversation_id (so callers can pipe into feedback.py).
    print(conv)


if __name__ == "__main__":
    main()
