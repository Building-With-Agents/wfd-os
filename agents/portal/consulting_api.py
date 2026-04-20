"""
Consulting Intake API — Handles project inquiry form submissions.
Run: uvicorn agents.portal.consulting_api:app --reload --port 8003
"""
import asyncio, traceback
from datetime import datetime, timezone
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import psycopg2.extras

# wfdos_common.config auto-loads the repo .env via python-dotenv find_dotenv —
# no hardcoded path needed. Pre-#27 this file had sys.path.insert hacks; the
# monorepo root pyproject.toml (#27) now exposes `agents.*` as a namespace
# package, so direct imports resolve without them.

# Email helper — Microsoft Graph backend. Import via full package path so it
# doesn't shadow Python's stdlib `email` package.
from wfdos_common.auth import SessionMiddleware, build_auth_router
from wfdos_common.config import settings
from wfdos_common.email import notify_internal, send_email
from wfdos_common.errors import (
    NotFoundError,
    ServiceUnavailableError,
    ValidationFailure,
    install_error_handlers,
)
from wfdos_common.logging import RequestContextMiddleware, configure as configure_logging, get_logger

# Configure structured logging at module import (idempotent).
configure_logging(service_name="consulting-api")
log = get_logger(__name__)

# Scoping Agent pipeline (lazy-imported inside the trigger to avoid blocking module load
# if Graph creds or Anthropic SDK aren't available on startup).

app = FastAPI(title="Waifinder Consulting API", version="0.1.0")

app.add_middleware(RequestContextMiddleware)
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.auth.secret_key,
    cookie_name=settings.auth.cookie_name,
    max_age_seconds=settings.auth.session_ttl_seconds,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3003", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# #29 — structured error envelope on every 4xx/5xx.
install_error_handlers(app)

# #24 — magic-link auth routes live on this service; other services
# just parse the cookie via SessionMiddleware.
app.include_router(build_auth_router())


def get_conn():
    """Raw DBAPI connection from the wfdos_common.db engine pool (#22c).

    Returns a psycopg2-compatible connection; conn.close() returns it
    to the shared pool instead of actually closing the socket.
    """
    from wfdos_common.db import get_engine
    return get_engine().raw_connection()


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
    conn = get_conn()
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
        log.warning("email.submitter_confirmation.failed", error_type=type(e).__name__, error=str(e))

    # 2. Internal notification email to Ritu
    try:
        subject, html_body = render_internal_notification(inquiry, reference_number)
        notify_email = settings.email.notify
        send_email(notify_email, subject, html_body, html=True)
    except Exception as e:
        log.warning("email.internal_notification.failed", error_type=type(e).__name__, error=str(e))

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
            log.info("apollo.contact.created", email=inquiry.email, contact_id=apollo_contact_id)

            # Determine suggested sequence based on project type / org name
            project_lower = (inquiry.project_area or "").lower() + " " + (inquiry.organization_name or "").lower()
            if "workforce" in project_lower:
                apollo_sequence_suggested = "TX Workforce Board Sequence" if "texas" in project_lower or "tx" in project_lower else "WA Employer Sequence"
            elif "healthcare" in project_lower:
                apollo_sequence_suggested = "WA Employer Sequence"
            else:
                apollo_sequence_suggested = "TX Professional Services Sequence"

            # Save Apollo data to the inquiry row
            conn3 = get_conn()
            cur3 = conn3.cursor()
            cur3.execute(
                "UPDATE project_inquiries SET apollo_contact_id = %s, apollo_sequence_suggested = %s WHERE id = %s",
                (apollo_contact_id, apollo_sequence_suggested, inquiry_id),
            )
            conn3.commit()
            conn3.close()
            log.info("apollo.sequence.suggested", sequence=apollo_sequence_suggested, auto_enrolled=False)
        else:
            log.warning("apollo.contact.create_failed", error=apollo_result.get("error"))
    except Exception as e:
        log.warning("apollo.integration.exception", error_type=type(e).__name__, error=str(e), exc_info=True)

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
    conn = get_conn()
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
        raise NotFoundError("engagement")
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
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        "SELECT id, organization_name, sharepoint_workspace_url FROM consulting_engagements "
        "WHERE client_access_token = %s OR id = %s LIMIT 1",
        (client_id, client_id),
    )
    eng = cur.fetchone()
    conn.close()
    if not eng:
        raise NotFoundError("engagement")

    safe_name = _safe_name(eng["organization_name"])
    stored_sp_url = eng.get("sharepoint_workspace_url")

    try:
        from wfdos_common.graph.sharepoint import list_client_documents_sync
        files = list_client_documents_sync(safe_name, recursive=True)
    except Exception as e:
        log.error("sharepoint.list_documents.failed", error_type=type(e).__name__, error=str(e), exc_info=True)
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
    conn = get_conn()
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
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM project_inquiries WHERE id = %s", (inquiry_id,))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise NotFoundError("inquiry")
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
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM project_inquiries WHERE id = %s", (inquiry_id,))
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def _set_inquiry_status(inquiry_id: str, status: str, note_append: str | None = None) -> None:
    conn = get_conn()
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
    from wfdos_common.models.scoping import ScopingRequest, Contact, Organization

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
    log.info("scoping.pipeline.start", inquiry_id=inquiry_id)
    try:
        inq = _fetch_inquiry(inquiry_id)
        if not inq:
            log.warning("scoping.pipeline.inquiry_not_found", inquiry_id=inquiry_id)
            return

        from agents.scoping.pipeline import run_precall_pipeline
        req = _inquiry_to_scoping_request(inq)
        log.info(
            "scoping.pipeline.request_built",
            organization=req.organization.name,
            contact=req.contact.full_name,
            contact_email=req.contact.email,
            safe_name=req.organization.safe_name,
        )

        asyncio.run(run_precall_pipeline(req))

        success_note = (
            f"[{datetime.now(timezone.utc).isoformat(timespec='seconds')}] "
            f"Scoping Agent pipeline completed successfully. "
            f"SharePoint workspace at /sites/wAIFinder/Clients/{req.organization.safe_name}/"
        )
        _set_inquiry_status(inquiry_id, "scoped", note_append=success_note)
        log.info("scoping.pipeline.complete", inquiry_id=inquiry_id, status="scoped")

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
        log.error(
            "scoping.pipeline.failed",
            inquiry_id=inquiry_id,
            error_type=type(e).__name__,
            error=str(e),
            traceback=tb,
            exc_info=True,
        )
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
        raise ValidationFailure(f"Invalid status. Must be one of {VALID_STATUSES}")

    # Fetch current to detect transition
    current = _fetch_inquiry(inquiry_id)
    if not current:
        raise NotFoundError("inquiry")
    prev_status = current.get("status")

    conn = get_conn()
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
        raise NotFoundError("inquiry")

    scoping_triggered = False
    if update.status == "scoping" and prev_status != "scoping":
        # Fire pipeline as a background task — returns immediately.
        background_tasks.add_task(_run_scoping_pipeline_sync, inquiry_id)
        scoping_triggered = True
        log.info(
            "scoping.pipeline.queued",
            inquiry_id=inquiry_id,
            prev_status=prev_status,
            new_status="scoping",
        )

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
    return settings.platform.portal_base_url.rstrip("/")


