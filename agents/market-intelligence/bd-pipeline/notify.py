"""
Agent 12 + Agent 13 — Teams Notifications

Notification types:
- tier_escalation: company moved up a tier
- warm_signal: engagement detected on distributed content
- distribution_confirmation: content distributed to contacts
- weekly_report: Monday 7am summary

Uses Power Automate webhook + Adaptive Cards (existing WFD-OS pattern).

Usage:
    python notify.py --escalation --deployment waifinder-national
    python notify.py --weekly-summary --deployment waifinder-national
    python notify.py --warm-signal --domain example.com --deployment waifinder-national
"""
import os
import sys
import json
import argparse
from datetime import datetime, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../scripts"))
import psycopg2
from pgconfig import PG_CONFIG
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"), override=True)

import requests as http_requests

WEBHOOK_URL = os.getenv("SCOPING_WEBHOOK_URL")


def _post_adaptive_card(card_body, title="Waifinder BD Notification"):
    """Post an Adaptive Card to Teams via Power Automate webhook."""
    if not WEBHOOK_URL:
        print(f"[NOTIFY] No SCOPING_WEBHOOK_URL configured — printing to console:")
        for block in card_body:
            text = block.get("text", "")
            if text:
                print(f"  {text}")
            # Handle ColumnSets
            for col in block.get("columns", []):
                for item in col.get("items", []):
                    if item.get("text"):
                        print(f"    {item['text']}")
        return {"ok": False, "error": "No webhook URL"}

    payload = {
        "type": "message",
        "attachments": [
            {
                "contentType": "application/vnd.microsoft.card.adaptive",
                "content": {
                    "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                    "type": "AdaptiveCard",
                    "version": "1.4",
                    "body": card_body,
                },
            }
        ],
    }

    try:
        resp = http_requests.post(WEBHOOK_URL, json=payload, timeout=15)
        if resp.status_code in (200, 202):
            print(f"[NOTIFY] Teams notification sent: {title}")
            return {"ok": True, "error": None}
        else:
            print(f"[NOTIFY] Webhook failed ({resp.status_code}): {resp.text[:200]}")
            return {"ok": False, "error": f"HTTP {resp.status_code}"}
    except Exception as e:
        print(f"[NOTIFY] Webhook error: {e}")
        return {"ok": False, "error": str(e)}


# ============================================================
# Tier Escalation Alert
# ============================================================

