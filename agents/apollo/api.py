"""
Apollo Integration API — outbound contact creation + inbound webhook handling.

Endpoints:
  GET  /api/apollo/sequences          — list all CFA sequences
  GET  /api/apollo/stages             — list pipeline stages
  POST /api/apollo/contacts           — create contact + optional sequence enrollment
  GET  /api/apollo/contacts/{email}   — look up contact by email
  POST /api/apollo/webhook            — receive Apollo webhook events
  GET  /api/apollo/webhook/events     — list recent webhook events
  GET  /api/health

Run: uvicorn agents.apollo.api:app --port 8010
"""
import json
import os
from datetime import timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import psycopg2.extras

# wfdos_common.config auto-loads the repo .env via python-dotenv find_dotenv —
# no hardcoded path needed. Pre-#27 this file had sys.path.insert hacks; the
# monorepo root pyproject.toml (#27) now exposes `agents.*` as a namespace
# package, so direct imports resolve without them.
from wfdos_common.config import PG_CONFIG

from agents.apollo.client import (
    create_contact,
    get_sequences,
    enroll_in_sequence,
    get_stages,
    get_contact_by_email,
)

app = FastAPI(title="WFD OS Apollo Integration API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Outbound endpoints
# ---------------------------------------------------------------------------

@app.get("/api/apollo/sequences")
def list_sequences():
    return get_sequences()


@app.get("/api/apollo/stages")
def list_stages():
    stages = get_stages()
    return {"stages": stages, "count": len(stages)}


class CreateContactRequest(BaseModel):
    email: str
    first_name: str
    last_name: str
    organization: str
    title: Optional[str] = None
    phone: Optional[str] = None
    source: str = "wfd_os"
    reference_number: str = ""
    label_names: Optional[list[str]] = None
    sequence_id: Optional[str] = None  # auto-enroll if provided


@app.post("/api/apollo/contacts")
def api_create_contact(req: CreateContactRequest):
    result = create_contact(
        first_name=req.first_name,
        last_name=req.last_name,
        email=req.email,
        organization=req.organization,
        title=req.title,
        phone=req.phone,
        source=req.source,
        reference_number=req.reference_number,
        label_names=req.label_names,
    )

    enrollment = None
    if result.get("ok") and result.get("contact_id") and req.sequence_id:
        enrollment = enroll_in_sequence(result["contact_id"], req.sequence_id)

    return {
        "contact": result,
        "enrollment": enrollment,
    }


@app.get("/api/apollo/contacts/{email}")
def api_get_contact(email: str):
    result = get_contact_by_email(email)
    if not result.get("ok"):
        raise HTTPException(status_code=502, detail=result.get("error", "Apollo lookup failed"))
    return result


# ---------------------------------------------------------------------------
# Inbound webhook
# ---------------------------------------------------------------------------

@app.post("/api/apollo/webhook")
async def apollo_webhook(request: Request):
    """Receive and process webhook events from Apollo.

    Key events handled:
    - contact_stage_changed → "Ready to Scope" triggers Scoping Agent
    - email_replied → updates inquiry status, notifies Ritu
    """
    # Verify webhook secret if configured
    webhook_secret = os.getenv("APOLLO_WEBHOOK_SECRET")
    if webhook_secret:
        header_secret = request.headers.get("X-Apollo-Webhook-Secret", "")
        if header_secret != webhook_secret:
            raise HTTPException(status_code=401, detail="Invalid webhook secret")

    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event_type", payload.get("type", "unknown"))
    contact = payload.get("contact", payload.get("data", {}).get("contact", {}))
    contact_email = contact.get("email", "")
    contact_name = f"{contact.get('first_name', '')} {contact.get('last_name', '')}".strip()
    organization = contact.get("organization_name", contact.get("organization", {}).get("name", ""))
    stage = payload.get("stage", payload.get("data", {}).get("stage", {}))
    stage_name = stage.get("name", "") if isinstance(stage, dict) else str(stage)

    # Log the event
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO apollo_webhook_events
            (event_type, contact_email, contact_name, organization, stage_name, raw_payload)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (event_type, contact_email, contact_name, organization, stage_name, json.dumps(payload)))
    event_id = cur.fetchone()[0]
    conn.commit()

    action_taken = "logged"

    # Handle: contact moved to "Ready to Scope"
    if "stage" in event_type.lower() and stage_name.lower() in ("ready to scope", "ready_to_scope"):
        print(f"[APOLLO WEBHOOK] Ready to Scope trigger: {contact_name} <{contact_email}> at {organization}")

        # Find or create inquiry
        cur2 = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        cur2.execute("SELECT id, status FROM project_inquiries WHERE email = %s ORDER BY created_at DESC LIMIT 1", (contact_email,))
        inquiry = cur2.fetchone()

        if inquiry:
            # Update existing inquiry to trigger Scoping Agent
            if inquiry["status"] not in ("scoping", "scoped", "active"):
                cur.execute("UPDATE project_inquiries SET status = 'scoping', updated_at = NOW() WHERE id = %s", (inquiry["id"],))
                conn.commit()
                action_taken = f"updated inquiry {inquiry['id']} -> scoping (Scoping Agent triggered)"
                print(f"[APOLLO WEBHOOK] Inquiry {inquiry['id']} moved to scoping")

                # Fire scoping agent in background
                try:
                    import httpx
                    httpx.patch(
                        "http://localhost:8006/api/consulting/inquiry/" + str(inquiry["id"]) + "/status",
                        json={"status": "scoping"},
                        timeout=5,
                    )
                except Exception as e:
                    print(f"[APOLLO WEBHOOK] Scoping trigger call failed: {e}")
            else:
                action_taken = f"inquiry {inquiry['id']} already at status={inquiry['status']}"
        else:
            # Create new inquiry from Apollo data
            import uuid
            new_id = str(uuid.uuid4())
            first = contact.get("first_name", "")
            last = contact.get("last_name", "")

            # Generate reference number
            from datetime import datetime
            year = datetime.now().year
            cur.execute("SELECT COALESCE(MAX(CAST(SUBSTRING(reference_number FROM %s) AS INTEGER)), 0) FROM project_inquiries WHERE reference_number LIKE %s",
                        (len(f"INQ-{year}-") + 1, f"INQ-{year}-%"))
            max_seq = cur.fetchone()[0] or 0
            ref = f"INQ-{year}-{max_seq + 1:04d}"

            cur.execute("""
                INSERT INTO project_inquiries
                    (id, reference_number, organization_name, contact_name, email, status, project_description, apollo_contact_id, notes)
                VALUES (%s, %s, %s, %s, %s, 'scoping', %s, %s, %s)
            """, (
                new_id, ref, organization or "Unknown (from Apollo)",
                f"{first} {last}".strip() or "Unknown",
                contact_email, f"Auto-created from Apollo webhook (Ready to Scope)",
                contact.get("id", ""), f"Created by Apollo webhook event {event_id}",
            ))
            conn.commit()
            action_taken = f"created new inquiry {ref} -> scoping (from Apollo webhook)"
            print(f"[APOLLO WEBHOOK] Created inquiry {ref} for {contact_email}")

    # Handle: email replied
    elif "replied" in event_type.lower() or "reply" in event_type.lower():
        print(f"[APOLLO WEBHOOK] Reply from: {contact_name} <{contact_email}>")
        cur2 = conn.cursor()
        cur2.execute("""
            UPDATE project_inquiries SET status = 'contacted',
                notes = COALESCE(notes || E'\n', '') || %s,
                updated_at = NOW()
            WHERE email = %s AND status = 'new'
            RETURNING id
        """, (f"[{datetime.now(timezone.utc).isoformat()[:19]}] Replied to Apollo sequence", contact_email))
        updated = cur2.fetchone()
        conn.commit()

        if updated:
            action_taken = f"inquiry {updated[0]} -> contacted (replied to sequence)"
            # Notify Ritu
            try:
                from agents.portal.email import send_email
                send_email(
                    "ritu@computingforall.org",
                    f"Apollo reply: {contact_name} at {organization}",
                    f"{contact_name} ({contact_email}) replied to an Apollo email sequence.\n\nOrganization: {organization}\n\nReview in dashboard: http://localhost:3000/internal",
                )
            except Exception:
                pass
        else:
            action_taken = "no matching 'new' inquiry found for reply event"

    # Mark event as processed
    cur.execute("""
        UPDATE apollo_webhook_events SET processed = TRUE, processed_at = NOW(), action_taken = %s WHERE id = %s
    """, (action_taken, event_id))
    conn.commit()
    conn.close()

    return {"received": True, "event_id": event_id, "action_taken": action_taken}


@app.get("/api/apollo/webhook/events")
def list_webhook_events(limit: int = 20):
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, event_type, contact_email, contact_name, organization, stage_name,
               processed, action_taken, created_at
        FROM apollo_webhook_events
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))
    events = []
    for r in cur.fetchall():
        d = dict(r)
        if d.get("created_at"):
            d["created_at"] = d["created_at"].isoformat()
        events.append(d)
    conn.close()
    return {"events": events, "count": len(events)}


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "apollo-api", "port": 8010}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8010)
