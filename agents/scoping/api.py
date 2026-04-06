"""CFA Scoping Agent — main HTTP server.

Receives Apollo webhook when a lead moves to "Ready to Scope",
then orchestrates the full scoping pipeline.
"""

import sys
import os

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from aiohttp import web
from dotenv import load_dotenv

load_dotenv(override=True)

from agents.scoping.webhook import handle_scoping_trigger
from agents.scoping.postcall import handle_postcall_trigger


async def health(req: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "agent": "CFA-Scoping-Agent"})


app = web.Application()
app.router.add_post("/api/scoping-trigger", handle_scoping_trigger)
app.router.add_post("/api/postcall-trigger", handle_postcall_trigger)
app.router.add_get("/health", health)


if __name__ == "__main__":
    port = int(os.getenv("PORT", 7071))
    print(f"CFA Scoping Agent running on port {port}")
    print(f"Webhook endpoint: http://localhost:{port}/api/scoping-trigger")
    print(f"Post-call endpoint: http://localhost:{port}/api/postcall-trigger")
    print(f"Health check: http://localhost:{port}/health")
    web.run_app(app, host="0.0.0.0", port=port)