def send_escalation_alerts(deployment_id):
    """Send alerts for companies that changed tiers."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    cur.execute(
        """SELECT company_name, company_domain, tier, previous_tier,
                  scoring_rationale, key_signals, apollo_account_id
           FROM company_scores
           WHERE deployment_id = %s AND tier_changed = TRUE
             AND tier_assigned_at > NOW() - INTERVAL '24 hours'
           ORDER BY tier_assigned_at DESC""",
        (deployment_id,),
    )
    escalations = cur.fetchall()
    conn.close()

    if not escalations:
        print("[NOTIFY] No tier escalations in last 24 hours")
        return

    card_body = [
        {"type": "TextBlock", "text": "Tier Escalation Alert", "weight": "Bolder", "size": "Large"},
        {"type": "TextBlock", "text": f"{len(escalations)} company tier change(s) detected", "wrap": True},
    ]

    for name, domain, tier, prev_tier, rationale, signals, apollo_id in escalations:
        apollo_link = f"https://app.apollo.io/#/accounts/{apollo_id}" if apollo_id else "No Apollo record"
        signal_text = ", ".join(signals[:3]) if signals else "No signals"

        card_body.append({
            "type": "Container",
            "items": [
                {"type": "TextBlock", "text": f"**{name}** ({domain})", "wrap": True},
                {"type": "TextBlock", "text": f"{prev_tier or 'New'} -> **{tier}**", "wrap": True},
                {"type": "TextBlock", "text": f"Key signals: {signal_text}", "wrap": True, "size": "Small"},
                {"type": "TextBlock", "text": (rationale or "")[:200], "wrap": True, "size": "Small"},
                {"type": "TextBlock", "text": apollo_link, "wrap": True, "size": "Small"},
            ],
            "separator": True,
        })

    _post_adaptive_card(card_body, f"Tier Escalation: {len(escalations)} changes")
    print(f"[NOTIFY] Sent {len(escalations)} escalation alert(s)")


# ============================================================
# Warm Signal Alert
# ============================================================

def send_warm_signal_alert(signal_data):
    """Send warm signal alert for a single engagement detection."""
    priority_emoji = {
        "Immediate": "\U0001f534",  # red circle
        "High": "\U0001f7e0",  # orange circle
        "Medium": "\U0001f7e1",  # yellow circle
    }
    emoji = priority_emoji.get(signal_data.get("priority", "Medium"), "\U0001f7e1")

    card_body = [
        {"type": "TextBlock", "text": f"{emoji} Warm Signal Detected", "weight": "Bolder", "size": "Large"},
        {"type": "TextBlock", "text": f"**Priority:** {signal_data.get('priority', 'Medium')}", "wrap": True},
        {"type": "FactSet", "facts": [
            {"title": "Contact", "value": f"{signal_data.get('contact_name', '')} — {signal_data.get('contact_title', '')}"},
            {"title": "Company", "value": f"{signal_data.get('company_name', '')} ({signal_data.get('company_tier', '')})"},
            {"title": "Signal", "value": signal_data.get("signal_type", "")},
            {"title": "Content", "value": signal_data.get("content_engaged_with", "")},
        ]},
    ]

    if signal_data.get("suggested_opening"):
        card_body.append({
            "type": "Container",
            "items": [
                {"type": "TextBlock", "text": "**Suggested Opening:**", "wrap": True},
                {"type": "TextBlock", "text": signal_data["suggested_opening"], "wrap": True, "isSubtle": True},
            ],
            "style": "emphasis",
        })

    if signal_data.get("agent12_rationale_summary"):
        card_body.append({
            "type": "TextBlock",
            "text": f"Agent 12 context: {signal_data['agent12_rationale_summary'][:200]}",
            "wrap": True,
            "size": "Small",
        })

    if signal_data.get("apollo_record_url"):
        card_body.append({
            "type": "TextBlock",
            "text": f"[Apollo Record]({signal_data['apollo_record_url']})",
            "wrap": True,
        })

    _post_adaptive_card(card_body, f"Warm Signal: {signal_data.get('company_name', '')}")


# ============================================================
# Distribution Confirmation
# ============================================================

def send_distribution_confirmation(confirmation_data):
    """Send confirmation after content distribution."""
    card_body = [
        {"type": "TextBlock", "text": "Content Distributed", "weight": "Bolder", "size": "Large"},
        {"type": "FactSet", "facts": [
            {"title": "Content", "value": confirmation_data.get("content_title", "")},
            {"title": "Author", "value": confirmation_data.get("author", "")},
            {"title": "Contacts Reached", "value": str(confirmation_data.get("contacts_reached", 0))},
            {"title": "Confidence", "value": confirmation_data.get("confidence", "Medium")},
        ]},
    ]

    top = confirmation_data.get("top_companies", [])
    if top:
        card_body.append({
            "type": "TextBlock",
            "text": f"**Top companies:** {', '.join(top[:5])}",
            "wrap": True,
        })

    if confirmation_data.get("match_rationale"):
        card_body.append({
            "type": "TextBlock",
            "text": f"Match rationale: {confirmation_data['match_rationale']}",
            "wrap": True,
            "size": "Small",
        })

    _post_adaptive_card(card_body, f"Distributed: {confirmation_data.get('content_title', '')}")


# ============================================================
# Weekly Report
# ============================================================

def send_weekly_summary(deployment_id):
    """Send Monday 7am weekly summary report."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Tier distribution from company_scores
    cur.execute(
        """SELECT tier, COUNT(*)
           FROM (SELECT DISTINCT ON (company_domain) company_domain, tier
                 FROM company_scores WHERE deployment_id = %s
                 ORDER BY company_domain, tier_assigned_at DESC) sub
           GROUP BY tier ORDER BY tier""",
        (deployment_id,),
    )
    tier_dist = dict(cur.fetchall())

    # Prospects tracked
    cur.execute(
        "SELECT COUNT(*) FROM prospect_companies WHERE deployment_id = %s AND is_suppressed = FALSE",
        (deployment_id,),
    )
    total_prospects = cur.fetchone()[0]

    # Content distributed this week
    cur.execute(
        """SELECT COUNT(*) FROM content_submissions
           WHERE deployment_id = %s AND status = 'distributed'
             AND distributed_at > NOW() - INTERVAL '7 days'""",
        (deployment_id,),
    )
    content_distributed = cur.fetchone()[0]

    # Contacts reached this week
    cur.execute(
        """SELECT COUNT(*) FROM distribution_log
           WHERE deployment_id = %s
             AND enrolled_at > NOW() - INTERVAL '7 days'""",
        (deployment_id,),
    )
    contacts_reached = cur.fetchone()[0]

    # Warm signals this week
    cur.execute(
        """SELECT COUNT(*) FROM warm_signals
           WHERE deployment_id = %s
             AND detected_at > NOW() - INTERVAL '7 days'""",
        (deployment_id,),
    )
    warm_signals = cur.fetchone()[0]

    # Signal breakdown
    cur.execute(
        """SELECT signal_type, COUNT(*) FROM warm_signals
           WHERE deployment_id = %s
             AND detected_at > NOW() - INTERVAL '7 days'
           GROUP BY signal_type""",
        (deployment_id,),
    )
    signal_breakdown = dict(cur.fetchall())

    # Top Hot companies
    cur.execute(
        """SELECT DISTINCT ON (company_domain) company_name, company_domain
           FROM company_scores
           WHERE deployment_id = %s AND tier = 'Hot'
           ORDER BY company_domain, tier_assigned_at DESC
           LIMIT 5""",
        (deployment_id,),
    )
    top_hot = cur.fetchall()

    # Tier changes this week
    cur.execute(
        """SELECT COUNT(*) FROM company_scores
           WHERE deployment_id = %s AND tier_changed = TRUE
             AND tier_assigned_at > NOW() - INTERVAL '7 days'""",
        (deployment_id,),
    )
    tier_changes = cur.fetchone()[0]

    conn.close()

    now = datetime.now(timezone.utc)
    card_body = [
        {"type": "TextBlock", "text": "Waifinder BD Weekly Report", "weight": "Bolder", "size": "Large"},
        {"type": "TextBlock", "text": f"Week of {now.strftime('%B %d, %Y')} | {deployment_id}", "wrap": True},
        {"type": "FactSet", "facts": [
            {"title": "Prospects Tracked", "value": str(total_prospects)},
            {"title": "Content Distributed", "value": str(content_distributed)},
            {"title": "Contacts Reached", "value": str(contacts_reached)},
            {"title": "Warm Signals", "value": str(warm_signals)},
            {"title": "Tier Changes", "value": str(tier_changes)},
        ]},
        {"type": "TextBlock", "text": "**Tier Distribution:**", "wrap": True},
    ]

    for tier in ["Hot", "Warm", "Monitor", "Suppressed"]:
        count = tier_dist.get(tier, 0)
        if count:
            card_body.append({"type": "TextBlock", "text": f"  {tier}: {count}", "wrap": True})

    if signal_breakdown:
        card_body.append({"type": "TextBlock", "text": "**Signal Breakdown:**", "wrap": True})
        for sig_type, count in signal_breakdown.items():
            card_body.append({"type": "TextBlock", "text": f"  {sig_type}: {count}", "wrap": True})

    if top_hot:
        card_body.append({"type": "TextBlock", "text": "**Top Hot Prospects:**", "wrap": True})
        for name, domain in top_hot:
            card_body.append({"type": "TextBlock", "text": f"  - {name} ({domain})", "wrap": True})

    _post_adaptive_card(card_body, "Waifinder BD Weekly Report")


