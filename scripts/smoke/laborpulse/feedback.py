"""POST a thumbs-up or thumbs-down to LaborPulse feedback. The
conversation_id must come from a prior /query call (mock or real).
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import build_parser, fail, ok, resolve_base_url  # noqa: E402


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.add_argument("cookie", help="wfdos_session cookie value")
    parser.add_argument("conversation_id", help="From a prior /query call")
    parser.add_argument(
        "rating",
        nargs="?",
        default="1",
        choices=["1", "-1"],
        help="+1 for thumbs-up, -1 for thumbs-down",
    )
    parser.add_argument(
        "--question",
        default="smoke-test question",
        help="Question to attach to the feedback row.",
    )
    args = parser.parse_args()

    base = resolve_base_url(args, "http://localhost:8012")
    url = f"{base}/api/laborpulse/feedback"
    rating = int(args.rating)

    try:
        resp = httpx.post(
            url,
            json={
                "conversation_id": args.conversation_id,
                "question": args.question,
                "rating": rating,
            },
            cookies={"wfdos_session": args.cookie},
            timeout=15,
        )
    except httpx.RequestError as e:
        fail(f"could not reach {url}: {e}")

    if resp.status_code != 200:
        fail(f"expected 200, got {resp.status_code}", body=resp.text)

    body = resp.json()
    if not body.get("ok") or not isinstance(body.get("id"), int):
        fail("feedback response missing {ok: true, id: <int>}", body=body)

    ok(f"qa_feedback row {body['id']} written (rating={rating})")


if __name__ == "__main__":
    main()
