"""Teams operations — channels, messages, meeting scheduling."""

from datetime import datetime, timedelta
from agents.scoping.models import ScopingRequest, ScopingAnalysis
from agents.graph.auth import get_graph_client, graph_post
from agents.graph import config

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


async def _post_channel_message(team_id: str, channel_id: str, message: str) -> None:
    """Post a message to a Teams channel via Incoming Webhook.

    Microsoft Graph does not support app-only channel message posting.
    Instead, we use an Incoming Webhook connector configured on the channel.
    Set SCOPING_WEBHOOK_URL in .env to the webhook URL from the channel connector.
    """
    import httpx

    webhook_url = config.get("SCOPING_WEBHOOK_URL")
    if not webhook_url:
        print(f"[TEAMS] No SCOPING_WEBHOOK_URL configured - printing message to console:")
        print(message)
        return

    # Power Automate webhook expects Adaptive Card format
    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": [
                        {
                            "type": "TextBlock",
                            "text": message,
                            "wrap": True,
                        }
                    ],
                },
            }
        ],
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post(webhook_url, json=payload)
        if resp.status_code in (200, 202):
            print(f"[TEAMS] Message posted via webhook")
        else:
            print(f"[TEAMS] Webhook post failed ({resp.status_code}): {resp.text[:200]}")


TYPE_BADGES = {
    "milestone": "\U0001f3af Milestone",
    "delivery": "\U0001f4e6 Deliverable",
    "deliverable": "\U0001f4e6 Deliverable",
    "announcement": "\U0001f4e2 Announcement",
    "progress": "\U0001f4c8 Progress",
    "kickoff": "\U0001f680 Kickoff",
    "note": "\U0001f4dd Note",
}


