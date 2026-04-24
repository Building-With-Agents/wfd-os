"""JIE HTTP client — returns LaborPulse's assembled response dict.

`POST /analytics/query` on the job-intelligence-engine repo returns a
JSON body matching the `QueryResponse` shape documented in
`docs/laborpulse-backend-handoff.md` Part 2:

    {
      "conversation_id": str,
      "answer": str,
      "evidence": list[dict],
      "confidence": str | None,
      "follow_up_questions": list[str],
      "cost_usd": float | None,
      "sql_generated": str | None,
    }

This module posts the question + required headers and returns the
parsed JSON dict. The pre-refactor version folded SSE events into the
same dict shape; the JIE team now emits the final JSON directly per
the wfd-os-side "treat SSE as if it never existed" convention.
"""

from __future__ import annotations

from typing import Any, Optional

import httpx
from wfdos_common.errors import ServiceUnavailableError, ValidationFailure
from wfdos_common.logging import get_logger

log = get_logger(__name__)


async def query(
    *,
    base_url: str,
    question: str,
    tenant_id: str,
    user_email: str,
    request_id: Optional[str] = None,
    api_key: str = "",
    timeout_seconds: float = 300.0,
    conversation_id: Optional[str] = None,
) -> dict[str, Any]:
    """Post `question` to JIE, return the parsed JSON response.

    Raises `ServiceUnavailableError` (details.upstream='jie') on connection
    or timeout failures and on JIE 5xx responses; `ValidationFailure` on
    JIE 4xx responses. Both exceptions flow through the #29 envelope
    handler so callers see the standard error shape.
    """
    if not base_url:
        raise ServiceUnavailableError(
            "LaborPulse is not configured on this host",
            details={"upstream": "jie", "reason": "jie.base_url is empty"},
        )

    url = base_url.rstrip("/") + "/analytics/query"
    payload: dict[str, Any] = {"question": question}
    if conversation_id:
        payload["conversation_id"] = conversation_id

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Tenant-Id": tenant_id,
        "X-User-Email": user_email,
    }
    if request_id:
        headers["X-Request-Id"] = request_id
    if api_key:
        headers["X-API-Key"] = api_key

    # Per-stage timeouts — connect is snappy, read is generous (JIE
    # synthesis can take 15-45s), write is short (just the question JSON).
    timeout = httpx.Timeout(
        connect=10.0,
        read=timeout_seconds,
        write=30.0,
        pool=30.0,
    )

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            resp = await client.post(url, json=payload, headers=headers)
        except httpx.TimeoutException as e:
            log.error(
                "laborpulse.jie.timeout",
                tenant_id=tenant_id,
                exc_info=True,
            )
            raise ServiceUnavailableError(
                "JIE timed out",
                details={"upstream": "jie", "reason": "timeout"},
            ) from e
        except httpx.ConnectError as e:
            log.error(
                "laborpulse.jie.connect_error",
                tenant_id=tenant_id,
                exc_info=True,
            )
            raise ServiceUnavailableError(
                "JIE unreachable",
                details={"upstream": "jie", "reason": "connect_error"},
            ) from e

        if resp.status_code >= 500:
            log.error(
                "laborpulse.jie.5xx",
                status=resp.status_code,
                tenant_id=tenant_id,
            )
            raise ServiceUnavailableError(
                "JIE returned an upstream error",
                details={"upstream": "jie", "status": resp.status_code},
            )
        if resp.status_code >= 400:
            body_preview = (resp.text or "")[:200]
            log.warning(
                "laborpulse.jie.4xx",
                status=resp.status_code,
                tenant_id=tenant_id,
                body_preview=body_preview,
            )
            raise ValidationFailure(
                "JIE rejected the question",
                details={
                    "upstream": "jie",
                    "status": resp.status_code,
                    "body_preview": body_preview[:500],
                },
            )

        try:
            return resp.json()
        except ValueError as e:
            # JIE should always return JSON on 2xx; treat non-JSON as an
            # upstream failure so it surfaces as a 503 to the browser.
            log.error(
                "laborpulse.jie.bad_json",
                tenant_id=tenant_id,
                body_preview=(resp.text or "")[:200],
                exc_info=True,
            )
            raise ServiceUnavailableError(
                "JIE returned non-JSON response",
                details={"upstream": "jie", "reason": "invalid_json"},
            ) from e


__all__ = ["query"]
