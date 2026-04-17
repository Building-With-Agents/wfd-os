"""Finance Agent — Ritu's grant finance + compliance assistant.

Scoped narrowly to the grant-compliance system (agents/grant-compliance).
Lives at /internal/finance in the portal. Calls the grant-compliance
FastAPI on :8000 via its tools.

DESIGN CHOICES

- Narrow scope. Unlike staff_agent which has access to the whole wfd-os
  platform, finance_agent only knows about grants, transactions,
  allocations, compliance flags, and QB sync state. When Ritu is on
  /internal/finance thinking about grant compliance, she doesn't want
  the agent reasoning about the BD pipeline or Jessica's blog posts.
- Tools only read. The Compliance Monitor's allowability decisions and
  the Classifier's allocation proposals live in the grant-compliance
  scaffold itself — not in this agent. The agent SURFACES what those
  produce; it doesn't reproduce their reasoning.
- No writes to QB. The scaffold's _ReadOnlyHttpxClient guard stays in
  force; this agent calls the scaffold's API which in turn calls
  QbClient. Every hop preserves read-only discipline.
- Cites. When the agent reports a compliance flag, it quotes the rule
  citation (e.g. '2 CFR 200.421') from the flag record. When it reports
  a number, it says where in the DB it came from.

SYSTEM PROMPT PHILOSOPHY

Two audiences: Ritu (ED + developer, knows the system) and eventually
Krista (bookkeeper, not technical). Today the prompt optimizes for
Ritu. When Krista starts using it we'll branch prompts by user_role.
"""
from __future__ import annotations

import os
import sys
from typing import Any

import httpx

from agents.assistant.base import BaseAgent, Tool

# Grant-compliance API base — same machine, port 8000, no auth.
# Uses the ngrok-skip-browser-warning header pattern in case the agent
# eventually serves through the tunnel (though it won't today).
GC_API = os.getenv("GRANT_COMPLIANCE_API_BASE", "http://127.0.0.1:8000")


SYSTEM_PROMPT = """You are Ritu's Finance Assistant for CFA's grant compliance system.

ABOUT THE SYSTEM — READ CAREFULLY
You sit on top of a grant-compliance scaffold that mirrors QuickBooks into
a `grant_compliance` Postgres schema and layers a deterministic rule engine,
a transaction Classifier, a Compliance Monitor, and a Reporting agent on
top. Every action the scaffold takes that matters (a sync, a classification
proposal, a compliance flag raised, a report drafted) writes an
append-only row in `audit_log`. Nothing is auto-approved.

YOUR JOB
Ritu asks you questions about grant finance and compliance status. You
answer using the tools below, which read from the scaffold's API on
:8000. When you cite a number, say where it came from. When you cite a
compliance flag, quote the rule (e.g. "2 CFR 200.421 — advertising").

HARD RULES

1. You NEVER write to QuickBooks. You never propose writing to QB. The
   scaffold's _ReadOnlyHttpxClient guard prevents this architecturally;
   you should respect the same discipline in how you describe the
   system's capabilities to Ritu.

2. You NEVER decide whether a cost is allowable under 2 CFR 200. That's
   deterministic Python code in compliance/unallowable_costs.py. When
   you surface a flag, you quote what the rule engine said; you don't
   render your own verdict.

3. You NEVER approve allocations on Ritu's behalf. If she asks you to,
   explain that allocations are human-approved via the review queue
   (once it's built) or the /allocations/{id}/decide API route.

4. If a tool returns an empty list, say so plainly. Don't make up data.
   Many tables are empty right now (grants, allocations, compliance
   flags) because the system was just wired to real QB data. That's
   expected — don't embellish.

5. Be concise. Ritu wrote the scaffold. She doesn't need framework
   explanations; she needs the number, the rule citation, or the
   status.

WHAT YOU CAN HELP WITH
- "What's my QB connection status?" → use get_qb_status
- "How many transactions did we pull in the last sync?" → get_qb_status
  or get_recent_transactions
- "Any open compliance flags?" → get_open_compliance_flags
- "Show me the last 10 transactions" → get_recent_transactions(limit=10)
- "What grants do we have configured?" → get_grants
- "Anything in Krista's review queue?" → get_allocation_queue

WHAT YOU CANNOT HELP WITH (yet)
- Running a full Classifier pass → that's POST /transactions/{id}/classify,
  scaffold-side, not exposed here as a tool until the review queue UI
  is built.
- Drafting a report → POST /reports, scaffold-side.
- Telling Ritu whether a specific transaction is allowable → only the
  Compliance Monitor decides that, via POST /compliance/scan.
"""


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


def _get(path: str) -> Any:
    """GET against the grant-compliance API. Never raises — returns error dict."""
    try:
        r = httpx.get(f"{GC_API}{path}", timeout=15)
        if r.status_code != 200:
            return {
                "error": f"HTTP {r.status_code}",
                "path": path,
                "body_preview": r.text[:200],
            }
        return r.json()
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "path": path}


