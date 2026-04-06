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


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "marketing-api", "port": 8008}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8008)
