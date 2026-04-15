"""
Email helper for WFD OS portal APIs — Microsoft Graph API backend.

Uses the existing Graph app registration (GRAPH_CLIENT_ID) and sends via
POST https://graph.microsoft.com/v1.0/users/{sender}/sendMail

Configuration (from .env, loaded by callers):
    GRAPH_TENANT_ID        — Azure tenant
    GRAPH_CLIENT_ID        — App client id
    GRAPH_CLIENT_SECRET    — App client secret
    EMAIL_SENDER           — (optional) mailbox to send from, defaults to ritu@computingforall.org
    NOTIFY_EMAIL           — (optional) default internal recipient, defaults to ritu@computingforall.org

The app registration must have Application permission `Mail.Send` granted
(admin consent required). No user delegation is used.

Public API:
    send_email(to, subject, body, html=True) -> dict
    notify_internal(subject, body)          -> dict

Both functions NEVER raise — they always return a status dict:
    {"sent": bool, "reason": str, "to": str, "subject": str, ...}

If the Graph call fails, full error details are logged and the caller
continues unaffected. This guarantees that form submission and other
user-facing flows are never blocked by email issues.
"""
from __future__ import annotations

import os
import sys
import traceback
from typing import Optional

import httpx

from wfdos_common.graph.auth import _get_credential

# On Windows, uvicorn inherits cp1252 stdout which can't encode unicode
# characters (checkmarks, em-dashes) we use in email bodies. Reconfigure
# stdout/stderr to UTF-8 with errors='replace' so console logging never
# crashes the caller.
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


GRAPH_BASE = "https://graph.microsoft.com/v1.0"
# TODO(#18): CFA-specific default — moves to wfdos_common.config.org.default_sender_email
# as part of the CFA → Waifinder identity decoupling. Kept as a literal here to preserve
# behavior during the #17 migration (no breaking changes invariant).
DEFAULT_SENDER = "ritu@computingforall.org"


def _safe_print(line: str) -> None:
    """Print a line that may contain unicode; fall back to ASCII on error."""
    try:
        print(line)
    except UnicodeEncodeError:
        print(line.encode("ascii", errors="replace").decode("ascii"))


def _get_graph_token() -> Optional[str]:
    """Fetch an app-only Graph token. Returns None on failure."""
    try:
        cred = _get_credential()
        token_obj = cred.get_token("https://graph.microsoft.com/.default")
        return token_obj.token
    except Exception as e:
        _safe_print(f"[EMAIL] Graph token fetch failed: {type(e).__name__}: {e}")
        return None


def _body_to_html(body: str) -> str:
    """Convert a plain-text body to minimally-formatted HTML.

    Preserves line breaks and whitespace. If the caller already provided HTML
    (detected by a leading '<'), returns it unchanged.
    """
    if not body:
        return ""
    stripped = body.lstrip()
    if stripped.startswith("<"):
        return body
    # Escape HTML special chars and preserve whitespace via CSS
    import html as htmllib
    escaped = htmllib.escape(body)
    return (
        '<div style="font-family: -apple-system, Segoe UI, Arial, sans-serif; '
        'font-size: 14px; line-height: 1.5; color: #222; white-space: pre-wrap;">'
        + escaped
        + "</div>"
    )


def send_email(
    to: str,
    subject: str,
    body: str,
    html: bool = True,
    sender: Optional[str] = None,
    cc: Optional[list[str]] = None,
    reply_to: Optional[str] = None,
) -> dict:
    """Send an email via Microsoft Graph sendMail. Never raises.

    Args:
        to:       recipient email address
        subject:  email subject line
        body:     email body (plain text will be wrapped in minimal HTML unless html=False)
        html:     True (default) sends HTML; False sends as plain text
        sender:   override sender mailbox (defaults to EMAIL_SENDER env var or ritu@)
        cc:       optional list of CC addresses
        reply_to: optional reply-to address

    Returns:
        {"sent": bool, "reason": str, "to": str, "subject": str,
         "status_code": int | None, "sender": str}
    """
    if not to:
        return {"sent": False, "reason": "no recipient", "to": to, "subject": subject,
                "status_code": None, "sender": ""}

    sender = sender or os.getenv("EMAIL_SENDER") or DEFAULT_SENDER

    token = _get_graph_token()
    if not token:
        return {"sent": False, "reason": "Graph token unavailable (check GRAPH_* env vars)",
                "to": to, "subject": subject, "status_code": None, "sender": sender}

    # Build the sendMail request body
    content_type = "HTML" if html else "Text"
    content = _body_to_html(body) if html else body

    message: dict = {
        "subject": subject,
        "body": {
            "contentType": content_type,
            "content": content,
        },
        "toRecipients": [{"emailAddress": {"address": to}}],
    }
    if cc:
        message["ccRecipients"] = [{"emailAddress": {"address": addr}} for addr in cc]
    if reply_to:
        message["replyTo"] = [{"emailAddress": {"address": reply_to}}]

    payload = {
        "message": message,
        "saveToSentItems": True,
    }

    url = f"{GRAPH_BASE}/users/{sender}/sendMail"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    try:
        r = httpx.post(url, headers=headers, json=payload, timeout=30.0)
    except Exception as e:
        _safe_print(f"[EMAIL ERROR] Graph sendMail exception: {type(e).__name__}: {e}")
        traceback.print_exc()
        return {"sent": False, "reason": f"{type(e).__name__}: {e}",
                "to": to, "subject": subject, "status_code": None, "sender": sender}

    # 202 Accepted is the success status for sendMail
    if r.status_code == 202:
        _safe_print(f"[EMAIL SENT] to={to} from={sender} subject={subject!r}")
        return {"sent": True, "reason": "ok (202 Accepted)",
                "to": to, "subject": subject, "status_code": 202, "sender": sender}

    # Non-success — log full response body for diagnosis
    try:
        detail = r.json()
    except Exception:
        detail = r.text[:500]
    _safe_print(f"[EMAIL ERROR] Graph sendMail HTTP {r.status_code} to={to} sender={sender}")
    _safe_print(f"[EMAIL ERROR] response: {detail}")
    return {
        "sent": False,
        "reason": f"HTTP {r.status_code}: {str(detail)[:200]}",
        "to": to,
        "subject": subject,
        "status_code": r.status_code,
        "sender": sender,
    }


def notify_internal(subject: str, body: str) -> dict:
    """Send an email to the internal NOTIFY_EMAIL address."""
    to = os.getenv("NOTIFY_EMAIL", DEFAULT_SENDER)
    if not to:
        _safe_print(f"[EMAIL] NOTIFY_EMAIL not set; subject={subject!r}")
        return {"sent": False, "reason": "NOTIFY_EMAIL not set",
                "to": "", "subject": subject, "status_code": None, "sender": ""}
    return send_email(to, subject, body)
