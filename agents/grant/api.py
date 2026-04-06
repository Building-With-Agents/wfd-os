import os
import sys
from aiohttp import web

# Fix Windows console encoding so Unicode in HTTP libs doesn't crash the process
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter, TurnContext
from botbuilder.schema import Activity
from bot.grant_bot import GrantBot
from database.db import init_db
from dotenv import load_dotenv

load_dotenv(override=True)

# Bot adapter
settings = BotFrameworkAdapterSettings(
    app_id=os.getenv("MICROSOFT_APP_ID"),
    app_password=os.getenv("MICROSOFT_APP_PASSWORD"),
    channel_auth_tenant=os.getenv("MICROSOFT_APP_TENANT_ID"),
)
adapter = BotFrameworkAdapter(settings)
bot = GrantBot()


async def on_error(context: TurnContext, error: Exception):
    print(f"[ERROR] {error}")
    await context.send_activity("An unexpected error occurred. Please try again.")

adapter.on_turn_error = on_error


async def messages(req: web.Request) -> web.Response:
    if req.content_type != "application/json":
        return web.Response(status=415)
    body = await req.json()
    activity = Activity().deserialize(body)
    auth_header = req.headers.get("Authorization", "")
    try:
        await adapter.process_activity(activity, auth_header, bot.on_turn)
        return web.Response(status=200)
    except Exception as e:
        print(f"Error processing activity: {e}")
        return web.Response(status=500)


async def health(req: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "bot": "CFA-Grant-Bot"})


app = web.Application()
app.router.add_post("/api/messages", messages)
app.router.add_get("/health", health)


if __name__ == "__main__":
    init_db()
    port = int(os.getenv("PORT", 3978))
    print(f"CFA Grant Bot running on port {port}")
    print(f"Messaging endpoint: http://localhost:{port}/api/messages")
    web.run_app(app, host="0.0.0.0", port=port)