def post_engagement_update_to_teams(
    title: str,
    body: str,
    update_type: str = "progress",
    engagement_name: str = "",
    portal_url: str = "",
) -> dict:
    """Post an engagement update to the Teams channel via Power Automate webhook.

    Synchronous function — never raises. Returns {"ok": bool, "error": str | None}.
    """
    import httpx
    import os

    webhook_url = os.getenv("SCOPING_WEBHOOK_URL")
    if not webhook_url:
        print("[TEAMS] No SCOPING_WEBHOOK_URL — skipping Teams post")
        return {"ok": False, "error": "SCOPING_WEBHOOK_URL not set"}

    badge = TYPE_BADGES.get(update_type, "\U0001f4c8 Update")
    portal_link = portal_url or "http://localhost:3000/internal"

    card_body = [
        {"type": "TextBlock", "text": f"{badge}: {title}", "weight": "bolder", "size": "medium", "wrap": True},
    ]
    if engagement_name:
        card_body.append({"type": "TextBlock", "text": engagement_name, "isSubtle": True, "spacing": "none"})
    card_body.append({"type": "TextBlock", "text": body, "wrap": True, "spacing": "medium"})
    card_body.append({
        "type": "ActionSet",
        "actions": [{
            "type": "Action.OpenUrl",
            "title": "View in portal",
            "url": portal_link,
        }],
    })

    payload = {
        "type": "message",
        "attachments": [{
            "contentType": "application/vnd.microsoft.card.adaptive",
            "content": {
                "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                "type": "AdaptiveCard",
                "version": "1.4",
                "body": card_body,
            },
        }],
    }

    try:
        r = httpx.post(webhook_url, json=payload, timeout=15)
        if r.status_code in (200, 202):
            print(f"[TEAMS] Update posted: {badge} {title}")
            return {"ok": True, "error": None}
        else:
            print(f"[TEAMS] Post failed: HTTP {r.status_code} {r.text[:200]}")
            return {"ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        print(f"[TEAMS] Post exception: {type(e).__name__}: {e}")
        return {"ok": False, "error": str(e)}


async def create_client_channel(req: ScopingRequest) -> dict:
    """Create a Teams channel for the client engagement.

    Returns dict with channel_id and channel_name.
    """
    client = get_graph_client()
    team_id = config.CFA_TEAM_ID
    channel_name = f"{req.organization.name} - CFA Project"

    if not team_id:
        print(f"[TEAMS] No CFA_TEAM_ID - skipping channel creation")
        return {"channel_id": "", "channel_name": channel_name}

    try:
        from msgraph.generated.models.channel import Channel

        body = Channel(
            display_name=channel_name,
            description=f"CFA project channel for {req.organization.name}",
        )
        result = await client.teams.by_team_id(team_id).channels.post(body)
        channel_id = result.id if result else ""
        print(f"[TEAMS] Created channel: {channel_name} ({channel_id})")
        return {"channel_id": channel_id, "channel_name": channel_name}
    except Exception as e:
        print(f"[TEAMS] Error creating channel: {e}")
        return {"channel_id": "", "channel_name": channel_name}


async def post_welcome_message(channel_info: dict, req: ScopingRequest, portal_url: str) -> None:
    """Send a welcome email from Ritu to the client contact.

    App-only credentials cannot post to Teams channels directly, so we
    send a welcome email instead and note the channel in the Scoping
    notification.
    """
    import httpx

    if not req.contact.email:
        print(f"[TEAMS] No client email - skipping welcome message")
        return

    ritu_user_id = "be5fe791-2674-4547-bc8e-eabc67917369"

    email_body = {
        "message": {
            "subject": f"Welcome to your CFA project, {req.contact.first_name}",
            "body": {
                "contentType": "HTML",
                "content": (
                    f"<p>Hi {req.contact.first_name},</p>"
                    f"<p>Welcome to your CFA project. We're excited to work with {req.organization.name}.</p>"
                    f"<p>Here's what you need to know:</p>"
                    f"<ul>"
                    f"<li><strong>Your project portal:</strong> <a href='{portal_url}'>{portal_url}</a></li>"
                    f"<li><strong>Your Teams channel:</strong> {channel_info.get('channel_name', '')} "
                    f"(in the Consulting Leadership Team)</li>"
                    f"</ul>"
                    f"<p>Use your Teams channel for:</p>"
                    f"<ul>"
                    f"<li>Questions and updates during the engagement</li>"
                    f"<li>Sharing files or context with our team</li>"
                    f"<li>Scheduling check-ins</li>"
                    f"</ul>"
                    f"<p><strong>Your CFA team:</strong></p>"
                    f"<ul>"
                    f"<li>Ritu Bahl - Executive Director</li>"
                    f"<li>Gary - Technical Lead</li>"
                    f"</ul>"
                    f"<p>We're looking forward to our scoping conversation.</p>"
                    f"<p>Best,<br>Ritu Bahl<br>Computing for All</p>"
                ),
            },
            "toRecipients": [
                {
                    "emailAddress": {
                        "address": req.contact.email,
                        "name": req.contact.full_name,
                    }
                }
            ],
        },
        "saveToSentItems": True,
    }

    try:
        from graph.auth import _get_credential
        credential = _get_credential()
        token = credential.get_token("https://graph.microsoft.com/.default")
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json",
        }

        url = f"{GRAPH_BASE}/users/{ritu_user_id}/sendMail"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, headers=headers, json=email_body)

        if r.status_code in (200, 202):
            print(f"[TEAMS] Welcome email sent to {req.contact.full_name} ({req.contact.email})")
        else:
            print(f"[TEAMS] Welcome email failed ({r.status_code}): {r.text[:200]}")
    except Exception as e:
        print(f"[TEAMS] Error sending welcome email: {e}")


