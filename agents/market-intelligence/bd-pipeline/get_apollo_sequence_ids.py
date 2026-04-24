"""
Utility: List all Apollo email sequences with their IDs.

Usage:
    python get_apollo_sequence_ids.py
"""
import os
import sys
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "../../../.env"), override=True)

import requests

APOLLO_BASE = "https://api.apollo.io/v1"


def _headers():
    return {
        "X-Api-Key": os.getenv("APOLLO_API_KEY", ""),
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def list_sequences():
    """List all Apollo email sequences."""
    resp = requests.post(
        f"{APOLLO_BASE}/emailer_campaigns/search",
        headers=_headers(),
        json={"per_page": 100},
        timeout=15,
    )
    if resp.status_code != 200:
        print(f"Error: HTTP {resp.status_code}")
        return

    campaigns = resp.json().get("emailer_campaigns", [])
    print(f"\nApollo Email Sequences ({len(campaigns)} total)")
    print(f"{'='*80}")
    print(f"{'Sequence Name':<45} {'ID':<30} {'Active':<8} {'Steps'}")
    print(f"{'-'*80}")

    for c in campaigns:
        name = c.get("name") or "Unnamed"
        seq_id = c.get("id") or ""
        active = "Yes" if c.get("active") else "No"
        steps = c.get("num_steps") or 0
        contacts = (c.get("unique_scheduled") or 0) + (c.get("unique_delivered") or 0)
        print(f"  {name:<43} {seq_id:<30} {active:<8} {steps} steps, {contacts} contacts")

    print(f"\nCopy the sequence IDs above to wire Agent 13's SEQUENCE_MAP.")


if __name__ == "__main__":
    list_sequences()
