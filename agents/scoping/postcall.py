"""Post-call webhook handler — Phase 2 entry point.

Can be triggered manually or by a polling function that detects
when a scoping meeting has ended and the transcript is available.
"""

import asyncio
import traceback
from aiohttp import web

from wfdos_common.models.scoping import ScopingRequest
from agents.scoping.pipeline import run_postcall_pipeline


async def handle_postcall_trigger(req: web.Request) -> web.Response:
    """POST /api/postcall-trigger — manually trigger post-call processing.

    Expected payload:
    {
        "meeting_id": "<Teams meeting ID>",
        "contact": { ... },
        "organization": { ... },
        "notes": ""
    }
    """
    if req.content_type != "application/json":
        return web.json_response(
            {"error": "Content-Type must be application/json"}, status=415
        )

    try:
        payload = await req.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    meeting_id = payload.get("meeting_id")
    if not meeting_id:
        return web.json_response({"error": "Missing meeting_id"}, status=400)

    scoping_req = ScopingRequest.from_webhook(payload)

    print(f"[POSTCALL] Trigger received for {scoping_req.organization.name}, meeting {meeting_id}")

    asyncio.create_task(_run_postcall_safe(meeting_id, scoping_req))

    return web.json_response({
        "status": "accepted",
        "message": f"Post-call processing initiated for {scoping_req.organization.name}",
    })


async def _run_postcall_safe(meeting_id: str, scoping_req: ScopingRequest) -> None:
    try:
        await run_postcall_pipeline(meeting_id, scoping_req)
    except Exception as e:
        print(f"[POSTCALL][ERROR] Pipeline failed for {scoping_req.organization.name}: {e}")
        traceback.print_exc()
