"""
Consulting Intake API — Handles project inquiry form submissions.
Run: uvicorn consulting_api:app --reload --port 8003
"""
import sys, os, json, asyncio, traceback
from datetime import datetime, timezone
from typing import Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr

# Make wfd-os repo root importable so `agents.scoping.*` and `agents.graph.*` resolve
_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv

# Load .env from wfd-os root so SMTP_* vars are picked up
load_dotenv(os.path.join(os.path.dirname(__file__), "../../.env"), override=False)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts"))
from pgconfig import PG_CONFIG

# Email helper — Microsoft Graph backend. Import via full package path so it
# doesn't shadow Python's stdlib `email` package.
from agents.portal.email import notify_internal, send_email

# Scoping Agent pipeline (lazy-imported inside the trigger to avoid blocking module load
# if Graph creds or Anthropic SDK aren't available on startup).

app = FastAPI(title="Waifinder Consulting API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3003", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class ProjectInquiry(BaseModel):
    organization_name: str
    contact_name: str
    contact_role: str | None = None
    email: str
    phone: str | None = None
    is_coalition_member: bool = False
    project_description: str
    problem_statement: str | None = None
    success_criteria: str | None = None
    project_area: str | None = None
    timeline: str | None = None
    budget_range: str | None = None


@app.post("/api/consulting/inquire")
def submit_inquiry(inquiry: ProjectInquiry):
    """Submit a new consulting project inquiry."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Generate a human-friendly reference number: INQ-<year>-<0001, 0002, ...>
    # Uses MAX-based next-value so deletions never cause collisions. Numbers
    # are monotonically increasing within a calendar year.
    # Format is always 'INQ-YYYY-NNNN' (13 chars) — the numeric suffix starts
    # at character position 10 (1-indexed for Postgres SUBSTRING).
    current_year = datetime.now(timezone.utc).year
    prefix = f"INQ-{current_year}-"
    cur.execute("""
        SELECT COALESCE(MAX(CAST(SUBSTRING(reference_number FROM %s) AS INTEGER)), 0)
        FROM project_inquiries
        WHERE reference_number LIKE %s
    """, (len(prefix) + 1, f"{prefix}%"))
    max_seq = cur.fetchone()[0] or 0
    reference_number = f"{prefix}{max_seq + 1:04d}"

    cur.execute("""
        INSERT INTO project_inquiries (
            reference_number,
            organization_name, contact_name, contact_role,
            email, phone, is_coalition_member,
            project_description, problem_statement, success_criteria,
            project_area, timeline, budget_range, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'new')
        RETURNING id
    """, (
        reference_number,
        inquiry.organization_name,
        inquiry.contact_name,
        inquiry.contact_role,
        inquiry.email,
        inquiry.phone,
        inquiry.is_coalition_member,
        inquiry.project_description,
        inquiry.problem_statement,
        inquiry.success_criteria,
        inquiry.project_area,
        inquiry.timeline,
        inquiry.budget_range,
    ))

    inquiry_id = cur.fetchone()[0]
    conn.commit()
    conn.close()

    # --- Send two HTML emails: submitter confirmation + internal notification ---
    # Templates live in agents/portal/email_templates.py. Both calls are wrapped
    # in try/except so form submission NEVER fails due to email issues.
    from agents.portal.email_templates import (
        render_submitter_confirmation,
        render_internal_notification,
    )

    # 1. Confirmation email to the submitter
    try:
        subject, html_body = render_submitter_confirmation(inquiry, reference_number)
        send_email(inquiry.email, subject, html_body, html=True)
    except Exception as e:
        print(f"[WARN] submitter confirmation email raised: {type(e).__name__}: {e}")

    # 2. Internal notification email to Ritu
    try:
        subject, html_body = render_internal_notification(inquiry, reference_number)
        notify_email = os.getenv("NOTIFY_EMAIL", "ritu@computingforall.org")
        send_email(notify_email, subject, html_body, html=True)
    except Exception as e:
        print(f"[WARN] internal notification email raised: {type(e).__name__}: {e}")

    # --- Create Apollo contact (best-effort, never blocks the response) ---
    apollo_contact_id = None
    apollo_sequence_suggested = None
    try:
        from agents.apollo.client import create_contact as apollo_create
        first_name = (inquiry.contact_name or "").strip().split()[0] if inquiry.contact_name else ""
        last_name = " ".join((inquiry.contact_name or "").strip().split()[1:])
        apollo_result = apollo_create(
            first_name=first_name,
            last_name=last_name or "",
            email=inquiry.email,
            organization=inquiry.organization_name,
            title=inquiry.contact_role,
            phone=inquiry.phone,
            source="consulting_inquiry",
            reference_number=reference_number,
        )
        if apollo_result.get("ok"):
            apollo_contact_id = apollo_result.get("contact_id")
            print(f"[APOLLO] Contact created for {inquiry.email} -> {apollo_contact_id}")

            # Determine suggested sequence based on project type / org name
            project_lower = (inquiry.project_area or "").lower() + " " + (inquiry.organization_name or "").lower()
            if "workforce" in project_lower:
                apollo_sequence_suggested = "TX Workforce Board Sequence" if "texas" in project_lower or "tx" in project_lower else "WA Employer Sequence"
            elif "healthcare" in project_lower:
                apollo_sequence_suggested = "WA Employer Sequence"
            else:
                apollo_sequence_suggested = "TX Professional Services Sequence"

            # Save Apollo data to the inquiry row
            conn3 = psycopg2.connect(**PG_CONFIG)
            cur3 = conn3.cursor()
            cur3.execute(
                "UPDATE project_inquiries SET apollo_contact_id = %s, apollo_sequence_suggested = %s WHERE id = %s",
                (apollo_contact_id, apollo_sequence_suggested, inquiry_id),
            )
            conn3.commit()
            conn3.close()
            print(f"[APOLLO] Sequence suggested: {apollo_sequence_suggested} (not auto-enrolled — Jason approves)")
        else:
            print(f"[APOLLO] Contact creation failed: {apollo_result.get('error')}")
    except Exception as e:
        print(f"[WARN] Apollo integration raised: {type(e).__name__}: {e}")

    return {
        "success": True,
        "reference_number": reference_number,
        "inquiry_id": str(inquiry_id),
        "message": "Your project inquiry has been submitted. We'll reach out within 24 hours.",
        "next_steps": [
            "CFA reviews your project description",
            "We schedule a 30-minute scoping call",
            "You receive a fixed-price proposal",
            "You approve before anything starts",
        ],
        "apollo": {
            "contact_created": apollo_contact_id is not None,
            "contact_id": apollo_contact_id,
            "sequence_suggested": apollo_sequence_suggested,
        },
    }


@app.get("/api/consulting/client/{client_id}")
def get_client_engagement(client_id: str):
    """Full engagement data for an active consulting client.

    Accepts either the engagement id (legacy) OR the random client_access_token.
    """
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Look up by client_access_token first (new flow), then by id (legacy / WSB)
    cur.execute(
        "SELECT * FROM consulting_engagements WHERE client_access_token = %s OR id = %s LIMIT 1",
        (client_id, client_id),
    )
    engagement = cur.fetchone()
    # Resolve actual engagement id for downstream queries (keyed by id, not token)
    if engagement:
        client_id = engagement["id"]
    if not engagement:
        conn.close()
        raise HTTPException(status_code=404, detail="Engagement not found")
    engagement = dict(engagement)

    # Milestones
    cur.execute("""
        SELECT milestone_number, title, status, target_date, completed_date, deliverables
        FROM engagement_milestones
        WHERE engagement_id = %s ORDER BY milestone_number
    """, (client_id,))
    milestones = [dict(r) for r in cur.fetchall()]

    # Team
    cur.execute("""
        SELECT member_name, role, is_apprentice, skills, avatar_initials
        FROM engagement_team WHERE engagement_id = %s
    """, (client_id,))
    team = [dict(r) for r in cur.fetchall()]

    # Engagement updates (client-visible activity feed)
    cur.execute("""
        SELECT id, update_date, author, author_email, update_type, title, body, is_client_visible
        FROM engagement_updates
        WHERE engagement_id = %s AND is_client_visible = TRUE
        ORDER BY update_date DESC
    """, (client_id,))
    updates = []
    for r in cur.fetchall():
        u = dict(r)
        if u.get("update_date"):
            u["update_date"] = u["update_date"].isoformat()
        updates.append(u)

    # Deliverables (project outputs)
    cur.execute("""
        SELECT title, description, status, delivered_date, url
        FROM engagement_deliverables
        WHERE engagement_id = %s ORDER BY delivered_date NULLS LAST
    """, (client_id,))
    all_deliverables = [dict(r) for r in cur.fetchall()]

    # Split into deliverables (project work) and documents (reference docs)
    doc_titles = {'Architecture Document', 'Project Proposal', 'Sprint 1 Report',
                  'Sprint 2 Report', 'Scoping Call Recording'}
    deliverables = [d for d in all_deliverables if d['title'] not in doc_titles]
    documents = [d for d in all_deliverables if d['title'] in doc_titles]

    conn.close()

    # Calculate progress
    completed_milestones = sum(1 for m in milestones if m['status'] == 'complete')
    total_milestones = len(milestones)
    progress_pct = round(completed_milestones / total_milestones * 100) if total_milestones else 0

    # Days remaining
    import math
    from datetime import date
    days_remaining = None
    if engagement.get('expected_completion'):
        delta = engagement['expected_completion'] - date.today()
        days_remaining = max(0, delta.days)

    # Serialize dates
    for key in ('start_date', 'expected_completion', 'next_milestone_date', 'created_at', 'updated_at'):
        if engagement.get(key):
            engagement[key] = engagement[key].isoformat() if hasattr(engagement[key], 'isoformat') else str(engagement[key])
    for m in milestones:
        for key in ('target_date', 'completed_date'):
            if m.get(key):
                m[key] = m[key].isoformat()
    for d in deliverables:
        if d.get('delivered_date'):
            d['delivered_date'] = d['delivered_date'].isoformat()

    # Budget summary
    budget = float(engagement.get('budget') or 0)
    invoiced = float(engagement.get('invoiced_amount') or 0)
    paid = float(engagement.get('paid_amount') or 0)

    return {
        "engagement": engagement,
        "milestones": milestones,
        "team": [t for t in team if not t.get('is_apprentice')],
        "apprentices": [t for t in team if t.get('is_apprentice')],
        "deliverables": deliverables,
        "documents": documents,
        "updates": updates,
        "progress": {
            "completed_milestones": completed_milestones,
            "total_milestones": total_milestones,
            "progress_pct": progress_pct,
            "days_remaining": days_remaining,
        },
        "budget_summary": {
            "total": budget,
            "invoiced": invoiced,
            "paid": paid,
            "outstanding": invoiced - paid,
            "remaining": budget - invoiced,
        },
    }


@app.get("/api/consulting/client/{client_id}/documents")
def get_client_documents(client_id: str):
    """List all files in the client's SharePoint workspace (live from Graph).

    Accepts either the random access token or the engagement id. Returns files
    grouped by top-level folder (Scoping, Proposal, Delivery, Financials).
    """
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, organization_name, sharepoint_workspace_url FROM consulting_engagements "
        "WHERE client_access_token = %s OR id = %s LIMIT 1",
        (client_id, client_id),
    )
    eng = cur.fetchone()
    conn.close()
    if not eng:
        raise HTTPException(status_code=404, detail="Engagement not found")

    safe_name = _safe_name(eng["organization_name"])
    stored_sp_url = eng.get("sharepoint_workspace_url")

    try:
        from agents.graph.sharepoint import list_client_documents_sync
        files = list_client_documents_sync(safe_name, recursive=True)
    except Exception as e:
        print(f"[DOCUMENTS] list failed: {type(e).__name__}: {e}")
        files = []

    # Group by top-level section folder (Scoping / Proposal / Delivery / Financials)
    sections: dict[str, list[dict]] = {}
    for f in files:
        rel = f.get("relative_path") or ""
        top = rel.split("/", 1)[0] if rel else "Root"
        sections.setdefault(top, []).append(f)

    # Sort files within each section by last_modified desc
    for section in sections.values():
        section.sort(key=lambda x: x.get("last_modified", ""), reverse=True)

    return {
        "engagement_id": eng["id"],
        "organization_name": eng["organization_name"],
        "safe_name": safe_name,
        "sharepoint_base_url": stored_sp_url or f"https://computinforall.sharepoint.com/sites/wAIFinder/Shared%20Documents/Clients/{safe_name}",
        "total_files": len(files),
        "sections": sections,
        "files": files,
    }


@app.get("/api/consulting/pipeline")
def get_pipeline():
    """Full consulting pipeline: inquiries + active engagements."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # All inquiries
    cur.execute("""
        SELECT id, reference_number, organization_name, contact_name, contact_role, email, phone,
               project_description, problem_statement, success_criteria,
               project_area, timeline, budget_range, status, notes, created_at,
               apollo_contact_id, apollo_sequence_suggested
        FROM project_inquiries
        ORDER BY created_at DESC
    """)
    inquiries = []
    for row in cur.fetchall():
        d = dict(row)
        d['id'] = str(d['id'])
        if d.get('created_at'):
            d['created_at'] = d['created_at'].isoformat()
        if d.get('project_description'):
            d['project_description_short'] = (d['project_description'][:100] + '...') if len(d['project_description']) > 100 else d['project_description']
        inquiries.append(d)

    # All engagements
    cur.execute("""
        SELECT ce.id, ce.organization_name, ce.project_name, ce.status,
               ce.start_date, ce.expected_completion, ce.next_milestone,
               ce.next_milestone_date, ce.cfa_lead, ce.cfa_lead_email,
               ce.budget, ce.invoiced_amount, ce.paid_amount,
               ce.client_access_token, ce.sharepoint_workspace_url,
               (SELECT count(*) FROM engagement_milestones WHERE engagement_id = ce.id AND status = 'complete') as completed,
               (SELECT count(*) FROM engagement_milestones WHERE engagement_id = ce.id) as total,
               (SELECT count(*) FROM engagement_updates WHERE engagement_id = ce.id) as updates_count,
               (SELECT max(update_date) FROM engagement_updates WHERE engagement_id = ce.id) as last_update_at
        FROM consulting_engagements ce
        ORDER BY ce.created_at DESC
    """)
    engagements = []
    for row in cur.fetchall():
        d = dict(row)
        for k in ('start_date', 'expected_completion', 'next_milestone_date', 'last_update_at'):
            if d.get(k):
                d[k] = d[k].isoformat() if hasattr(d[k], 'isoformat') else str(d[k])
        d['progress_pct'] = round(d['completed'] / d['total'] * 100) if d.get('total') else 0
        d['budget'] = float(d['budget']) if d.get('budget') else 0
        d['invoiced_amount'] = float(d['invoiced_amount']) if d.get('invoiced_amount') else 0
        d['paid_amount'] = float(d['paid_amount']) if d.get('paid_amount') else 0
        # Prefer the secure random token if present; fall back to engagement id
        d['portal_token'] = d.get('client_access_token') or d['id']
        engagements.append(d)

    # Stats
    status_counts = {}
    for i in inquiries:
        s = i['status'] or 'new'
        status_counts[s] = status_counts.get(s, 0) + 1

    # Pipeline value from budget ranges
    budget_map = {
        "Under $10K": 5000,
        "$10K - $25K": 17500,
        "$25K - $50K": 37500,
        "$50K+": 75000,
        "Not sure - let's talk": 15000,
    }
    pipeline_value = sum(budget_map.get(i.get('budget_range', ''), 0) for i in inquiries if i.get('status') in ('new', 'contacted', 'scoped'))
    active_value = sum(e.get('budget', 0) for e in engagements if e.get('status') == 'in_progress')

    conn.close()

    return {
        "inquiries": inquiries,
        "engagements": engagements,
        "stats": {
            "new": status_counts.get('new', 0),
            "contacted": status_counts.get('contacted', 0),
            "scoped": status_counts.get('scoped', 0),
            "active_projects": len([e for e in engagements if e.get('status') == 'in_progress']),
            "closed": status_counts.get('closed', 0),
            "pipeline_value": pipeline_value,
            "active_value": active_value,
            "total_pipeline_value": pipeline_value + active_value,
        },
    }


@app.get("/api/consulting/inquiry/{inquiry_id}")
def get_inquiry(inquiry_id: str):
    """Full inquiry details."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM project_inquiries WHERE id = %s", (inquiry_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    d = dict(row)
    d['id'] = str(d['id'])
    if d.get('created_at'):
        d['created_at'] = d['created_at'].isoformat()
    if d.get('updated_at'):
        d['updated_at'] = d['updated_at'].isoformat()
    return d


class StatusUpdate(BaseModel):
    status: str
    notes: str | None = None


VALID_STATUSES = {"new", "contacted", "scoping", "scoped", "active", "closed"}


def _fetch_inquiry(inquiry_id: str) -> dict | None:
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM project_inquiries WHERE id = %s", (inquiry_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def _set_inquiry_status(inquiry_id: str, status: str, note_append: str | None = None) -> None:
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    if note_append:
        cur.execute("""
            UPDATE project_inquiries
            SET status = %s,
                notes = COALESCE(notes || E'\n', '') || %s,
                updated_at = NOW()
            WHERE id = %s
        """, (status, note_append, inquiry_id))
    else:
        cur.execute("""
            UPDATE project_inquiries
            SET status = %s, updated_at = NOW()
            WHERE id = %s
        """, (status, inquiry_id))
    conn.commit()
    conn.close()


def _inquiry_to_scoping_request(inq: dict):
    """Build a ScopingRequest from a project_inquiries row."""
    from agents.scoping.models import ScopingRequest, Contact, Organization

    # Split contact_name into first / last (best-effort)
    full = (inq.get("contact_name") or "").strip()
    parts = full.split(None, 1)
    first = parts[0] if parts else ""
    last = parts[1] if len(parts) > 1 else ""

    return ScopingRequest(
        contact=Contact(
            first_name=first,
            last_name=last,
            title=inq.get("contact_role") or "",
            email=inq.get("email") or "",
        ),
        organization=Organization(
            name=inq.get("organization_name") or "",
            industry=inq.get("project_area") or "",
            short_description=(inq.get("project_description") or "")[:500],
        ),
        notes=f"Submitted via CFA intake form. Inquiry ID: {inq.get('id')}",
    )


def _run_scoping_pipeline_sync(inquiry_id: str) -> None:
    """Background task: build a ScopingRequest and run the Phase 1 pipeline.

    Runs synchronously inside the background task (asyncio.run on the pipeline
    coroutine). Catches all exceptions so the task never propagates errors to
    FastAPI. On success, transitions status to 'scoped' and appends a note.
    On failure, leaves status at 'scoping' and records the error in notes.
    """
    print("=" * 60)
    print(f"[SCOPING TRIGGER] Starting background pipeline for inquiry {inquiry_id}")
    print("=" * 60)
    try:
        inq = _fetch_inquiry(inquiry_id)
        if not inq:
            print(f"[SCOPING TRIGGER] Inquiry {inquiry_id} not found - aborting")
            return

        from agents.scoping.pipeline import run_precall_pipeline
        req = _inquiry_to_scoping_request(inq)
        print(f"[SCOPING TRIGGER] Built request: {req.organization.name} / {req.contact.full_name} <{req.contact.email}>")
        print(f"[SCOPING TRIGGER] safe_name = {req.organization.safe_name}")

        asyncio.run(run_precall_pipeline(req))

        success_note = (
            f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] "
            f"Scoping Agent pipeline completed successfully. "
            f"SharePoint workspace at /sites/wAIFinder/Clients/{req.organization.safe_name}/"
        )
        _set_inquiry_status(inquiry_id, "scoped", note_append=success_note)
        print(f"[SCOPING TRIGGER] Pipeline complete - status -> scoped")

        # Internal notification (console fallback if SMTP not configured)
        try:
            notify_internal(
                subject=f"Scoping Agent done: {req.organization.name}",
                body=(
                    f"The Scoping Agent pipeline completed for {req.organization.name}.\n\n"
                    f"SharePoint: /sites/wAIFinder/Clients/{req.organization.safe_name}/\n"
                    f"Inquiry ID: {inquiry_id}\n\n"
                    f"Review in /internal dashboard."
                ),
            )
        except Exception:
            pass

    except Exception as e:
        tb = traceback.format_exc()
        print(f"[SCOPING TRIGGER] Pipeline FAILED: {type(e).__name__}: {e}")
        print(tb)
        err_note = (
            f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] "
            f"Scoping Agent pipeline FAILED: {type(e).__name__}: {e}"
        )
        try:
            _set_inquiry_status(inquiry_id, "scoping", note_append=err_note)
        except Exception:
            pass


@app.patch("/api/consulting/inquiry/{inquiry_id}/status")
def update_inquiry_status(
    inquiry_id: str,
    update: StatusUpdate,
    background_tasks: BackgroundTasks,
):
    """Update inquiry status and notes. Fires Scoping Agent when status -> 'scoping'."""
    if update.status not in VALID_STATUSES:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {VALID_STATUSES}")

    # Fetch current to detect transition
    current = _fetch_inquiry(inquiry_id)
    if not current:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    prev_status = current.get("status")

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        UPDATE project_inquiries
        SET status = %s, notes = COALESCE(%s, notes), updated_at = NOW()
        WHERE id = %s
        RETURNING id
    """, (update.status, update.notes, inquiry_id))
    result = cur.fetchone()
    conn.commit()
    conn.close()
    if not result:
        raise HTTPException(status_code=404, detail="Inquiry not found")

    scoping_triggered = False
    if update.status == "scoping" and prev_status != "scoping":
        # Fire pipeline as a background task — returns immediately.
        background_tasks.add_task(_run_scoping_pipeline_sync, inquiry_id)
        scoping_triggered = True
        print(f"[SCOPING TRIGGER] Queued background pipeline for inquiry {inquiry_id} ({prev_status} -> scoping)")

    return {
        "success": True,
        "id": str(result[0]),
        "status": update.status,
        "scoping_triggered": scoping_triggered,
    }


