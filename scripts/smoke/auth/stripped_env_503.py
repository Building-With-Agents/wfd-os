"""Verify that an @llm_gated endpoint returns 503 when no LLM provider
is configured. Prerequisite: services were started with
AZURE_OPENAI_KEY, ANTHROPIC_API_KEY, and GEMINI_API_KEY all empty.
"""

from __future__ import annotations

import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from _common import build_parser, fail, ok, resolve_base_url  # noqa: E402


def main() -> None:
    parser = build_parser(__doc__ or "")
    parser.add_argument("cookie", help="Value of wfdos_session cookie")
    args = parser.parse_args()

    base = resolve_base_url(args, "http://localhost:8009")
    url = f"{base}/api/assistant/chat"

    try:
        resp = httpx.post(
            url,
            json={"agent_type": "consulting", "message": "hi"},
            cookies={"wfdos_session": args.cookie},
            timeout=15,
        )
    except httpx.RequestError as e:
        fail(f"could not reach {url}: {e}")

    if resp.status_code != 503:
        fail(f"expected 503, got {resp.status_code}", body=resp.text)

    body = resp.json()
    err = body.get("error") or {}
    if err.get("code") != "service_unavailable":
        fail("error.code != service_unavailable", body=body)
    if (err.get("details") or {}).get("tier") != "llm_gated":
        fail("error.details.tier != llm_gated", body=body)

    ok("llm_gated returns 503 with tier=llm_gated when stripped")


if __name__ == "__main__":
    main()