def _get_qb_status() -> dict:
    """QB OAuth state: connected realms, token expiry, current environment."""
    return _get("/qb/status")


def _get_recent_transactions(limit: int = 10) -> dict:
    """Last N QB transactions by txn_date, most recent first."""
    data = _get("/transactions")
    if isinstance(data, dict) and "error" in data:
        return data
    if not isinstance(data, list):
        return {"error": "unexpected shape", "received": str(type(data))}
    # Sort by txn_date descending, cap to limit
    try:
        sorted_ = sorted(data, key=lambda t: t.get("txn_date") or "", reverse=True)
    except Exception:
        sorted_ = data
    return {
        "total": len(data),
        "showing": min(limit, len(data)),
        "transactions": sorted_[:limit],
    }


def _get_open_compliance_flags() -> dict:
    """All unresolved compliance flags (severity info/warning/blocker)."""
    data = _get("/compliance/flags")
    if isinstance(data, dict) and "error" in data:
        return data
    if not isinstance(data, list):
        return {"error": "unexpected shape", "received": str(type(data))}
    open_flags = [f for f in data if f.get("status") == "open"]
    return {
        "total_flags": len(data),
        "open_flags": len(open_flags),
        "by_severity": {
            "blocker": sum(1 for f in open_flags if f.get("severity") == "blocker"),
            "warning": sum(1 for f in open_flags if f.get("severity") == "warning"),
            "info": sum(1 for f in open_flags if f.get("severity") == "info"),
        },
        "flags": open_flags,
    }


def _get_grants() -> dict:
    """All grants currently configured in the scaffold."""
    data = _get("/grants")
    if isinstance(data, dict) and "error" in data:
        return data
    return {"total": len(data) if isinstance(data, list) else 0, "grants": data}


def _get_allocation_queue() -> dict:
    """Allocations currently in the 'proposed' state awaiting human review."""
    data = _get("/allocations/queue")
    if isinstance(data, dict) and "error" in data:
        return data
    return {"total_proposed": len(data) if isinstance(data, list) else 0, "allocations": data}


# ---------------------------------------------------------------------------
# Tool registrations
# ---------------------------------------------------------------------------


TOOLS = [
    Tool(
        name="get_qb_status",
        description=(
            "Get the QuickBooks OAuth connection state: connected realms, "
            "current environment (sandbox/production), access and refresh "
            "token expiry times, and whether the access token is currently "
            "expired. Call this when Ritu asks about connection status or "
            "when she's about to trigger a sync."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _get_qb_status(),
    ),
    Tool(
        name="get_recent_transactions",
        description=(
            "Get the most recent QB transactions from the mirror. Returns "
            "an object with total count, the number showing, and a list "
            "of transactions sorted by txn_date descending. Each "
            "transaction has qb_id, qb_type (Bill/Purchase/JournalEntry), "
            "txn_date, vendor_name, memo, amount_cents, and qb_class_id. "
            "Default limit is 10."
        ),
        parameters={
            "type": "object",
            "properties": {
                "limit": {
                    "type": "integer",
                    "description": "Max transactions to return. Default 10.",
                }
            },
            "required": [],
        },
        fn=lambda **kwargs: _get_recent_transactions(kwargs.get("limit", 10)),
    ),
    Tool(
        name="get_open_compliance_flags",
        description=(
            "Get unresolved compliance flags raised by the Compliance "
            "Monitor. Each flag cites a 2 CFR 200 rule (e.g., "
            "'2 CFR 200.421 — advertising'). Returns counts broken down "
            "by severity (blocker/warning/info) plus the full list. If "
            "the Compliance Monitor hasn't been run yet, the list will "
            "be empty — that's normal for a fresh system."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _get_open_compliance_flags(),
    ),
    Tool(
        name="get_grants",
        description=(
            "List all grants currently configured in the scaffold. Each "
            "grant has a name, funder, period_start/period_end, "
            "total_award_cents, and qb_class_name (the QB Class it maps "
            "to). If zero grants are configured, say so — this means the "
            "system was wired but grants haven't been seeded yet."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _get_grants(),
    ),
    Tool(
        name="get_allocation_queue",
        description=(
            "List proposed allocations awaiting Krista's review. An "
            "allocation is the Classifier's proposal to charge a "
            "transaction (or a portion of it) to a specific grant. "
            "Empty list means the Classifier hasn't been run against "
            "the synced transactions yet, OR Krista has worked through "
            "the queue."
        ),
        parameters={"type": "object", "properties": {}, "required": []},
        fn=lambda **_: _get_allocation_queue(),
    ),
]


finance_agent = BaseAgent(
    agent_type="finance",
    system_prompt=SYSTEM_PROMPT,
    tools=TOOLS,
)
