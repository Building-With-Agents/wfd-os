"""Apollo CRM API client.

All functions return structured dicts and never raise — errors are captured
in the return value so callers can log and continue without blocking user flows.

Auth: X-Api-Key header from APOLLO_API_KEY env var.
Base URL: https://api.apollo.io/v1
"""
from __future__ import annotations

import os
import json
import traceback
from typing import Optional

import requests

from wfdos_common.config import settings

APOLLO_BASE = "https://api.apollo.io/v1"


def _api_key() -> str:
    return settings.apollo.api_key


def _headers() -> dict:
    return {
        "X-Api-Key": _api_key(),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


# ---------------------------------------------------------------------------
# 1. Create contact
# ---------------------------------------------------------------------------

def create_contact(
    first_name: str,
    last_name: str,
    email: str,
    organization: str,
    title: str | None = None,
    phone: str | None = None,
    source: str = "wfd_os",
    reference_number: str = "",
    label_names: list[str] | None = None,
) -> dict:
    """Create a new contact in Apollo. Returns {ok, contact_id, error}."""
    if not _api_key():
        return {"ok": False, "contact_id": None, "error": "APOLLO_API_KEY not set"}

    body: dict = {
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "organization_name": organization,
        "label_names": label_names or ["WFD OS Lead"],
    }
    if title:
        body["title"] = title
    if phone:
        body["phone_numbers"] = [{"raw_number": phone}]

    try:
        r = requests.post(
            f"{APOLLO_BASE}/contacts",
            headers=_headers(),
            json=body,
            timeout=15,
        )
        data = r.json()

        if r.status_code in (200, 201):
            contact_id = data.get("contact", {}).get("id")
            print(f"[APOLLO] Contact created: {first_name} {last_name} <{email}> -> {contact_id}")
            return {"ok": True, "contact_id": contact_id, "error": None, "data": data.get("contact", {})}

        # Apollo returns 422 if contact already exists
        if r.status_code == 422:
            # Try to find existing contact
            existing = get_contact_by_email(email)
            if existing.get("ok") and existing.get("contact_id"):
                print(f"[APOLLO] Contact already exists: {email} -> {existing['contact_id']}")
                return {"ok": True, "contact_id": existing["contact_id"], "error": None, "already_existed": True}

        print(f"[APOLLO] Create contact failed: HTTP {r.status_code} {json.dumps(data)[:200]}")
        return {"ok": False, "contact_id": None, "error": f"HTTP {r.status_code}: {str(data)[:200]}"}

    except Exception as e:
        print(f"[APOLLO] Create contact exception: {type(e).__name__}: {e}")
        return {"ok": False, "contact_id": None, "error": f"{type(e).__name__}: {e}"}


# ---------------------------------------------------------------------------
# 2. Get sequences
# ---------------------------------------------------------------------------

def get_sequences() -> dict:
    """Get all email sequences (emailer campaigns) in the account."""
    if not _api_key():
        return {"ok": False, "sequences": [], "error": "APOLLO_API_KEY not set"}

    try:
        r = requests.get(
            f"{APOLLO_BASE}/emailer_campaigns",
            headers=_headers(),
            params={"per_page": 100},
            timeout=15,
        )
        data = r.json()

        if r.status_code == 200:
            campaigns = data.get("emailer_campaigns", [])
            sequences = []
            for c in campaigns:
                sequences.append({
                    "id": c.get("id"),
                    "name": c.get("name"),
                    "active": c.get("active", False),
                    "status": "active" if c.get("active") else "paused",
                    "num_steps": c.get("num_steps", 0),
                    "contact_count": c.get("unique_scheduled", 0) + c.get("unique_delivered", 0),
                    "created_at": c.get("created_at"),
                })
            print(f"[APOLLO] Found {len(sequences)} sequences")
            return {"ok": True, "sequences": sequences, "error": None, "total": len(sequences)}

        print(f"[APOLLO] Get sequences failed: HTTP {r.status_code}")
        return {"ok": False, "sequences": [], "error": f"HTTP {r.status_code}"}

    except Exception as e:
        print(f"[APOLLO] Get sequences exception: {e}")
        return {"ok": False, "sequences": [], "error": str(e)}


# ---------------------------------------------------------------------------
# 3. Enroll in sequence
# ---------------------------------------------------------------------------

def enroll_in_sequence(
    contact_id: str,
    sequence_id: str,
) -> dict:
    """Add a contact to an email sequence."""
    if not _api_key():
        return {"ok": False, "error": "APOLLO_API_KEY not set"}

    try:
        r = requests.post(
            f"{APOLLO_BASE}/emailer_campaigns/{sequence_id}/add_contact_ids",
            headers=_headers(),
            json={
                "contact_ids": [contact_id],
                "emailer_campaign_id": sequence_id,
            },
            timeout=15,
        )
        data = r.json()

        if r.status_code in (200, 201):
            print(f"[APOLLO] Enrolled {contact_id} in sequence {sequence_id}")
            return {"ok": True, "error": None}

        print(f"[APOLLO] Enroll failed: HTTP {r.status_code} {json.dumps(data)[:200]}")
        return {"ok": False, "error": f"HTTP {r.status_code}: {str(data)[:200]}"}

    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 4. Update contact stage
# ---------------------------------------------------------------------------

def get_stages() -> list[dict]:
    """Get all pipeline stages in the account."""
    try:
        r = requests.get(
            f"{APOLLO_BASE}/contact_stages",
            headers=_headers(),
            timeout=15,
        )
        if r.status_code == 200:
            return r.json().get("contact_stages", [])
    except Exception:
        pass
    return []


def update_contact_stage(contact_id: str, stage_name: str) -> dict:
    """Move a contact to a named pipeline stage."""
    stages = get_stages()
    stage_id = None
    for s in stages:
        if s.get("name", "").lower() == stage_name.lower():
            stage_id = s.get("id")
            break

    if not stage_id:
        return {"ok": False, "error": f"Stage '{stage_name}' not found. Available: {[s.get('name') for s in stages]}"}

    try:
        r = requests.put(
            f"{APOLLO_BASE}/contacts/{contact_id}",
            headers=_headers(),
            json={"contact_stage_id": stage_id},
            timeout=15,
        )
        if r.status_code == 200:
            print(f"[APOLLO] Contact {contact_id} moved to stage '{stage_name}'")
            return {"ok": True, "error": None}
        return {"ok": False, "error": f"HTTP {r.status_code}"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


# ---------------------------------------------------------------------------
# 5. Get contact by email
# ---------------------------------------------------------------------------

def get_contact_by_email(email: str) -> dict:
    """Look up a contact by email address."""
    if not _api_key():
        return {"ok": False, "contact_id": None, "error": "APOLLO_API_KEY not set"}

    try:
        r = requests.post(
            f"{APOLLO_BASE}/contacts/search",
            headers=_headers(),
            json={
                "q_keywords": email,
                "per_page": 1,
            },
            timeout=15,
        )
        data = r.json()

        if r.status_code == 200:
            contacts = data.get("contacts", [])
            if contacts:
                c = contacts[0]
                return {
                    "ok": True,
                    "contact_id": c.get("id"),
                    "name": f"{c.get('first_name', '')} {c.get('last_name', '')}".strip(),
                    "email": c.get("email"),
                    "organization": c.get("organization_name"),
                    "stage": c.get("contact_stage", {}).get("name") if c.get("contact_stage") else None,
                    "error": None,
                }
            return {"ok": True, "contact_id": None, "error": None, "message": "No contact found"}

        return {"ok": False, "contact_id": None, "error": f"HTTP {r.status_code}"}

    except Exception as e:
        return {"ok": False, "contact_id": None, "error": str(e)}