# ============================================================
# Partial Contact Digest (Agent 14 → Jason)
# ============================================================

def send_partial_contact_digest(deployment_id):
    """Monday 7am — send Jason a digest of Partial contacts needing manual research."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    cur.execute(
        """SELECT company_name, company_domain, company_tier,
                  recommended_buyer, discovery_notes
           FROM hot_warm_contacts
           WHERE match_confidence = 'Partial'
             AND pipeline_stage = 'Identified'
           ORDER BY
             CASE company_tier WHEN 'Hot' THEN 1 WHEN 'Warm' THEN 2 ELSE 3 END,
             found_at DESC"""
    )
    partials = cur.fetchall()
    conn.close()

    if not partials:
        print("[NOTIFY] No Partial contacts needing manual research")
        return

    card_body = [
        {"type": "TextBlock", "text": "\U0001f4cb Contacts Needing Manual Research",
         "weight": "Bolder", "size": "Large"},
        {"type": "TextBlock", "text": f"{len(partials)} companies need your help (~5 min each)",
         "wrap": True},
    ]

    for name, domain, tier, buyer, notes in partials:
        notes_preview = (notes or "")[:200]
        card_body.append({
            "type": "Container",
            "items": [
                {"type": "TextBlock", "text": f"**{name}** ({domain}) — {tier}", "wrap": True},
                {"type": "TextBlock", "text": f"Looking for: {buyer or 'Executive Director'}", "wrap": True, "size": "Small"},
                {"type": "TextBlock", "text": notes_preview, "wrap": True, "size": "Small"},
            ],
            "separator": True,
        })

    card_body.append({
        "type": "TextBlock",
        "text": f"Total: {len(partials)} companies need your help",
        "wrap": True,
        "weight": "Bolder",
    })

    _post_adaptive_card(card_body, f"Partial Contacts: {len(partials)} need research")
    print(f"[NOTIFY] Sent partial contact digest: {len(partials)} companies")


def main():
    parser = argparse.ArgumentParser(description="Waifinder BD — Teams Notifications")
    parser.add_argument("--deployment", default="waifinder-national")
    parser.add_argument("--escalation", action="store_true")
    parser.add_argument("--weekly-summary", action="store_true")
    parser.add_argument("--warm-signal", action="store_true")
    parser.add_argument("--distribution", action="store_true")
    parser.add_argument("--partial-digest", action="store_true")
    args = parser.parse_args()

    if args.escalation:
        send_escalation_alerts(args.deployment)
    elif args.weekly_summary:
        send_weekly_summary(args.deployment)
    elif args.partial_digest:
        send_partial_contact_digest(args.deployment)
    elif args.warm_signal:
        print("Warm signal alerts are triggered by agent13.py, not CLI")
    elif args.distribution:
        print("Distribution confirmations are triggered by agent13.py, not CLI")
    else:
        print("Specify --escalation, --weekly-summary, or --partial-digest")


if __name__ == "__main__":
    main()
