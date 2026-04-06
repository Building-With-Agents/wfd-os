"""Apollo webhook handler — Phase 1 entry point.

Receives POST from Apollo when a lead moves to "Ready to Scope".
Validates the payload, then kicks off the pre-call pipeline.
"""

import asyncio
import traceback
from aiohttp import web

from agents.scoping.models import ScopingRequest
from agents.scoping.pipeline import run_precall_pipeline


async def handle_scoping_trigger(req: web.Request) -> web.Response:
    """POST /api/scoping-trigger — Apollo webhook endpoint."""

    # Validate content type
    if req.content_type != "application/json":
        return web.json_response(
            {"error": "Content-Type must be application/json"}, status=415
        )

    # Parse payload
    try:
        payload = await req.json()
    except Exception:
        return web.json_response({"error": "Invalid JSON"}, status=400)

    # Validate required fields
    contact = payload.get("contact", {})
    org = payload.get("organization", {})

    if not contact.get("first_name") or not contact.get("last_name"):
        return web.json_response(
            {"error": "Missing contact first_name or last_name"}, status=400
        )
    if not org.get("name"):
        return web.json_response(
            {"error": "Missing organization name"}, status=400
        )

    # Parse into model
    scoping_req = ScopingRequest.from_webhook(payload)

    print(f"[SCOPING] Webhook received for {scoping_req.organization.name}")
    print(f"  Contact: {scoping_req.contact.full_name} ({scoping_req.contact.title})")
    print(f"  Industry: {scoping_req.organization.industry}")
    print(f"  Notes: {scoping_req.notes[:100]}..." if len(scoping_req.notes) > 100 else f"  Notes: {scoping_req.notes}")

    # Acknowledge immediately, run pipeline in background
    asyncio.create_task(_run_pipeline_safe(scoping_req))

    return web.json_response({
        "status": "accepted",
        "message": f"Scoping initiated for {scoping_req.organization.name}",
        "company": scoping_req.organization.name,
        "contact": scoping_req.contact.full_name,
    })


async def _run_pipeline_safe(scoping_req: ScopingRequest) -> None:
    """Run the pre-call pipeline with error handling."""
    try:
        await run_precall_pipeline(scoping_req)
    except Exception as e:
        print(f"[SCOPING][ERROR] Pipeline failed for {scoping_req.organization.name}: {e}")
        traceback.print_exc()
        # TODO: Post error alert to Teams scoping channel
