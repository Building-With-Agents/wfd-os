"""
Waifinder — Market Intelligence Agent
Teams bot server — port 3979
"""
import os
import sys

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Add agent root to path
sys.path.insert(0, os.path.dirname(__file__))

from aiohttp import web
from botbuilder.core import BotFrameworkAdapterSettings, BotFrameworkAdapter, TurnContext
from botbuilder.schema import Activity
from bot.market_bot import MarketBot
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../.env"), override=True)

# Bot adapter
settings = BotFrameworkAdapterSettings(
    app_id=os.getenv("WAIFINDER_APP_ID"),
    app_password=os.getenv("WAIFINDER_APP_PASSWORD"),
    channel_auth_tenant=os.getenv("AZURE_TENANT_ID"),
)
adapter = BotFrameworkAdapter(settings)
bot = MarketBot()


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
        print(f"[ERROR] processing activity: {e}")
        return web.Response(status=500)


async def health(req: web.Request) -> web.Response:
    return web.json_response({"status": "ok", "bot": "Waifinder-MarketIntelligence"})


app = web.Application()
app.router.add_post("/api/messages", messages)
app.router.add_get("/health", health)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3979))
    print(f"Waifinder Market Intelligence Bot running on port {port}")
    print(f"Messaging endpoint: http://localhost:{port}/api/messages")
    web.run_app(app, host="0.0.0.0", port=port)
