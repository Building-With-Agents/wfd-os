"""Hunter.io API client — email finder and domain search.

Free tier: 25 searches/month. Prioritize Hot companies.
Auth: api_key query parameter.
Base URL: https://api.hunter.io/v2

All functions return structured dicts and never raise.
"""
from __future__ import annotations

import os
import requests

HUNTER_BASE = "https://api.hunter.io/v2"


def _api_key() -> str:
    return os.getenv("HUNTER_API_KEY", "")


def find_email(domain: str, first_name: str, last_name: str) -> dict:
    """Find a verified email address for a person at a domain.

    Returns {ok, email, confidence, sources, error}.
    """
    key = _api_key()
    if not key:
        return {"ok": False, "email": None, "error": "HUNTER_API_KEY not set"}

    try:
        r = requests.get(
            f"{HUNTER_BASE}/email-finder",
            params={
                "domain": domain,
                "first_name": first_name,
                "last_name": last_name,
                "api_key": key,
            },
            timeout=15,
        )
        data = r.json()

        if r.status_code == 200 and data.get("data"):
            d = data["data"]
            email = d.get("email")
            confidence = d.get("confidence", 0)
            sources = d.get("sources", 0)
            if email and confidence >= 50:
                print(f"[HUNTER] Found email: {email} (confidence: {confidence}%)")
                return {
                    "ok": True,
                    "email": email,
                    "confidence": confidence,
                    "sources": sources,
                    "error": None,
                }
            return {
                "ok": True,
                "email": email if confidence >= 30 else None,
                "confidence": confidence,
                "sources": sources,
                "error": f"Low confidence: {confidence}%",
            }

        error_msg = data.get("errors", [{}])[0].get("details", str(r.status_code)) if data.get("errors") else f"HTTP {r.status_code}"
        return {"ok": False, "email": None, "error": error_msg}

    except Exception as e:
        print(f"[HUNTER] find_email error: {e}")
        return {"ok": False, "email": None, "error": str(e)}


def domain_search(domain: str, limit: int = 10) -> dict:
    """Search Hunter.io for email addresses at a domain.

    Returns {ok, emails: [{email, first_name, last_name, position, confidence}], error}.
    """
    key = _api_key()
    if not key:
        return {"ok": False, "emails": [], "error": "HUNTER_API_KEY not set"}

    try:
        r = requests.get(
            f"{HUNTER_BASE}/domain-search",
            params={
                "domain": domain,
                "limit": limit,
                "api_key": key,
            },
            timeout=15,
        )
        data = r.json()

        if r.status_code == 200 and data.get("data"):
            raw_emails = data["data"].get("emails", [])
            emails = []
            for e in raw_emails:
                emails.append({
                    "email": e.get("value"),
                    "first_name": e.get("first_name"),
                    "last_name": e.get("last_name"),
                    "position": e.get("position"),
                    "seniority": e.get("seniority"),
                    "confidence": e.get("confidence", 0),
                })
            return {"ok": True, "emails": emails, "error": None}

        return {"ok": False, "emails": [], "error": f"HTTP {r.status_code}"}

    except Exception as e:
        print(f"[HUNTER] domain_search error: {e}")
        return {"ok": False, "emails": [], "error": str(e)}
