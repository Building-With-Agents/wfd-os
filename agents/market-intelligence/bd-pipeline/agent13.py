"""
Agent 13 — Content Distribution Agent (Runtime Harness)

Generates personalized email sequences via Gemini, creates drafts
in sender's Microsoft 365 mailbox via Graph API for human review.
After approval, sends Touch 1 and auto-schedules Touch 2/3.
Detects replies via inbox polling and writes to scoring_feedback.

Apollo is used for contact data only — all email sending is via
Microsoft Graph API.

Usage:
    python agent13.py --distribute --deployment waifinder-national
    python agent13.py --process-touches --deployment waifinder-national
    python agent13.py --poll-replies --deployment waifinder-national
"""
import os
import sys
import json
import time
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../apollo"))
import psycopg2
from pgconfig import PG_CONFIG
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"), override=True)

import requests as http_requests

# ============================================================
# CONFIG
# ============================================================

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

MAX_CONTACTS_PER_RUN = 50
MAX_RETRIES = 2
BASE_DELAY = 2

SYSTEM_PROMPT_PATH = os.path.join(os.path.dirname(__file__), "agent13_system.txt")

# Sender mapping — Ritu confirmed, Jason TBD
SENDER_EMAILS = {
    "ritu": "ritu@computinforall.org",
    # "jason": "jason@computingforall.org",  # Confirm with Ritu before uncommenting
}

# Ritu's Graph API user ID (from existing codebase)
RITU_USER_ID = "be5fe791-2674-4547-bc8e-eabc67917369"

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


# ============================================================
# Graph API Helpers
# ============================================================

def _get_graph_token():
    """Get Bearer token using Azure ClientSecretCredential."""
    try:
        from azure.identity import ClientSecretCredential
        credential = ClientSecretCredential(
            tenant_id=os.getenv("GRAPH_TENANT_ID", os.getenv("AZURE_TENANT_ID", "")),
            client_id=os.getenv("GRAPH_CLIENT_ID", os.getenv("AZURE_CLIENT_ID", "")),
            client_secret=os.getenv("GRAPH_CLIENT_SECRET", os.getenv("AZURE_CLIENT_SECRET", "")),
        )
        token = credential.get_token("https://graph.microsoft.com/.default")
        return token.token
    except Exception as e:
        print(f"[GRAPH] Token error: {e}")
        return None


def _graph_headers():
    token = _get_graph_token()
    if not token:
        return None
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def _get_user_id(sender_email):
    """Map sender email to Graph user ID."""
    if sender_email == "ritu@computinforall.org":
        return RITU_USER_ID
    # For other senders, use email as userPrincipalName
    return sender_email


def create_draft_email(sender_email, to_email, to_name, subject, body, sequence_id=None):
    """Create a draft in sender's mailbox for human review. Returns message_id."""
    headers = _graph_headers()
    if not headers:
        print("[GRAPH] Cannot create draft — no token")
        return None

    user_id = _get_user_id(sender_email)
    url = f"{GRAPH_BASE}/users/{user_id}/messages"

    categories = []
    if sequence_id:
        categories.append(f"waifinder-sequence-{sequence_id}")

    payload = {
        "subject": subject,
        "body": {
            "contentType": "Text",
            "content": body,
        },
        "toRecipients": [
            {"emailAddress": {"name": to_name, "address": to_email}}
        ],
        "categories": categories,
        "isDraft": True,
    }

    try:
        resp = http_requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code in (200, 201):
            message_id = resp.json().get("id")
            print(f"[GRAPH] Draft created: {subject} -> {to_email} (msg: {message_id[:20]}...)")
            return message_id
        else:
            print(f"[GRAPH] Draft failed: {resp.status_code} {resp.text[:200]}")
            return None
    except Exception as e:
        print(f"[GRAPH] Draft error: {e}")
        return None


def send_approved_email(sender_email, message_id):
    """Send a previously created draft that has been approved."""
    headers = _graph_headers()
    if not headers:
        return False

    user_id = _get_user_id(sender_email)
    url = f"{GRAPH_BASE}/users/{user_id}/messages/{message_id}/send"

    try:
        resp = http_requests.post(url, headers=headers, timeout=30)
        if resp.status_code == 202:
            print(f"[GRAPH] Email sent: {message_id[:20]}...")
            return True
        else:
            print(f"[GRAPH] Send failed: {resp.status_code} {resp.text[:200]}")
            return False
    except Exception as e:
        print(f"[GRAPH] Send error: {e}")
        return False


