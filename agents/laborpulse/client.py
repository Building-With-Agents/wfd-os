"""JIE streaming client — isolates the httpx SSE plumbing so api.py stays
focused on FastAPI wiring and so tests can swap in an async generator
without mocking httpx itself.

The contract is intentionally minimal:

  stream_query(question, *, tenant_id, user_email, request_id) -> async
  iterator of bytes chunks in `text/event-stream` framing. wfd-os does
  not parse, transform, or re-frame the chunks — we pass JIE's wire
  format through unchanged so the frontend sees exactly what JIE
  produced. That keeps the two repos decoupled: JIE changes its
  `event:`/`data:` schema, wfd-os doesn't care.
"""

from __future__ import annotations

from typing import AsyncIterator, Optional

import httpx

from wfdos_common.errors import ServiceUnavailableError
from wfdos_common.logging import get_logger

log = get_logger(__name__)


async def stream_query(
    *,
    base_url: str,
    question: str,
    tenant_id: str,
    user_email: str,
    request_id: Optional[str] = None,
    api_key: str = "",
    timeout_seconds: float = 300.0,
    conversation_id: Optional[str] = None,
) -> AsyncIterator[bytes]:
    """Async iterator over JIE's SSE body.

    Raises `ServiceUnavailableError` with `details.upstream = "jie"` on
    connection/timeout failures so the upstream envelope handler turns
    it into a 503 envelope — matches the stripped-.env 503 story from
    the @llm_gated tier decorator (#25).
    """
    if not base_url:
        raise ServiceUnavailableError(
            "LaborPulse is not configured on this host",
            details={"upstream": "jie", "reason": "jie.base_url is empty"},
        )

    url = base_url.rstrip("/") + "/analytics/query"
    payload = {"question": question}
    if conversation_id:
        payload["conversation_id"] = conversation_id

    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "X-Tenant-Id": tenant_id,
        "X-User-Email": user_email,
    }
    if request_id:
        headers["X-Request-Id"] = request_id
    if api_key:
        headers["X-API-Key"] = api_key

    timeout = httpx.Timeout(connect=10.0, read=timeout_seconds, write=30.0, pool=30.0)

    async with httpx.AsyncClient(timeout=timeout) as client:
        try:
            async with client.stream(
                "POST", url, json=payload, headers=headers
            ) as resp:
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
                    # 4xx from JIE — most likely a malformed question or
                    # tenant-scoping rejection. Surface as validation
                    # (422) rather than 503 so the client knows to
                    # adjust, not to retry.
                    body = await resp.aread()
                    log.warning(
                        "laborpulse.jie.4xx",
                        status=resp.status_code,
                        tenant_id=tenant_id,
                        body_preview=body[:200].decode(errors="replace"),
                    )
                    from wfdos_common.errors import ValidationFailure

                    raise ValidationFailure(
                        "JIE rejected the question",
                        details={
                            "upstream": "jie",
                            "status": resp.status_code,
                            "body_preview": body[:500].decode(errors="replace"),
                        },
                    )
                async for chunk in resp.aiter_bytes():
                    yield chunk
        except httpx.TimeoutException as e:
            log.error("laborpulse.jie.timeout", tenant_id=tenant_id, exc_info=True)
            raise ServiceUnavailableError(
                "JIE timed out",
                details={"upstream": "jie", "reason": "timeout"},
            ) from e
        except httpx.ConnectError as e:
            log.error("laborpulse.jie.connect_error", tenant_id=tenant_id, exc_info=True)
            raise ServiceUnavailableError(
                "JIE unreachable",
                details={"upstream": "jie", "reason": "connect_error"},
            ) from e


__all__ = ["stream_query"]
