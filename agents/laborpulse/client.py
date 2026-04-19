"""JIE HTTP client — returns LaborPulse's assembled response dict.

`POST /analytics/query` on the job-intelligence-engine repo emits a
series of framed events (Intent → Route → SQL → Synthesize → Cite →
Follow-up). This module consumes the full response body, folds each
event into a single `QueryResponse`-shaped dict, and returns it to
the caller. The canonical shape:

    {
      "conversation_id": str,
      "answer": str,                      # concatenation of answer events
      "evidence": list[dict],
      "confidence": str | None,
      "follow_up_questions": list[str],
      "cost_usd": float | None,
      "sql_generated": str | None,
    }

Unknown event types are ignored. Malformed data payloads are tolerated
(JIE's plain-text answer chunks sometimes arrive without JSON wrapping;
those get concatenated into `answer` as-is).
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
    """Post `question` to JIE, consume the SSE body, return the assembled dict.

    Raises `ServiceUnavailableError` (details.upstream='jie') on connection
    or timeout failures; `ValidationFailure` on JIE 4xx responses. Both
    exceptions flow through the #29 envelope handler so callers see the
    standard error shape.
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
        "Accept": "text/event-stream",
        "X-Tenant-Id": tenant_id,
        "X-User-Email": user_email,
    }
    if request_id:
        headers["X-Request-Id"] = request_id
    if api_key:
        headers["X-API-Key"] = api_key

    # Per-stage timeouts — connect is snappy, read is generous (synthesis
    # can take 15-45s), write is short (just the question JSON).
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
                    body = await resp.aread()
                    log.warning(
                        "laborpulse.jie.4xx",
                        status=resp.status_code,
                        tenant_id=tenant_id,
                        body_preview=body[:200].decode(errors="replace"),
                    )
                    raise ValidationFailure(
                        "JIE rejected the question",
                        details={
                            "upstream": "jie",
                            "status": resp.status_code,
                            "body_preview": body[:500].decode(errors="replace"),
                        },
                    )

                assembled = _new_result()
                # Consume the SSE body as a text stream, frame-by-frame.
                buf = ""
                async for chunk in resp.aiter_text():
                    buf += chunk
                    # SSE frames end with a blank line.
                    while "\n\n" in buf:
                        frame, buf = buf.split("\n\n", 1)
                        _fold_frame_into(assembled, frame)
                # Handle any trailing frame without a terminating blank line.
                if buf.strip():
                    _fold_frame_into(assembled, buf)
                return assembled
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


# ---------------------------------------------------------------------------
# Frame parsing + folding
# ---------------------------------------------------------------------------


def _new_result() -> dict[str, Any]:
    return {
        "conversation_id": None,
        "answer": "",
        "evidence": [],
        "confidence": None,
        "follow_up_questions": [],
        "cost_usd": None,
        "sql_generated": None,
    }


def _fold_frame_into(acc: dict[str, Any], frame: str) -> None:
    """Parse one SSE frame and fold its payload into the accumulator."""
    event_name = "message"
    data_line = ""
    for line in frame.split("\n"):
        if line.startswith("event:"):
            event_name = line[6:].strip()
        elif line.startswith("data:"):
            data_line += line[5:].strip()

    if not data_line:
        return

    # JIE emits JSON-encoded data for most events, but answer chunks may
    # arrive as plain-text tokens. Fall back gracefully.
    import json

    payload: Any
    try:
        payload = json.loads(data_line)
    except (json.JSONDecodeError, ValueError):
        payload = {"text": data_line}

    _apply_event(acc, event_name, payload if isinstance(payload, dict) else {"text": str(payload)})


def _apply_event(acc: dict[str, Any], event_name: str, payload: dict[str, Any]) -> None:
    if event_name == "answer":
        text = payload.get("text") or payload.get("delta") or ""
        if text:
            acc["answer"] += text
    elif event_name == "evidence":
        # JIE can emit one evidence item per event or a list; normalize.
        items = payload.get("items")
        if isinstance(items, list):
            acc["evidence"].extend(items)
        else:
            acc["evidence"].append(payload)
    elif event_name == "confidence":
        level = payload.get("level") or payload.get("text")
        if level:
            acc["confidence"] = level
    elif event_name in ("followup", "follow_up"):
        q = payload.get("question")
        if q:
            acc["follow_up_questions"].append(q)
        qs = payload.get("questions")
        if isinstance(qs, list):
            acc["follow_up_questions"].extend(qs)
    elif event_name == "sql":
        sql = payload.get("sql") or payload.get("query") or payload.get("text")
        if sql:
            acc["sql_generated"] = sql
    elif event_name == "done":
        if payload.get("conversation_id"):
            acc["conversation_id"] = payload["conversation_id"]
        if isinstance(payload.get("cost_usd"), (int, float)):
            acc["cost_usd"] = float(payload["cost_usd"])
    # Unknown events are silently ignored — keeps wfd-os decoupled from
    # JIE's event vocabulary evolution.


__all__ = ["query"]