def _safe_name(org_name: str) -> str:
    """PascalCase version of an org name for SharePoint paths."""
    return "".join(
        word.capitalize()
        for word in (org_name or "").replace("-", " ").replace("_", " ").split()
        if word.isalnum() or word.replace(".", "").isalnum()
    )


def _public_portal_base() -> str:
    """Base URL the client will use to reach their portal (configurable via env)."""
    return os.getenv("CLIENT_PORTAL_BASE_URL", "http://localhost:3000").rstrip("/")


@app.delete("/api/consulting/inquiry/{inquiry_id}")
def delete_inquiry(inquiry_id: str):
    """Hard-delete a single inquiry. Returns the deleted row's organization
    name so the client can show a friendly toast."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM project_inquiries WHERE id = %s RETURNING organization_name, reference_number",
        (inquiry_id,),
    )
    row = cur.fetchone()
    conn.commit()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Inquiry not found")
    return {
        "success": True,
        "id": inquiry_id,
        "organization_name": row[0],
        "reference_number": row[1],
    }


@app.delete("/api/consulting/inquiries/test-entries")
def delete_test_inquiries():
    """Bulk-delete inquiries that look like test data.

    Matches rows where organization_name OR email contains the literal
    string 'test' (case-insensitive). Returns the list of deleted rows
    so the UI can show exactly what was removed.
    """
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        DELETE FROM project_inquiries
        WHERE organization_name ILIKE %s OR email ILIKE %s
        RETURNING id, reference_number, organization_name, email
    """, ("%test%", "%test%"))
    deleted = [dict(r) for r in cur.fetchall()]
    for d in deleted:
        d["id"] = str(d["id"])
    conn.commit()
    conn.close()
    return {
        "success": True,
        "deleted_count": len(deleted),
        "deleted": deleted,
    }


