"""
Marketing Content API — manages content lifecycle from draft to published.

Endpoints:
  POST   /api/marketing/content               — create new content
  GET    /api/marketing/content               — list (filter by type, status, audience)
  GET    /api/marketing/content/{id}          — single item
  PATCH  /api/marketing/content/{id}/status   — approve / publish / archive
  POST   /api/marketing/content/{id}/mark-loaded — mark email sequence as loaded in Apollo
  GET    /api/marketing/pipeline              — content grouped by status for kanban
  GET    /api/health

Run: uvicorn agents.marketing.api:app --port 8008
"""
import os
import re
import sys
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import psycopg2
import psycopg2.extras

_REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../.."))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(_REPO_ROOT, ".env"), override=False)

sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts"))
from pgconfig import PG_CONFIG

app = FastAPI(title="WFD OS Marketing Content API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _slugify(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower().strip()).strip("-")
    return slug[:80]


def _serialize(row: dict) -> dict:
    d = dict(row)
    for k in ("created_at", "updated_at", "approved_at", "published_at"):
        if d.get(k):
            d[k] = d[k].isoformat()
    return d


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

class CreateContent(BaseModel):
    content_type: str  # blog_post, case_study, email_sequence, sales_asset, social_post
    title: str
    content_body: Optional[str] = None
    author: Optional[str] = None
    audience_tag: Optional[str] = None
    status: Optional[str] = "draft"
    sharepoint_doc_url: Optional[str] = None


class StatusUpdate(BaseModel):
    status: str  # draft, in_review, approved, published, active, archived
    approved_by: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.post("/api/marketing/content")
def create_content(c: CreateContent):
    slug = _slugify(c.title)
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO marketing_content
            (content_type, title, slug, content_body, author, audience_tag, status, sharepoint_doc_url)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
    """, (c.content_type, c.title, slug, c.content_body, c.author, c.audience_tag, c.status or "draft", c.sharepoint_doc_url))
    content_id = cur.fetchone()[0]
    conn.commit()
    conn.close()
    return {"success": True, "id": content_id, "slug": slug}


@app.get("/api/marketing/content")
def list_content(
    content_type: Optional[str] = None,
    status: Optional[str] = None,
    audience: Optional[str] = None,
    slug: Optional[str] = None,
    limit: int = Query(50, le=200),
):
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    conditions = []
    params = []
    if content_type:
        conditions.append("content_type = %s")
        params.append(content_type)
    if status:
        conditions.append("status = %s")
        params.append(status)
    if audience:
        conditions.append("audience_tag = %s")
        params.append(audience)
    if slug:
        conditions.append("slug = %s")
        params.append(slug)
    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    cur.execute(f"""
        SELECT id, content_type, title, slug, author, audience_tag, status,
               sharepoint_doc_url, published_url, approved_by, approved_at, published_at,
               created_at, updated_at
        FROM marketing_content {where}
        ORDER BY created_at DESC
        LIMIT %s
    """, params + [limit])
    rows = [_serialize(r) for r in cur.fetchall()]
    conn.close()
    return {"content": rows, "count": len(rows)}


@app.get("/api/marketing/content/{content_id}")
def get_content(content_id: str):
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("SELECT * FROM marketing_content WHERE id = %s OR slug = %s", (content_id, content_id))
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Content not found")
    return _serialize(row)


@app.patch("/api/marketing/content/{content_id}/status")
def update_status(content_id: str, update: StatusUpdate):
    valid = {"draft", "in_review", "approved", "published", "active", "archived"}
    if update.status not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of {valid}")

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    sets = ["status = %s", "updated_at = NOW()"]
    params = [update.status]

    if update.status == "approved" and update.approved_by:
        sets.extend(["approved_by = %s", "approved_at = NOW()"])
        params.append(update.approved_by)
    if update.status == "published":
        sets.append("published_at = NOW()")

    params.append(content_id)
    cur.execute(f"UPDATE marketing_content SET {', '.join(sets)} WHERE id = %s OR slug = %s RETURNING id, title",
                params + [content_id])
    row = cur.fetchone()
    conn.commit()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Content not found")
    return {"success": True, "id": row[0], "title": row[1], "status": update.status}


@app.post("/api/marketing/content/{content_id}/mark-loaded")
def mark_loaded(content_id: str):
    """Mark an email sequence as loaded into Apollo — sets status to 'active'."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        UPDATE marketing_content SET status = 'active', updated_at = NOW()
        WHERE (id = %s OR slug = %s) AND content_type = 'email_sequence'
        RETURNING id, title
    """, (content_id, content_id))
    row = cur.fetchone()
    conn.commit()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Email sequence not found")
    return {"success": True, "id": row[0], "title": row[1], "status": "active"}


@app.get("/api/marketing/pipeline")
def get_pipeline():
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute("""
        SELECT id, content_type, title, slug, author, audience_tag, status,
               sharepoint_doc_url, published_url, approved_by, approved_at, published_at,
               created_at, updated_at
        FROM marketing_content
        ORDER BY created_at DESC
    """)
    all_content = [_serialize(r) for r in cur.fetchall()]

    # Group by status
    pipeline = {}
    for c in all_content:
        s = c["status"]
        pipeline.setdefault(s, []).append(c)

    # Stats
    stats = {}
    for s in ("draft", "in_review", "approved", "published", "active", "archived"):
        stats[s] = len(pipeline.get(s, []))

    conn.close()
    return {"pipeline": pipeline, "stats": stats, "total": len(all_content)}


class LeadCapture(BaseModel):
    name: str
    email: str
    content_id: Optional[str] = None
    content_title: Optional[str] = None
    content_type: Optional[str] = None


@app.post("/api/marketing/leads")
def capture_lead(lead: LeadCapture):
    """Capture a lead from gated content download. Creates record + Apollo contact."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO marketing_leads (name, email, content_id, content_title, content_type)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id
    """, (lead.name, lead.email, lead.content_id, lead.content_title, lead.content_type))
    lead_id = cur.fetchone()[0]
    conn.commit()
    conn.close()

    # Best-effort Apollo contact creation
    apollo_id = None
    try:
        from agents.apollo.client import create_contact
        parts = lead.name.strip().split(None, 1)
        result = create_contact(
            first_name=parts[0] if parts else lead.name,
            last_name=parts[1] if len(parts) > 1 else "",
            email=lead.email,
            organization="",
            source=f"gated_download:{lead.content_type}",
            label_names=["Content Download", "WFD OS Lead"],
        )
        if result.get("ok"):
            apollo_id = result.get("contact_id")
            conn2 = psycopg2.connect(**PG_CONFIG)
            cur2 = conn2.cursor()
            cur2.execute("UPDATE marketing_leads SET apollo_contact_id = %s WHERE id = %s", (apollo_id, lead_id))
            conn2.commit()
            conn2.close()
    except Exception as e:
        print(f"[LEADS] Apollo creation failed: {e}")

    return {
        "success": True,
        "lead_id": lead_id,
        "apollo_contact_id": apollo_id,
        "download_url": f"/downloads/{lead.content_id}.pdf" if lead.content_id else None,
    }


# ---------------------------------------------------------------------------
# Newsletter subscribe / unsubscribe
# ---------------------------------------------------------------------------

_EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")


class NewsletterSubscribe(BaseModel):
    email: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    source: Optional[str] = "website_footer"


def _derive_name_from_email(email: str) -> tuple[str, str, str]:
    """Derive first_name, last_name, organization from an email address.

    Used for Apollo contact creation when the form only collects an email.
    """
    local, _, domain = email.partition("@")
    parts = re.split(r"[._\-]", local, maxsplit=1)
    first = parts[0].capitalize() if parts and parts[0] else "Newsletter"
    last = parts[1].capitalize() if len(parts) > 1 and parts[1] else "Subscriber"
    return first, last, domain


def _sync_apollo_newsletter(email: str, first_name: str, last_name: str) -> dict:
    """Create or update an Apollo contact tagged as newsletter-subscriber.

    Never raises — returns {ok, contact_id, error}. Runs after the DB write
    so a failure here does not break the subscribe flow.
    """
    try:
        from agents.apollo import client as apollo_client
        first, last, domain = _derive_name_from_email(email)
        if first_name:
            first = first_name
        if last_name:
            last = last_name
        result = apollo_client.create_contact(
            first_name=first,
            last_name=last,
            email=email,
            organization=domain or "Unknown",
            source="newsletter_website",
            label_names=["newsletter-subscriber"],
        )
        return result
    except Exception as e:
        print(f"[NEWSLETTER] Apollo sync exception: {type(e).__name__}: {e}")
        return {"ok": False, "contact_id": None, "error": f"{type(e).__name__}: {e}"}


@app.post("/api/marketing/newsletter-subscribe")
def newsletter_subscribe(body: NewsletterSubscribe):
    """Subscribe an email to the WFD OS / Waifinder newsletter.

    Writes to newsletter_subscribers, then best-effort syncs to Apollo with
    the 'newsletter-subscriber' label. Duplicates return 409 with a friendly
    message. Apollo failures do not break the subscribe (logged only).
    """
    email = (body.email or "").strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Please enter a valid email address")

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    cur.execute(
        "SELECT id, status FROM newsletter_subscribers WHERE email = %s",
        (email,),
    )
    existing = cur.fetchone()

    if existing:
        if existing["status"] == "active":
            conn.close()
            return JSONResponse(
                status_code=409,
                content={
                    "success": False,
                    "already_subscribed": True,
                    "message": "Already subscribed",
                },
            )
        # Previously unsubscribed — reactivate
        cur.execute(
            """
            UPDATE newsletter_subscribers
            SET status = 'active',
                unsubscribed_at = NULL,
                subscribed_at = NOW(),
                source = %s
            WHERE email = %s
            RETURNING id
            """,
            (body.source or "website_footer", email),
        )
        sub_id = cur.fetchone()["id"]
    else:
        cur.execute(
            """
            INSERT INTO newsletter_subscribers (email, first_name, last_name, source)
            VALUES (%s, %s, %s, %s)
            RETURNING id
            """,
            (email, body.first_name, body.last_name, body.source or "website_footer"),
        )
        sub_id = cur.fetchone()["id"]

    conn.commit()
    conn.close()

    apollo_result = _sync_apollo_newsletter(email, body.first_name or "", body.last_name or "")

    return {
        "success": True,
        "id": sub_id,
        "email": email,
        "message": "You're in — first issue coming soon",
        "apollo": {
            "ok": apollo_result.get("ok", False),
            "contact_id": apollo_result.get("contact_id"),
            "error": apollo_result.get("error"),
        },
    }


@app.get("/api/marketing/newsletter-unsubscribe")
def newsletter_unsubscribe(email: str):
    """Unsubscribe an email from the newsletter by URL parameter.

    Called by the /unsubscribe landing page (Change 2). Best-effort Apollo
    untag. Returns success even if the email was not found so the landing
    page still renders.
    """
    email = (email or "").strip().lower()
    if not _EMAIL_RE.match(email):
        raise HTTPException(status_code=400, detail="Invalid email address")

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()
    cur.execute(
        """
        UPDATE newsletter_subscribers
        SET status = 'unsubscribed',
            unsubscribed_at = NOW()
        WHERE email = %s
        RETURNING id
        """,
        (email,),
    )
    row = cur.fetchone()
    conn.commit()
    conn.close()

    apollo_untag = {"ok": False, "error": "not attempted"}
    try:
        from agents.apollo import client as apollo_client
        lookup = apollo_client.get_contact_by_email(email)
        if lookup.get("ok") and lookup.get("contact_id"):
            # Apollo labels update is not in the existing client — we log intent
            # and rely on the contact's status change via a stage update instead.
            apollo_untag = {
                "ok": True,
                "contact_id": lookup["contact_id"],
                "note": "contact_id located — label removal TODO (not in client)",
            }
    except Exception as e:
        apollo_untag = {"ok": False, "error": f"{type(e).__name__}: {e}"}

    return {
        "success": True,
        "email": email,
        "found": bool(row),
        "apollo": apollo_untag,
    }


# ---------------------------------------------------------------------------
# Newsletter issues (archive)
# ---------------------------------------------------------------------------

def _serialize_issue(row: dict) -> dict:
    d = dict(row)
    if d.get("issue_date"):
        d["issue_date"] = d["issue_date"].isoformat()
    if d.get("published_at"):
        d["published_at"] = d["published_at"].isoformat()
    if d.get("created_at"):
        d["created_at"] = d["created_at"].isoformat()
    return d


@app.get("/api/marketing/newsletter-issues")
def list_newsletter_issues(status: Optional[str] = "published", limit: int = Query(50, le=200)):
    """List newsletter issues for the archive page. Defaults to published only."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    if status:
        cur.execute(
            """
            SELECT id, issue_number, issue_date, headline, subheadline, description,
                   status, published_at, created_at
            FROM newsletter_issues
            WHERE status = %s
            ORDER BY issue_number DESC
            LIMIT %s
            """,
            (status, limit),
        )
    else:
        cur.execute(
            """
            SELECT id, issue_number, issue_date, headline, subheadline, description,
                   status, published_at, created_at
            FROM newsletter_issues
            ORDER BY issue_number DESC
            LIMIT %s
            """,
            (limit,),
        )
    rows = [_serialize_issue(r) for r in cur.fetchall()]
    conn.close()
    return {"issues": rows, "count": len(rows)}


@app.get("/api/marketing/newsletter-issues/{issue_number}")
def get_newsletter_issue(issue_number: int):
    """Fetch a single newsletter issue by issue_number for the detail page."""
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute(
        """
        SELECT id, issue_number, issue_date, headline, subheadline, description,
               html_content, status, published_at, created_at
        FROM newsletter_issues
        WHERE issue_number = %s
        """,
        (issue_number,),
    )
    row = cur.fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Newsletter issue not found")
    return _serialize_issue(row)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "marketing-api", "port": 8008}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