async def schedule_scoping_meeting(req: ScopingRequest) -> dict:
    """Schedule a Teams meeting with recording enabled on Ritu's calendar.

    Creates a calendar event via Graph API on Ritu's mailbox with a Teams
    online meeting link. Invites the prospect, Jason, and Gary.

    Returns dict with meeting_id, meeting_url, and proposed times.
    """
    import httpx

    # Propose 3 times in the next 5 business days
    now = datetime.now()
    proposed_times = []
    day = now
    while len(proposed_times) < 3:
        day += timedelta(days=1)
        if day.weekday() < 5:  # Mon-Fri
            meeting_time = day.replace(hour=10, minute=0, second=0, microsecond=0)
            proposed_times.append(meeting_time)

    meeting_start = proposed_times[0]
    meeting_end = meeting_start + timedelta(hours=1)

    agenda = (
        "Agenda - CFA Scoping Call\n\n"
        "1. Introductions (5 min)\n"
        "2. Your organization and current data landscape (15 min)\n"
        "3. The problem we're exploring together (15 min)\n"
        "4. What success looks like (10 min)\n"
        "5. CFA's approach and fit (10 min)\n"
        "6. Next steps (5 min)"
    )

    if not config.AZURE_TENANT_ID:
        print(f"[TEAMS] No credentials - skipping meeting creation")
        return {
            "meeting_id": "",
            "meeting_url": "",
            "proposed_times": [t.isoformat() for t in proposed_times],
        }

    # Ritu's user ID — organizer of all scoping calls
    ritu_user_id = "be5fe791-2674-4547-bc8e-eabc67917369"

    # Build attendee list
    attendees = []
    if req.contact.email:
        attendees.append({
            "emailAddress": {"address": req.contact.email, "name": req.contact.full_name},
            "type": "required",
        })

    event_body = {
        "subject": f"CFA Scoping Call - {req.organization.name}",
        "body": {"contentType": "text", "content": agenda},
        "start": {
            "dateTime": meeting_start.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "Pacific Standard Time",
        },
        "end": {
            "dateTime": meeting_end.strftime("%Y-%m-%dT%H:%M:%S"),
            "timeZone": "Pacific Standard Time",
        },
        "attendees": attendees,
        "isOnlineMeeting": True,
        "onlineMeetingProvider": "teamsForBusiness",
    }

    try:
        from graph.auth import _get_credential
        credential = _get_credential()
        token = credential.get_token("https://graph.microsoft.com/.default")
        headers = {
            "Authorization": f"Bearer {token.token}",
            "Content-Type": "application/json",
        }

        url = f"{GRAPH_BASE}/users/{ritu_user_id}/events"
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(url, headers=headers, json=event_body)

        if r.status_code in (200, 201):
            data = r.json()
            meeting_url = data.get("onlineMeeting", {}).get("joinUrl", "")
            event_id = data.get("id", "")
            event_link = data.get("webLink", "")
            print(f"[TEAMS] Meeting scheduled: {meeting_start.strftime('%B %d at %I:%M %p PT')}")
            print(f"[TEAMS] Teams join URL: {meeting_url}")
            print(f"[TEAMS] Attendees: {req.contact.full_name}, Ritu")
            return {
                "meeting_id": event_id,
                "meeting_url": meeting_url,
                "event_link": event_link,
                "proposed_times": [t.isoformat() for t in proposed_times],
            }
        else:
            print(f"[TEAMS] Meeting creation failed ({r.status_code}): {r.text[:300]}")
            return {
                "meeting_id": "",
                "meeting_url": "",
                "proposed_times": [t.isoformat() for t in proposed_times],
            }
    except Exception as e:
        print(f"[TEAMS] Error scheduling meeting: {e}")
        return {
            "meeting_id": "",
            "meeting_url": "",
            "proposed_times": [t.isoformat() for t in proposed_times],
        }