@app.post("/api/consulting/inquiry/{inquiry_id}/convert")
def convert_inquiry(inquiry_id: str):
    """Convert a scoped inquiry to an active consulting engagement.

    Steps:
      1. Create consulting_engagements row with random client_access_token
      2. Grant the client SharePoint access to /sites/wAIFinder/Clients/<SafeName>/
      3. Send welcome email with portal link + SharePoint note
      4. Update inquiry status to 'active'
    """
    import re, secrets

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get inquiry
    cur.execute("SELECT * FROM project_inquiries WHERE id = %s", (inquiry_id,))
    inquiry = cur.fetchone()
    if not inquiry:
        conn.close()
        raise HTTPException(status_code=404, detail="Inquiry not found")
    inquiry = dict(inquiry)

    # Generate slug-based engagement id
    slug = re.sub(r'[^a-z0-9]', '', inquiry['organization_name'].lower())[:20]
    cur.execute("SELECT id FROM consulting_engagements WHERE id LIKE %s", (f"{slug}%",))
    existing = cur.fetchall()
    suffix = f"-{len(existing)+1:03d}"
    engagement_id = f"{slug}{suffix}"

    # Generate cryptographically-random client access token (distinct from engagement_id)
    client_access_token = secrets.token_urlsafe(24)

    safe_name = _safe_name(inquiry['organization_name'])
    sharepoint_url = f"https://computinforall.sharepoint.com/sites/wAIFinder/Clients/{safe_name}"

    # Budget estimate from range
    budget_map = {
        "Under $10K": 8000,
        "$10K - $25K": 17500,
        "$25K - $50K": 37500,
        "$50K+": 75000,
        "Not sure - let's talk": 25000,
    }
    budget = budget_map.get(inquiry.get('budget_range', ''), 25000)

    # Create engagement
    cur.execute("""
        INSERT INTO consulting_engagements (
            id, organization_name, contact_name, contact_email,
            project_name, project_description, status,
            start_date, expected_completion, budget, invoiced_amount, paid_amount,
            next_milestone, next_milestone_date,
            cfa_lead, cfa_lead_email, tech_lead, tech_lead_email,
            client_access_token, sharepoint_workspace_url
        ) VALUES (%s, %s, %s, %s, %s, %s, 'in_progress',
                  CURRENT_DATE, CURRENT_DATE + INTERVAL '90 days',
                  %s, 0, 0, 'Discovery and scoping', CURRENT_DATE + INTERVAL '14 days',
                  'Ritu Bahl', 'ritu@computingforall.org', 'Gary', 'gary@computingforall.org',
                  %s, %s)
        RETURNING id
    """, (
        engagement_id,
        inquiry['organization_name'],
        inquiry['contact_name'],
        inquiry['email'],
        inquiry.get('project_area') or 'Consulting Project',
        inquiry['project_description'],
        budget,
        client_access_token,
        sharepoint_url,
    ))

    # Update inquiry status
    cur.execute("UPDATE project_inquiries SET status = 'active', updated_at = NOW() WHERE id = %s", (inquiry_id,))
    conn.commit()
    conn.close()

    # --- Grant SharePoint access (best-effort; never blocks the response) ---
    sharepoint_invite: dict = {"ok": False, "error": "not attempted"}
    try:
        from agents.graph.invitations import invite_to_client_folder
        sharepoint_invite = invite_to_client_folder(
            company_safe_name=safe_name,
            email=inquiry['email'],
            display_name=inquiry['contact_name'],
            roles=["read"],
            message=(
                f"Welcome to your CFA project workspace for "
                f"{inquiry['organization_name']}. This folder contains all project "
                f"documents, proposals, and deliverables. — Computing for All"
            ),
        )
    except Exception as e:
        print(f"[CONVERT] SharePoint invite exception: {type(e).__name__}: {e}")
        sharepoint_invite = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    # --- Send welcome email with portal link (mailer has console fallback) ---
    portal_url = f"{_public_portal_base()}/coalition/client?token={client_access_token}"
    welcome_sent: dict = {"sent": False}
    try:
        welcome_subject = f"Welcome to your CFA project, {inquiry['contact_name'].split()[0] if inquiry['contact_name'] else 'team'}!"
        welcome_body = (
            f"Hello {inquiry['contact_name'] or 'there'},\n\n"
            f"Thank you for choosing Computing for All for your {inquiry.get('project_area') or 'AI'} project. "
            f"Your engagement is now active and we are getting to work.\n\n"
            f"YOUR CLIENT PORTAL\n"
            f"{portal_url}\n"
            f"Bookmark this link — it is your single source of truth for project status, "
            f"milestones, deliverables, and our team.\n\n"
            f"YOUR PROJECT WORKSPACE (SharePoint)\n"
            f"{sharepoint_url}\n"
            f"You have been granted read access. You will receive a separate email from "
            f"Microsoft SharePoint with a link to accept the invitation. Sign in with the "
            f"email address this message was sent to.\n\n"
            f"YOUR CFA TEAM\n"
            f"  Ritu Bahl — Executive Director — ritu@computingforall.org\n"
            f"  Gary — Technical Lead — gary@computingforall.org\n\n"
            f"NEXT STEPS\n"
            f"  1. Accept the SharePoint invitation email you will receive shortly\n"
            f"  2. Open your client portal and review the project plan\n"
            f"  3. We will schedule a kickoff call within the next 5 business days\n\n"
            f"Reply to this email any time — we are excited to get started.\n\n"
            f"— The CFA Team\n"
            f"Computing for All  |  computingforall.org"
        )
        from mailer import send_email  # type: ignore
        welcome_sent = send_email(inquiry['email'], welcome_subject, welcome_body)
        # Also cc internal team
        notify_internal(
            subject=f"Engagement activated: {inquiry['organization_name']}",
            body=(
                f"A new consulting engagement is active.\n\n"
                f"Organization: {inquiry['organization_name']}\n"
                f"Contact:      {inquiry['contact_name']} <{inquiry['email']}>\n"
                f"Engagement:   {engagement_id}\n"
                f"Budget:       ${budget:,}\n"
                f"SharePoint:   {sharepoint_url}\n"
                f"Portal:       {portal_url}\n"
                f"SP invite:    {'sent' if sharepoint_invite.get('ok') else 'FAILED - ' + str(sharepoint_invite.get('error'))}\n"
                f"Welcome:      {'sent' if welcome_sent.get('sent') else 'logged (' + str(welcome_sent.get('reason')) + ')'}\n"
            ),
        )
    except Exception as e:
        print(f"[CONVERT] Welcome email exception: {type(e).__name__}: {e}")

    # Persist timestamp if welcome email actually went out
    if welcome_sent.get("sent"):
        try:
            conn2 = psycopg2.connect(**PG_CONFIG)
            cur2 = conn2.cursor()
            cur2.execute(
                "UPDATE consulting_engagements SET welcome_email_sent_at = NOW() WHERE id = %s",
                (engagement_id,),
            )
            conn2.commit()
            conn2.close()
        except Exception:
            pass

    return {
        "success": True,
        "engagement_id": engagement_id,
        "client_access_token": client_access_token,
        "client_portal_url": f"/coalition/client?token={client_access_token}",
        "client_portal_url_absolute": portal_url,
        "sharepoint_workspace_url": sharepoint_url,
        "sharepoint_invite": {
            "ok": sharepoint_invite.get("ok", False),
            "error": sharepoint_invite.get("error"),
            "folder_path": sharepoint_invite.get("folder_path"),
        },
        "welcome_email": {
            "sent": welcome_sent.get("sent", False),
            "reason": welcome_sent.get("reason"),
            "to": inquiry['email'],
        },
        "next_steps": [
            "Client receives SharePoint invitation email from Microsoft",
            "Client receives welcome email from CFA with portal link",
            "Schedule kickoff meeting with client",
            "Populate milestones, deliverables, and team in the engagement",
        ],
    }