# NOTE: send_email_direct() removed by design.
# All outbound emails MUST go through the BD dashboard approve flow:
#   POST /api/consulting/bd/email-drafts/{id}/approve
# This guarantees no automatic sending of any kind.


def poll_inbox_for_replies(sender_email):
    """Check inbox for replies to sent sequence emails."""
    headers = _graph_headers()
    if not headers:
        return []

    user_id = _get_user_id(sender_email)
    url = (
        f"{GRAPH_BASE}/users/{user_id}/messages"
        f"?$filter=isDraft eq false and isRead eq false"
        f"&$orderby=receivedDateTime desc"
        f"&$top=50"
        f"&$select=id,subject,from,receivedDateTime,bodyPreview,conversationId"
    )

    try:
        resp = http_requests.get(url, headers=headers, timeout=30)
        if resp.status_code == 200:
            return resp.json().get("value", [])
        else:
            print(f"[GRAPH] Inbox poll failed: {resp.status_code}")
            return []
    except Exception as e:
        print(f"[GRAPH] Inbox poll error: {e}")
        return []


# ============================================================
# Gemini Email Generation
# ============================================================

def _call_gemini(prompt, temperature=0.7):
    """Call Gemini REST API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}"

    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature},
    }

    for attempt in range(MAX_RETRIES):
        try:
            resp = http_requests.post(url, json=payload, timeout=60)
            if resp.status_code == 429:
                time.sleep(BASE_DELAY * (2 ** (attempt + 1)))
                continue
            if resp.status_code != 200:
                continue

            data = resp.json()
            text = ""
            for part in data.get("candidates", [{}])[0].get("content", {}).get("parts", []):
                if "text" in part:
                    text += part["text"]

            text = text.strip()
            if text.startswith("```"):
                lines = text.split("\n")
                text = "\n".join(lines[1:-1])

            return json.loads(text)
        except (json.JSONDecodeError, Exception) as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(BASE_DELAY)

    return None


def _read_outreach_definition(cur, deployment_id):
    cur.execute(
        "SELECT definition FROM outreach_definitions WHERE deployment_id = %s ORDER BY updated_at DESC LIMIT 1",
        (deployment_id,),
    )
    row = cur.fetchone()
    return row[0] if row else ""


def _get_voice_guide(sender, outreach_def):
    """Extract voice guide for sender from outreach definition."""
    if sender == "ritu":
        return ("Ritu's voice — direct, technically credible, strategically minded. "
                "Speaks as a peer to operational leaders. Leads with insight.")
    elif sender == "jason":
        return ("Jason's voice — warm, relationship-oriented, never pushy. "
                "Leads with connection and curiosity.")
    return "Professional, insightful, empathetic."


def generate_email_sequence(contact, scores, content, sender, outreach_def):
    """Generate all 3 touches for a personalized email sequence."""
    voice = _get_voice_guide(sender, outreach_def)

    prompt = f"""Write a 3-touch personalized outreach email sequence from {sender} to {contact['contact_name']}, {contact['contact_title']} at {contact['company_name']}.

Sender voice: {voice}

What we know about their situation:
{scores.get('scoring_rationale', 'No scoring data available')}

Their digital transformation signals:
Fragmented data: {scores.get('fragmented_data_evidence', 'Unknown')}
Technology ambition: {scores.get('technology_ambition_evidence', 'Unknown')}
Execution gap: {scores.get('execution_gap_evidence', 'Unknown')}

Content piece to reference:
Title: {content['title']}
URL: {content.get('url', '')}

Touch 1 — initial outreach:
Lead with their specific situation. Reference the content piece naturally. One clear low-pressure call to action.

Touch 2 — follow-up (sent 5 days later):
Different angle. Reference something specific from their public presence. Shorter than Touch 1.

Touch 3 — final touch (sent 10 days after Touch 1):
Acknowledge they may be busy. Leave door open. No pressure. Shortest of the three.