async def post_scoping_initiated(
    req: ScopingRequest,
    briefing_url: str,
    internal_site_url: str,
    portal_url: str,
    channel_info: dict,
    meeting_info: dict,
) -> None:
    """Post the 'SCOPING INITIATED' notification to internal Teams channel."""
    team_id = config.CFA_TEAM_ID
    channel_id = config.SCOPING_NOTIFY_CHANNEL_ID

    times_str = ""
    if meeting_info.get("proposed_times"):
        times_str = " / ".join(meeting_info["proposed_times"][:3])

    message = (
        f"NEW SCOPING INITIATED - {req.organization.name}\n\n"
        f"Contact: {req.contact.full_name}, {req.contact.title}\n"
        f"Industry: {req.organization.industry}\n"
        f"Triggered by: Jason (Apollo stage -> Ready to Scope)\n\n"
        f"Pre-call briefing doc: {briefing_url}\n"
        f"Internal client workspace: {internal_site_url}\n"
        f"Client portal: {portal_url}\n"
        f"Teams channel: {channel_info.get('channel_name', '')}\n"
        f"Scoping meeting: {times_str or 'Pending confirmation'}\n\n"
        "Action required:\n"
        "- Jason: Confirm meeting time with prospect\n"
        "- Ritu + Gary: Review briefing doc before call"
    )

    if not team_id or not channel_id:
        print(f"[TEAMS] No team/channel configured - notification printed to console:")
        print(message)
        return

    try:
        await _post_channel_message(team_id, channel_id, message)
        print(f"[TEAMS] Scoping initiated notification posted")
    except Exception as e:
        print(f"[TEAMS] Error posting notification: {e}")
        print(message)


async def post_scoping_complete(
    req: ScopingRequest,
    analysis: ScopingAnalysis,
    proposal_url: str,
    transcript_url: str,
) -> None:
    """Post the 'SCOPING COMPLETE' notification to internal Teams channel."""
    team_id = config.CFA_TEAM_ID
    channel_id = config.SCOPING_NOTIFY_CHANNEL_ID

    data_confidence = "Not assessed"
    if len(analysis.answers) >= 2:
        data_confidence = analysis.answers[1].confidence

    success_metric = "Not discussed"
    if len(analysis.answers) >= 3:
        success_metric = analysis.answers[2].answer or "Not discussed"

    gaps_text = ""
    if analysis.gaps:
        gaps_text = "\n".join(f"  - {g}" for g in analysis.gaps)
    if analysis.followup_questions:
        gaps_text += "\n" + "\n".join(f"  - {q}" for q in analysis.followup_questions)

    message = (
        f"SCOPING COMPLETE - {req.organization.name}\n\n"
        "Transcript processed. Proposal draft ready for review.\n\n"
        "Scoping summary:\n"
        f"- Problem: {analysis.problem_summary or 'See transcript'}\n"
        f"- Data available: {data_confidence}\n"
        f"- Success metric: {success_metric[:100]}\n"
        f"- Champion: {analysis.champion or 'Not identified'}\n"
        f"- Decision maker: {analysis.decision_maker or 'Not identified'}\n"
        f"- Timeline signal: {analysis.timeline_signal or 'Not discussed'}\n"
        f"- Budget signal: {analysis.budget_signal or 'Not discussed'}\n\n"
        "Gaps to follow up before submitting proposal:\n"
        f"{gaps_text or '  None identified'}\n\n"
        "Documents:\n"
        f"- Proposal draft (review before sending): {proposal_url}\n"
        f"- Full transcript: {transcript_url}\n\n"
        "Actions required:\n"
        "- Gary: Complete technical sections (Sections 4, 5, 6) by [3 business days]\n"
        "- Ritu: Confirm investment figures (Section 8)\n"
        "- Jason: Send gap follow-up questions to prospect"
    )

    if not team_id or not channel_id:
        print(f"[TEAMS] No team/channel configured - notification printed to console:")
        print(message)
        return

    try:
        await _post_channel_message(team_id, channel_id, message)
        print(f"[TEAMS] Scoping complete notification posted")
    except Exception as e:
        print(f"[TEAMS] Error posting notification: {e}")
        print(message)
