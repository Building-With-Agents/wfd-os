"""
Market Intelligence Bot — Teams interface for the Market Intelligence Agent.
"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from botbuilder.core import ActivityHandler, TurnContext, MessageFactory
from botbuilder.schema import Activity, ActivityTypes
from agent import run_agent

HELP_TEXT = """**Waifinder — Market Intelligence Agent**

I answer labor market questions using real Lightcast job posting data (Q3 2024).

**Try asking:**
- *What are the top skills employers are asking for right now?*
- *Which skills have the biggest shortage — high demand, low supply?*
- *Which skills are growing fastest in the market?*
- *What does a network administrator earn in Washington?*
- *Which companies are posting the most tech jobs?*
- *Show me QA tester job postings and the skills they require*
- *A student knows Python, SQL and Excel — how do they match the market?*
- *Give me a full market overview*

**Commands:**
- **/help** — show this message
- **/summary** — full market snapshot

Data source: Lightcast Q3 2024 | Region: Washington state
"""


class MarketBot(ActivityHandler):

    async def on_message_activity(self, turn_context: TurnContext):
        message = (turn_context.activity.text or "").strip()
        if not message:
            return

        # Send typing indicator
        await turn_context.send_activity(Activity(type=ActivityTypes.typing))

        try:
            if message.lower() in ["/help", "help"]:
                await turn_context.send_activity(MessageFactory.text(HELP_TEXT))
                return

            if message.lower() in ["/summary", "market summary", "market overview"]:
                message = "Give me a full market overview including total postings, top skills, top employers, and median wage."

            # Route everything through the Market Intelligence Agent
            response = run_agent(message)
            await turn_context.send_activity(MessageFactory.text(response))

        except Exception as e:
            await turn_context.send_activity(
                MessageFactory.text(f"Sorry, I encountered an error: {str(e)}")
            )

    async def on_members_added_activity(self, members_added, turn_context: TurnContext):
        for member in members_added:
            if member.id != turn_context.activity.recipient.id:
                await turn_context.send_activity(MessageFactory.text(
                    "👋 Hi! I'm the **Waifinder Market Intelligence Agent**.\n\n"
                    "I can answer real labor market questions using Lightcast job posting data.\n\n"
                    "Try: *What are the top skills employers are asking for?*\n\n"
                    "Type **/help** for more examples."
                ))
