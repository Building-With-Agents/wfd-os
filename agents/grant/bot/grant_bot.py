"""Grant Bot — Teams interface for the Grant Agent.

Minimal stub so agents/grant/api.py imports resolve.
TODO: wire to actual grant Q&A / WJI reconciliation logic.
"""
from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import Activity, ActivityTypes

HELP_TEXT = """**CFA Grant Bot**

I can help with grant reporting and WJI reconciliation.

**Try asking:**
- *What is the current budget status?*
- *Show me last month's transactions.*
- *Are there any anomalies?*
- *Give me a WJI summary.*

**Commands:**
- **/help** — show this message
- **/summary** — full WJI snapshot
"""


class GrantBot(ActivityHandler):
    async def on_message_activity(self, turn_context: TurnContext):
        message = (turn_context.activity.text or "").strip()
        if not message:
            return

        await turn_context.send_activity(Activity(type=ActivityTypes.typing))

        try:
            if message.lower() in ["/help", "help"]:
                await turn_context.send_activity(MessageFactory.text(HELP_TEXT))
                return

            if message.lower() in ["/summary", "wji summary", "grant summary"]:
                # TODO: integrate with actual reconciliation engine
                await turn_context.send_activity(
                    MessageFactory.text(
                        "📊 **Grant Summary**\n\n"
                        "WJI reconciliation is running.\n"
                        "Connect to the actual data pipeline for live results."
                    )
                )
                return

            await turn_context.send_activity(
                MessageFactory.text(
                    f"You said: {message}\n\n"
                    "I'm still learning. Try **/help** or **/summary**."
                )
            )
        except Exception as e:
            await turn_context.send_activity(
                MessageFactory.text(f"Sorry, I encountered an error: {str(e)}")
            )

    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(
                    MessageFactory.text(
                        "👋 Hi! I'm the **CFA Grant Bot**.\n\n"
                        "I help with grant reporting and WJI reconciliation.\n\n"
                        "Try: *What is the current budget status?*\n\n"
                        "Type **/help** for more examples."
                    )
                )