Rules:
- Never pitch Waifinder directly
- Never mention price
- Sound like a human who did their homework — not a sales sequence
- Subject line: specific to their situation, not generic
- Body: 3-5 sentences maximum per touch
- One link maximum per touch

Return JSON:
{{
  "subject": "subject line (used for all 3 touches)",
  "touch_1": "email body plain text",
  "touch_2": "email body plain text",
  "touch_3": "email body plain text"
}}"""

    return _call_gemini(prompt, temperature=0.7)


# ============================================================
# Content Distribution
# ============================================================

def distribute_content(deployment_id, region):
    """Match pending content to scored companies, generate emails, create drafts."""
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    outreach_def = _read_outreach_definition(cur, deployment_id)
    print(f"  Outreach definition: {len(outreach_def)} chars")

    # Get pending content
    cur.execute(
        """SELECT id, title, url, author, vertical, topic_tags, funnel_stage
           FROM content_submissions
           WHERE status = 'pending' AND deployment_id = %s
           ORDER BY submitted_at""",
        (deployment_id,),
    )
    pending = cur.fetchall()
    print(f"  Pending content: {len(pending)}")

    if not pending:
        print("  No pending content to distribute")
        conn.close()
        return {"distributed": 0, "sequences_created": 0}

    total_sequences = 0

    for content_id, title, url, author, vertical, topic_tags, funnel_stage in pending:
        print(f"\n  Content: '{title}' by {author}")

        sender = author or "ritu"
        sender_email = SENDER_EMAILS.get(sender)
        if not sender_email:
            print(f"    No sender email for '{sender}' — skipping")
            continue

        # Get Hot/Warm contacts from hot_warm_contacts
        cur.execute(
            """SELECT hwc.id, hwc.company_domain, hwc.company_name, hwc.company_tier,
                      hwc.contact_name, hwc.contact_title, hwc.contact_email,
                      hwc.match_confidence
               FROM hot_warm_contacts hwc
               WHERE hwc.match_confidence IN ('High', 'Medium')
                 AND hwc.contact_email IS NOT NULL
                 AND hwc.company_domain NOT IN (
                     SELECT company_domain FROM email_sequences
                     WHERE content_id = %s
                 )
               ORDER BY
                 CASE hwc.company_tier WHEN 'Hot' THEN 1 WHEN 'Warm' THEN 2 ELSE 3 END,
                 hwc.found_at DESC
               LIMIT %s""",
            (content_id, MAX_CONTACTS_PER_RUN),
        )
        contacts = cur.fetchall()
        print(f"    Eligible contacts (email verified): {len(contacts)}")

        for (hwc_id, domain, co_name, tier, c_name, c_title, c_email, confidence) in contacts:
            # Get scoring data
            cur.execute(
                """SELECT scoring_rationale, fragmented_data_evidence,
                          technology_ambition_evidence, execution_gap_evidence
                   FROM company_scores
                   WHERE company_domain = %s
                   ORDER BY tier_assigned_at DESC LIMIT 1""",
                (domain,),
            )
            score_row = cur.fetchone()
            scores = {
                "scoring_rationale": score_row[0] if score_row else "",
                "fragmented_data_evidence": score_row[1] if score_row else "",
                "technology_ambition_evidence": score_row[2] if score_row else "",
                "execution_gap_evidence": score_row[3] if score_row else "",
            }

            contact_data = {
                "contact_name": c_name,
                "contact_title": c_title,
                "company_name": co_name,
            }
            content_data = {"title": title, "url": url}

            # Generate email sequence via Gemini
            print(f"    Generating sequence: {c_name} @ {co_name}...")
            email = generate_email_sequence(contact_data, scores, content_data, sender, outreach_def)

            if not email or not email.get("subject"):
                print(f"      Failed to generate email")
                continue

            subject = email["subject"]
            touch_1 = email.get("touch_1", "")
            touch_2 = email.get("touch_2", "")
            touch_3 = email.get("touch_3", "")

            # Create draft in sender's mailbox for Touch 1
            message_id = create_draft_email(sender_email, c_email, c_name, subject, touch_1)

            # Write to email_sequences
            cur.execute(
                """INSERT INTO email_sequences
                   (contact_id, content_id, company_domain, company_name,
                    contact_name, contact_email, sender, sender_email,
                    subject_line, touch_1_body, touch_1_message_id,
                    touch_2_body, touch_3_body,
                    sequence_status, deployment_id)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING id""",
                (
                    hwc_id, content_id, domain, co_name,
                    c_name, c_email, sender, sender_email,
                    subject, touch_1, message_id,
                    touch_2, touch_3,
                    "pending_review", deployment_id,
                ),
            )
            seq_id = cur.fetchone()[0]
            total_sequences += 1

            status = "draft_created" if message_id else "generated"
            print(f"      Subject: {subject}")
            print(f"      Sequence #{seq_id}: {status} -> {c_email} [{tier}]")

            time.sleep(1)

        # Update content status
        if total_sequences > 0:
            cur.execute(
                "UPDATE content_submissions SET status = 'distributed', distributed_at = NOW() WHERE id = %s",
                (content_id,),
            )

    conn.close()
    print(f"\n  Distribution complete: {total_sequences} sequences created")
    return {"distributed": len(pending), "sequences_created": total_sequences}


# ============================================================
# Sequence Touch Processing
#
# CRITICAL RULE: This function NEVER sends emails directly.
# It only transitions sequences to 'pending_review' status when Touch 2
# or Touch 3 becomes due. The actual send always requires human approval
# via the BD dashboard.
# ============================================================

def process_sequence_touches(deployment_id):
    """Promote due touches to pending_review for human approval.

    No emails are sent here. After Touch 1 is sent and 5 days pass with no
    reply, the sequence moves to current_touch=2, status=pending_review so
    Ritu sees the Touch 2 draft on the BD dashboard. Same for Touch 3 after
    another 5 days (10 total since Touch 1).
    """
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    # Touch 2 ready for review: Touch 1 sent 5+ days ago, no reply, current_touch still 1
    cur.execute(
        """UPDATE email_sequences
           SET current_touch = 2,
               sequence_status = 'pending_review'
           WHERE sequence_status = 'active'
             AND current_touch = 1
             AND touch_1_sent_at IS NOT NULL
             AND touch_1_sent_at < NOW() - INTERVAL '5 days'
             AND reply_detected_at IS NULL
             AND deployment_id = %s
           RETURNING id, company_name, contact_name""",
        (deployment_id,),
    )
    t2_promoted = cur.fetchall()

    # Touch 3 ready for review: Touch 2 sent 5+ days ago (10 total since Touch 1), no reply
    cur.execute(
        """UPDATE email_sequences
           SET current_touch = 3,
               sequence_status = 'pending_review'
           WHERE sequence_status = 'active'
             AND current_touch = 2
             AND touch_2_sent_at IS NOT NULL
             AND touch_2_sent_at < NOW() - INTERVAL '5 days'
             AND reply_detected_at IS NULL
             AND deployment_id = %s
           RETURNING id, company_name, contact_name""",
        (deployment_id,),
    )
    t3_promoted = cur.fetchall()

    conn.close()
    print(f"  Promoted {len(t2_promoted)} sequence(s) to Touch 2 review, "
          f"{len(t3_promoted)} to Touch 3 review")
    if t2_promoted:
        for seq_id, co, contact in t2_promoted:
            print(f"    Touch 2 ready: #{seq_id} {co} - {contact}")
    if t3_promoted:
        for seq_id, co, contact in t3_promoted:
            print(f"    Touch 3 ready: #{seq_id} {co} - {contact}")
    print("  NOTE: No emails sent. All touches require human approval via BD dashboard.")


# ============================================================
# Reply Detection
# ============================================================

def poll_for_replies(deployment_id):
    """Poll inbox for replies to sequence emails. Write to scoring_feedback immediately."""
    conn = psycopg2.connect(**PG_CONFIG)
    conn.autocommit = True
    cur = conn.cursor()

    # Get active sequences with sent emails
    cur.execute(
        """SELECT id, sender_email, contact_email, company_domain, company_name,
                  contact_name, subject_line
           FROM email_sequences
           WHERE sequence_status = 'active'
             AND reply_detected_at IS NULL
             AND touch_1_sent_at IS NOT NULL
             AND deployment_id = %s""",
        (deployment_id,),
    )
    active_sequences = cur.fetchall()

    if not active_sequences:
        print("  No active sequences to check")
        conn.close()
        return 0

    # Build lookup of contact emails -> sequence IDs
    email_to_seq = {}
    for seq_id, sender_email, contact_email, domain, co_name, c_name, subject in active_sequences:
        email_to_seq[contact_email.lower()] = {
            "seq_id": seq_id,
            "sender_email": sender_email,
            "domain": domain,
            "company_name": co_name,
            "contact_name": c_name,
            "subject": subject,
        }

    # Poll each sender's inbox
    sender_emails = set(s[1] for s in active_sequences)
    replies_found = 0

    for sender_email in sender_emails:
        messages = poll_inbox_for_replies(sender_email)
        print(f"  Polled {sender_email}: {len(messages)} unread messages")

        for msg in messages:
            from_email = msg.get("from", {}).get("emailAddress", {}).get("address", "").lower()
            if from_email in email_to_seq:
                seq_info = email_to_seq[from_email]
                seq_id = seq_info["seq_id"]

                # Update sequence
                cur.execute(
                    """UPDATE email_sequences
                       SET reply_detected_at = NOW(),
                           reply_message_id = %s,
                           reply_body = %s,
                           sequence_status = 'replied'
                       WHERE id = %s""",
                    (msg.get("id"), msg.get("bodyPreview", "")[:500], seq_id),
                )

                # Write to scoring_feedback IMMEDIATELY
                cur.execute(
                    """INSERT INTO scoring_feedback
                       (company_domain, engagement_type, engaged_at,
                        tier_at_engagement, converted_to_conversation)
                       VALUES (%s, %s, NOW(), %s, %s)""",
                    (
                        seq_info["domain"],
                        "email_reply",
                        "Hot",  # We only email Hot/Warm
                        False,  # Will be updated when conversation happens
                    ),
                )

                replies_found += 1
                print(f"  REPLY DETECTED: {seq_info['contact_name']} @ {seq_info['company_name']}")

                # Send warm signal alert
                _send_reply_alert(seq_info, msg)

    conn.close()
    print(f"  Replies detected: {replies_found}")
    return replies_found


def _send_reply_alert(seq_info, message):
    """Send Teams alert when a reply is detected."""
    from notify import _post_adaptive_card

    card_body = [
        {"type": "TextBlock", "text": "\U0001f534 Reply Detected — Immediate",
         "weight": "Bolder", "size": "Large"},
        {"type": "FactSet", "facts": [
            {"title": "Contact", "value": seq_info["contact_name"]},
            {"title": "Company", "value": seq_info["company_name"]},
            {"title": "Subject", "value": seq_info["subject"]},
        ]},
        {"type": "TextBlock", "text": f"Preview: {message.get('bodyPreview', '')[:200]}",
         "wrap": True, "size": "Small"},
        {"type": "TextBlock", "text": "Ritu should respond within 2 hours.",
         "wrap": True, "weight": "Bolder"},
    ]

    _post_adaptive_card(card_body, f"Reply: {seq_info['company_name']}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(description="Agent 13 — Content Distribution Agent")
    parser.add_argument("--deployment", default="waifinder-national")
    parser.add_argument("--region", default="National")
    parser.add_argument("--distribute", action="store_true", help="Generate emails and create drafts")
    parser.add_argument("--process-touches", action="store_true", help="Send pending Touch 2/3")
    parser.add_argument("--poll-replies", action="store_true", help="Check inbox for replies")
    args = parser.parse_args()

    print(f"Agent 13 — {datetime.now(timezone.utc).isoformat()}")
    print(f"Deployment: {args.deployment}")

    if args.distribute:
        print("\n--- CONTENT DISTRIBUTION ---")
        distribute_content(args.deployment, args.region)

    if args.process_touches:
        print("\n--- PROCESS TOUCHES ---")
        process_sequence_touches(args.deployment)

    if args.poll_replies:
        print("\n--- POLL REPLIES ---")
        poll_for_replies(args.deployment)

    if not any([args.distribute, args.process_touches, args.poll_replies]):
        print("Specify --distribute, --process-touches, or --poll-replies")


if __name__ == "__main__":
    main()