class NewUpdate(BaseModel):
    author: str
    author_email: str | None = None
    update_type: str = "progress"  # progress | kickoff | milestone | delivery | note
    title: str
    body: str
    is_client_visible: bool = True
    post_to_teams: bool = False


@app.post("/api/consulting/engagement/{engagement_id}/updates")
def post_engagement_update(engagement_id: str, update: NewUpdate):
    """Post a new engagement update (internal team -> client activity feed).

    If post_to_teams=true, also posts an Adaptive Card to the Teams channel
    via Power Automate webhook. Teams failure never blocks the DB save.
    """
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    # Verify engagement exists
    cur.execute("SELECT id, organization_name, contact_email, client_access_token FROM consulting_engagements WHERE id = %s", (engagement_id,))
    eng = cur.fetchone()
    if not eng:
        conn.close()
        raise HTTPException(status_code=404, detail="Engagement not found")

    eng_id, org_name, contact_email, client_token = eng

    cur.execute("""
        INSERT INTO engagement_updates
          (engagement_id, author, author_email, update_type, title, body, is_client_visible)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, update_date
    """, (
        engagement_id,
        update.author,
        update.author_email,
        update.update_type,
        update.title,
        update.body,
        update.is_client_visible,
    ))
    new_id, update_date = cur.fetchone()
    # Bump engagement.updated_at so the client portal reflects activity
    cur.execute("UPDATE consulting_engagements SET updated_at = NOW() WHERE id = %s", (engagement_id,))
    conn.commit()
    conn.close()

    # Post to Teams channel (best-effort — never blocks)
    teams_result = None
    if update.post_to_teams:
        try:
            from agents.graph.teams import post_engagement_update_to_teams
            portal_url = f"http://localhost:3000/coalition/client?token={client_token or engagement_id}"
            teams_result = post_engagement_update_to_teams(
                title=update.title,
                body=update.body,
                update_type=update.update_type,
                engagement_name=org_name,
                portal_url=portal_url,
            )
        except Exception as e:
            print(f"[WARN] Teams post failed: {type(e).__name__}: {e}")
            teams_result = {"ok": False, "error": str(e)}

    return {
        "success": True,
        "id": new_id,
        "engagement_id": engagement_id,
        "update_date": update_date.isoformat() if update_date else None,
        "teams": teams_result,
    }