@app.delete("/api/consulting/inquiry/{inquiry_id}")
def delete_inquiry(inquiry_id: str):
    """Hard-delete a single inquiry. Returns the deleted row's organization
    name so the client can show a friendly toast."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM project_inquiries WHERE id = %s RETURNING organization_name, reference_number",
        (inquiry_id,),
    )
    row = cur.fetchone()
    conn.commit()
    conn.close()
    if not row:
        raise NotFoundError("inquiry")
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
    conn = get_conn()
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

    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Get inquiry
    cur.execute("SELECT * FROM project_inquiries WHERE id = %s", (inquiry_id,))
    inquiry = cur.fetchone()
    if not inquiry:
        conn.close()
        raise NotFoundError("inquiry")
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
        from wfdos_common.graph.invitations import invite_to_client_folder
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
        log.warning("convert.sharepoint_invite.failed", error_type=type(e).__name__, error=str(e))
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
        log.warning("convert.welcome_email.failed", error_type=type(e).__name__, error=str(e))

    # Persist timestamp if welcome email actually went out
    if welcome_sent.get("sent"):
        try:
            conn2 = get_conn()
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
    conn = get_conn()
    cur = conn.cursor()
    # Verify engagement exists
    cur.execute("SELECT id, organization_name, contact_email, client_access_token FROM consulting_engagements WHERE id = %s", (engagement_id,))
    eng = cur.fetchone()
    if not eng:
        conn.close()
        raise NotFoundError("engagement")

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
            from wfdos_common.graph.teams import post_engagement_update_to_teams
            portal_url = f"http://localhost:3000/coalition/client?token={client_token or engagement_id}"
            teams_result = post_engagement_update_to_teams(
                title=update.title,
                body=update.body,
                update_type=update.update_type,
                engagement_name=org_name,
                portal_url=portal_url,
            )
        except Exception as e:
            log.warning("teams.post.failed", error_type=type(e).__name__, error=str(e))
            teams_result = {"ok": False, "error": str(e)}

    return {
        "success": True,
        "id": new_id,
        "engagement_id": engagement_id,
        "update_date": update_date.isoformat() if update_date else None,
        "teams": teams_result,
    }


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "consulting-api", "port": 8003}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