# =================================================================
# BD COMMAND CENTER API — Jason's dashboard endpoints
# =================================================================

@app.get("/api/consulting/bd/priorities")
def bd_priorities():
    """Today's priorities — warm signals + new Hot companies."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT id, company_name, contact_name, contact_title, signal_type,
                   signal_detail, priority, detected_at, content_id
            FROM warm_signals
            WHERE alert_sent = TRUE AND converted_to_conversation = FALSE
            ORDER BY detected_at DESC LIMIT 5
        """)
        signals = [dict(r) for r in cur.fetchall()]

        cur.execute("""
            SELECT DISTINCT ON (company_domain)
                   company_name, company_domain, confidence, scoring_rationale,
                   recommended_buyer, tier_assigned_at
            FROM company_scores
            WHERE tier = 'Hot'
              AND tier_assigned_at > NOW() - INTERVAL '48 hours'
            ORDER BY company_domain, tier_assigned_at DESC
        """)
        new_hot = [dict(r) for r in cur.fetchall()]

        for r in signals + new_hot:
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.isoformat()

        return {"signals": signals, "new_hot": new_hot}
    finally:
        conn.close()


@app.get("/api/consulting/bd/hot-prospects")
def bd_hot_prospects():
    """All Hot companies with contact and pipeline status."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT DISTINCT ON (cs.company_domain)
                   cs.company_name, cs.company_domain, cs.confidence,
                   cs.recommended_buyer, cs.tier_assigned_at,
                   cs.scoring_rationale,
                   hwc.id as contact_id, hwc.contact_name, hwc.contact_title,
                   hwc.contact_email, hwc.match_confidence, hwc.pipeline_stage,
                   EXTRACT(DAY FROM NOW() - cs.tier_assigned_at)::int as days_since_scored
            FROM company_scores cs
            LEFT JOIN hot_warm_contacts hwc ON hwc.company_domain = cs.company_domain
            WHERE cs.tier = 'Hot'
            ORDER BY cs.company_domain, cs.tier_assigned_at DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.isoformat()
        return {"prospects": rows}
    finally:
        conn.close()


@app.get("/api/consulting/bd/warm-signals")
def bd_warm_signals():
    """All unacted warm signals."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT id, company_name, company_domain, contact_name, contact_title,
                   signal_type, signal_detail, priority, company_tier_at_signal,
                   detected_at
            FROM warm_signals
            WHERE converted_to_conversation = FALSE
            ORDER BY
              CASE priority WHEN 'Immediate' THEN 1 WHEN 'High' THEN 2 ELSE 3 END,
              detected_at DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.isoformat()
        return {"signals": rows}
    finally:
        conn.close()


@app.get("/api/consulting/bd/pipeline")
def bd_pipeline():
    """Pipeline kanban — hot_warm_contacts grouped by stage."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT id, company_name, company_domain, contact_name, contact_title,
                   contact_email, company_tier, match_confidence, pipeline_stage
            FROM hot_warm_contacts
            ORDER BY found_at DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]

        stages = ["Identified", "LinkedIn Sent", "LinkedIn Connected", "Email Sent",
                  "Replied", "Conversation", "Proposal", "Client"]
        grouped = {s: [] for s in stages}
        for r in rows:
            stage = r.get("pipeline_stage") or "Identified"
            if stage not in grouped:
                grouped[stage] = []
            grouped[stage].append(r)
        return {"stages": stages, "pipeline": grouped}
    finally:
        conn.close()


class PipelineStageUpdate(BaseModel):
    stage: str


@app.patch("/api/consulting/bd/pipeline/{contact_id}")
def bd_update_pipeline(contact_id: int, body: PipelineStageUpdate):
    """Update pipeline_stage for a contact."""
    valid = {"Identified", "LinkedIn Sent", "LinkedIn Connected", "Email Sent",
             "Replied", "Conversation", "Proposal", "Client"}
    if body.stage not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid stage. Valid: {sorted(valid)}")

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE hot_warm_contacts SET pipeline_stage = %s WHERE id = %s",
            (body.stage, contact_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Contact not found")
        return {"success": True, "contact_id": contact_id, "stage": body.stage}
    finally:
        conn.close()


class SignalActioned(BaseModel):
    actioned: bool = True


@app.patch("/api/consulting/bd/signals/{signal_id}")
def bd_action_signal(signal_id: int, body: SignalActioned):
    """Mark a warm signal as actioned/converted."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    try:
        cur.execute(
            "UPDATE warm_signals SET converted_to_conversation = %s WHERE id = %s",
            (body.actioned, signal_id),
        )
        conn.commit()
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Signal not found")
        return {"success": True, "signal_id": signal_id, "actioned": body.actioned}
    finally:
        conn.close()


# =================================================================
# Email Drafts — review, edit, approve, send from dashboard
# =================================================================

def _graph_credential():
    """Return Azure ClientSecretCredential for Graph API."""
    from azure.identity import ClientSecretCredential
    return ClientSecretCredential(
        tenant_id=os.getenv("GRAPH_TENANT_ID", os.getenv("AZURE_TENANT_ID", "")),
        client_id=os.getenv("GRAPH_CLIENT_ID", os.getenv("AZURE_CLIENT_ID", "")),
        client_secret=os.getenv("GRAPH_CLIENT_SECRET", os.getenv("AZURE_CLIENT_SECRET", "")),
    )


def _graph_headers():
    cred = _graph_credential()
    token = cred.get_token("https://graph.microsoft.com/.default")
    return {
        "Authorization": f"Bearer {token.token}",
        "Content-Type": "application/json",
    }


def _sender_user_id(sender_email: str) -> str:
    """Map sender email to Graph user ID."""
    if sender_email == "ritu@computinforall.org":
        return "be5fe791-2674-4547-bc8e-eabc67917369"
    return sender_email


GRAPH_BASE = "https://graph.microsoft.com/v1.0"


@app.get("/api/consulting/bd/email-drafts")
def bd_email_drafts():
    """List all email sequences awaiting review."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT id, contact_id, content_id, company_domain, company_name,
                   contact_name, contact_email, sender, sender_email,
                   subject_line, touch_1_body, touch_2_body, touch_3_body,
                   touch_1_message_id, sequence_status, created_at
            FROM email_sequences
            WHERE sequence_status = 'pending_review'
            ORDER BY created_at DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.isoformat()
        return {"drafts": rows}
    finally:
        conn.close()


class EmailDraftUpdate(BaseModel):
    subject_line: Optional[str] = None
    touch_1_body: Optional[str] = None
    touch_2_body: Optional[str] = None
    touch_3_body: Optional[str] = None


@app.patch("/api/consulting/bd/email-drafts/{draft_id}")
def bd_update_email_draft(draft_id: int, body: EmailDraftUpdate):
    """Edit subject or body of an email draft. Also updates the Outlook draft."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM email_sequences WHERE id = %s", (draft_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Draft not found")
        if row["sequence_status"] != "pending_review":
            raise HTTPException(status_code=400, detail=f"Cannot edit sequence in status '{row['sequence_status']}'")

        # Build SQL update
        updates = []
        params = []
        for field in ["subject_line", "touch_1_body", "touch_2_body", "touch_3_body"]:
            value = getattr(body, field)
            if value is not None:
                updates.append(f"{field} = %s")
                params.append(value)

        if updates:
            params.append(draft_id)
            cur.execute(f"UPDATE email_sequences SET {', '.join(updates)} WHERE id = %s", params)
            conn.commit()

        # Sync changes to the Outlook draft via Graph API
        if row.get("touch_1_message_id") and (body.subject_line or body.touch_1_body):
            try:
                import requests as http_req
                user_id = _sender_user_id(row["sender_email"])
                headers = _graph_headers()
                patch_body = {}
                if body.subject_line:
                    patch_body["subject"] = body.subject_line
                if body.touch_1_body:
                    patch_body["body"] = {"contentType": "Text", "content": body.touch_1_body}
                if patch_body:
                    r = http_req.patch(
                        f"{GRAPH_BASE}/users/{user_id}/messages/{row['touch_1_message_id']}",
                        headers=headers,
                        json=patch_body,
                        timeout=15,
                    )
                    if r.status_code not in (200, 204):
                        print(f"[GRAPH] Draft update warning: {r.status_code} {r.text[:200]}")
            except Exception as e:
                print(f"[GRAPH] Draft sync error: {e}")

        return {"success": True, "draft_id": draft_id}
    finally:
        conn.close()


class ApprovalBody(BaseModel):
    approved_by: str = "ritu"


@app.post("/api/consulting/bd/email-drafts/{draft_id}/approve")
def bd_approve_email_draft(draft_id: int, body: ApprovalBody):
    """Approve and send the Touch 1 draft. Sequence becomes 'active'.
    Touch 2 and Touch 3 will auto-send on schedule via process_sequence_touches.
    """
    import requests as http_req

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM email_sequences WHERE id = %s", (draft_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Draft not found")
        if row["sequence_status"] != "pending_review":
            raise HTTPException(status_code=400, detail=f"Cannot approve sequence in status '{row['sequence_status']}'")

        sender_email = row["sender_email"]
        user_id = _sender_user_id(sender_email)
        headers = _graph_headers()

        # Try to send the existing draft first if we have a message_id
        sent = False
        if row.get("touch_1_message_id"):
            try:
                r = http_req.post(
                    f"{GRAPH_BASE}/users/{user_id}/messages/{row['touch_1_message_id']}/send",
                    headers=headers,
                    timeout=30,
                )
                if r.status_code in (200, 202):
                    sent = True
                    print(f"[GRAPH] Sent existing draft {row['touch_1_message_id'][:30]}...")
                else:
                    print(f"[GRAPH] Send-existing-draft failed: {r.status_code} {r.text[:200]}")
            except Exception as e:
                print(f"[GRAPH] Send-existing-draft error: {e}")

        # Fallback: send fresh via /sendMail (works even if draft doesn't exist)
        if not sent:
            try:
                payload = {
                    "message": {
                        "subject": row["subject_line"],
                        "body": {"contentType": "Text", "content": row["touch_1_body"]},
                        "toRecipients": [
                            {"emailAddress": {"name": row["contact_name"], "address": row["contact_email"]}}
                        ],
                    },
                    "saveToSentItems": True,
                }
                r = http_req.post(
                    f"{GRAPH_BASE}/users/{user_id}/sendMail",
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                if r.status_code == 202:
                    sent = True
                    print(f"[GRAPH] Sent fresh email -> {row['contact_email']}")
                else:
                    raise HTTPException(
                        status_code=502,
                        detail=f"Graph send failed: {r.status_code} {r.text[:200]}",
                    )
            except HTTPException:
                raise
            except Exception as e:
                raise HTTPException(status_code=502, detail=f"Graph send error: {e}")

        # Mark sequence active and record timestamps
        cur.execute(
            """UPDATE email_sequences
               SET sequence_status = 'active',
                   touch_1_sent_at = NOW(),
                   approved_by = %s,
                   approved_at = NOW()
               WHERE id = %s""",
            (body.approved_by, draft_id),
        )
        conn.commit()

        return {
            "success": True,
            "draft_id": draft_id,
            "company_name": row["company_name"],
            "contact_name": row["contact_name"],
            "sent_to": row["contact_email"],
            "next_touch": "Touch 2 will auto-send in 5 days if no reply",
        }
    finally:
        conn.close()


@app.delete("/api/consulting/bd/email-drafts/{draft_id}")
def bd_reject_email_draft(draft_id: int):
    """Reject a draft — deletes the Outlook draft and the sequence row."""
    import requests as http_req

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("SELECT * FROM email_sequences WHERE id = %s", (draft_id,))
        row = cur.fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Draft not found")

        # Delete the Outlook draft if it exists
        if row.get("touch_1_message_id"):
            try:
                user_id = _sender_user_id(row["sender_email"])
                headers = _graph_headers()
                r = http_req.delete(
                    f"{GRAPH_BASE}/users/{user_id}/messages/{row['touch_1_message_id']}",
                    headers=headers,
                    timeout=15,
                )
                if r.status_code not in (200, 204):
                    print(f"[GRAPH] Draft delete warning: {r.status_code}")
            except Exception as e:
                print(f"[GRAPH] Draft delete error: {e}")

        # Delete from database
        cur.execute("DELETE FROM email_sequences WHERE id = %s", (draft_id,))
        conn.commit()

        return {"success": True, "draft_id": draft_id, "rejected": True}
    finally:
        conn.close()


# =================================================================
# MARKETING COMMAND CENTER API — Jessica's dashboard endpoints
# =================================================================

@app.get("/api/consulting/marketing/performance")
def marketing_performance():
    """Content performance metrics — signals per piece."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT cs.id, cs.title, cs.author, cs.vertical, cs.topic_tags,
                   cs.status, cs.distributed_at, cs.submitted_at,
                   COALESCE(dl.contacts_reached, 0) as contacts_reached,
                   COALESCE(ws.signal_count, 0) as signals_generated
            FROM content_submissions cs
            LEFT JOIN (
                SELECT content_id, COUNT(*) as contacts_reached
                FROM distribution_log GROUP BY content_id
            ) dl ON cs.id = dl.content_id
            LEFT JOIN (
                SELECT content_id, COUNT(*) as signal_count
                FROM warm_signals GROUP BY content_id
            ) ws ON cs.id = ws.content_id
            ORDER BY cs.submitted_at DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            contacts = r.get("contacts_reached") or 0
            signals = r.get("signals_generated") or 0
            r["signal_rate_pct"] = round(signals / contacts * 100, 1) if contacts > 0 else 0
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.isoformat()
        return {"content": rows}
    finally:
        conn.close()


@app.get("/api/consulting/marketing/gaps")
def marketing_gaps():
    """Content gap analysis from company_scores recommended_content."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT DISTINCT ON (company_domain)
                   company_name, company_domain, tier, recommended_content
            FROM company_scores
            WHERE tier IN ('Hot', 'Warm')
              AND recommended_content IS NOT NULL
              AND recommended_content != ''
            ORDER BY company_domain, tier_assigned_at DESC
        """)
        recs = [dict(r) for r in cur.fetchall()]

        cur.execute("SELECT id, title, topic_tags FROM content_submissions")
        existing = [dict(r) for r in cur.fetchall()]
        existing_tags = set()
        for c in existing:
            for tag in (c.get("topic_tags") or []):
                existing_tags.add(tag.lower())

        gaps = {}
        for r in recs:
            topic = (r.get("recommended_content") or "")[:120]
            if topic not in gaps:
                gaps[topic] = {"topic": topic, "companies": [], "tiers": []}
            gaps[topic]["companies"].append(r["company_name"])
            gaps[topic]["tiers"].append(r["tier"])

        gap_list = []
        for topic, data in gaps.items():
            count = len(data["companies"])
            topic_words = set(topic.lower().split())
            has_coverage = bool(topic_words & existing_tags)
            if count >= 3 and not has_coverage:
                priority = "high"
            elif count >= 1 and not has_coverage:
                priority = "medium"
            else:
                priority = "covered"
            gap_list.append({
                "topic": topic,
                "company_count": count,
                "companies": data["companies"][:5],
                "tiers": data["tiers"],
                "has_coverage": has_coverage,
                "priority": priority,
            })

        gap_list.sort(key=lambda x: (-x["company_count"], x["has_coverage"]))
        return {"gaps": gap_list}
    finally:
        conn.close()


@app.get("/api/consulting/marketing/calendar")
def marketing_calendar():
    """Content calendar — all content_submissions with status."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT cs.*, COALESCE(ws.signal_count, 0) as signals
            FROM content_submissions cs
            LEFT JOIN (
                SELECT content_id, COUNT(*) as signal_count
                FROM warm_signals GROUP BY content_id
            ) ws ON cs.id = ws.content_id
            ORDER BY cs.submitted_at DESC
        """)
        rows = [dict(r) for r in cur.fetchall()]
        for r in rows:
            for k, v in r.items():
                if isinstance(v, datetime):
                    r[k] = v.isoformat()
        return {"calendar": rows}
    finally:
        conn.close()


class ContentSubmission(BaseModel):
    title: str
    url: Optional[str] = None
    author: str
    vertical: Optional[str] = "general"
    topic_tags: Optional[list[str]] = None
    funnel_stage: Optional[str] = "awareness"
    format: Optional[str] = "long-form"
    distribute_immediately: Optional[bool] = True
    schedule_datetime: Optional[str] = None


@app.post("/api/consulting/marketing/submit-content")
def marketing_submit(body: ContentSubmission):
    """Submit a new content piece to the distribution pipeline."""
    distribution_timing = None
    if not body.distribute_immediately and body.schedule_datetime:
        distribution_timing = body.schedule_datetime

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    try:
        cur.execute(
            """INSERT INTO content_submissions
               (title, url, author, vertical, topic_tags, funnel_stage, format,
                distribution_timing, status, deployment_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
               RETURNING id""",
            (
                body.title, body.url, body.author, body.vertical,
                body.topic_tags or [], body.funnel_stage, body.format,
                distribution_timing, "pending", "waifinder-national",
            ),
        )
        new_id = cur.fetchone()[0]
        conn.commit()
        return {
            "id": new_id,
            "status": "pending",
            "estimated_distribution": "next 15-minute Agent 13 cycle"
                                      if body.distribute_immediately
                                      else body.schedule_datetime,
        }
    finally:
        conn.close()


@app.get("/api/consulting/marketing/leads-summary")
def marketing_leads_summary():
    """Lead capture metrics — this week vs last week. Endpoint name avoids collision with existing /api/marketing/leads."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    try:
        cur.execute("""
            SELECT COUNT(*) as total FROM marketing_leads
            WHERE created_at > NOW() - INTERVAL '7 days'
        """)
        this_week = cur.fetchone()["total"]

        cur.execute("""
            SELECT COUNT(*) as total FROM marketing_leads
            WHERE created_at BETWEEN NOW() - INTERVAL '14 days'
                                 AND NOW() - INTERVAL '7 days'
        """)
        last_week = cur.fetchone()["total"]

        cur.execute("""
            SELECT content_title, content_type, COUNT(*) as leads
            FROM marketing_leads
            WHERE created_at > NOW() - INTERVAL '7 days'
            GROUP BY content_title, content_type
            ORDER BY leads DESC LIMIT 10
        """)
        by_content = [dict(r) for r in cur.fetchall()]

        return {
            "this_week": this_week,
            "last_week": last_week,
            "delta_pct": round((this_week - last_week) / last_week * 100, 1) if last_week else 0,
            "by_content": by_content,
        }
    finally:
        conn.close()


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "consulting-api", "port": 8003}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
