"""
CFA Finance Cockpit API — Phase 2B.

Serves the cockpit's live data over HTTP. The Next.js portal page at
/internal/finance/ fetches from /api/finance/* (rewritten by
portal/student/next.config.mjs to :8013/*) for status, hero metrics,
decisions list, per-tab content, and polymorphic drill content.

Endpoints:
  GET  /cockpit/status            — metadata + data source health
  GET  /cockpit/hero              — 4 hero-cell payloads
  GET  /cockpit/decisions         — sorted decision items
  GET  /cockpit/tabs/{tab_id}     — content for one tab
  GET  /cockpit/drills/{key}      — polymorphic drill content
  POST /cockpit/refresh           — re-read from data source
  GET  /health                    — liveness check

Run: uvicorn agents.finance.cockpit_api:app --reload --port 8013

Data source
-----------
Wraps agents/finance/data_source.py::ExcelDataSource, which in turn wraps
agents/finance/design/cockpit_data.py::extract_all. Switching to QB later
is a one-line change in default_source().
"""

from __future__ import annotations

import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Windows consoles default to cp1252 and choke on UTF-8 characters that the
# spreadsheets / cockpit text contain (em-dash, middle dot, etc.). Force
# stdout/stderr to UTF-8 so log lines and error tracebacks don't crash.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

# Make the repo root importable so `from agents.finance.data_source import ...`
# works when running uvicorn from various cwds.
_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

# Optional .env — match the pattern used by other agent APIs.
try:
    from dotenv import load_dotenv
    load_dotenv(_REPO_ROOT / ".env", override=False)
except ImportError:  # pragma: no cover — dotenv is a dev-only convenience
    pass

from agents.finance.data_source import DataSource, default_source  # noqa: E402


# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = FastAPI(title="CFA Finance Cockpit API", version="0.2.0")

# Every /api/finance/* request from the portal (Next.js dev server on :3000,
# or whatever auto-port it grabbed) gets proxied here. Allow both the stable
# localhost and the 127.0.0.1 form; wildcard * is unsafe for this kind of
# finance-data surface.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # When the dev server picks a non-3000 auto-port, the browser still
        # reports its own origin — list a few common local variants. The
        # regex below catches the auto-port case without opening up to *.
    ],
    allow_origin_regex=r"http://(localhost|127\.0\.0\.1):\d+",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Structured request log. Frontend traffic is visible without tcpdump."""
    t0 = time.perf_counter()
    response = await call_next(request)
    dur_ms = (time.perf_counter() - t0) * 1000
    print(
        f"[cockpit_api] {request.method} {request.url.path} "
        f"-> {response.status_code} | {dur_ms:.1f}ms",
        flush=True,
    )
    return response


# The DataSource lives for the process lifetime; extract() memoizes. Refresh
# repopulates the cache.
_SOURCE: DataSource = default_source()


def _data() -> dict:
    """Shorthand so endpoint handlers don't repeat the data-source dance."""
    return _SOURCE.extract()


# ---------------------------------------------------------------------------
# Helpers that map the extract_all() dict → endpoint response shapes
# ---------------------------------------------------------------------------

def _trailing_q1_total(data: dict) -> int:
    return sum(
        row["invoice"]
        for row in data["placements"]["q1_provider_actuals_breakdown"]
        if row.get("invoice") is not None
    )


def _high_priority_count(data: dict) -> int:
    return sum(1 for i in data["action_items"] if i["priority"] == "HIGH")


def _fmt_usd(n: float | int) -> str:
    return f"${n:,.0f}"


def _fmt_num(n: float | int) -> str:
    return f"{n:,}"


def _excel_source_label() -> str:
    """Human-friendly source chip value for hero cells."""
    info = _SOURCE.info()
    if info["type"] == "excel":
        return "Excel · K8341 fixtures"
    return info["type"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _priority_tone(priority: str) -> str:
    return {"HIGH": "critical", "MEDIUM": "watch"}.get(priority, "neutral")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@app.get("/health")
def health():
    return {"ok": True, "service": "cockpit_api", "version": app.version}


@app.get("/cockpit/status")
def status():
    """Metadata the top bar + refresh-timestamp surfaces read."""
    data = _data()
    summary = data["summary"]
    info = _SOURCE.info()
    return {
        "as_of": summary["today"],
        "months_remaining": summary["months_remaining"],
        "days_remaining": summary["days_remaining"],
        "last_sync": info.get("loaded_at"),
        "data_sources": [info],
    }


@app.get("/cockpit/hero")
def hero():
    """Four hero cells — same data the cockpit-client renders up top."""
    data = _data()
    summary = data["summary"]
    placements = data["placements"]
    trailing_q1 = _trailing_q1_total(data)
    high_count = _high_priority_count(data)
    source = _excel_source_label()
    updated = _SOURCE.info().get("loaded_at") or _now_iso()

    return {
        "backbone": {
            "drill_key": "backbone",
            "label": "Backbone Runway",
            "value": _fmt_usd(summary["backbone_runway_combined"]),
            "subtitle": (
                f"{_fmt_usd(summary['backbone_remaining'])} staff & overhead · "
                f"{_fmt_usd(summary['cfa_contractor_remaining'])} recovery contractors"
            ),
            "status_chip": {"label": "Tight · On Track", "tone": "watch"},
            "updated_at": updated,
            "source": source,
        },
        "placements": {
            "drill_key": "placements",
            "label": "Placements",
            "value": str(placements["confirmed_total"]),
            "value_suffix": f"/ {_fmt_num(placements['grant_goal'])}",
            "subtitle": (
                f"PIP threshold ({placements['pip_threshold']}) cleared · "
                f"{placements['grant_goal'] - placements['confirmed_total']} to grant goal"
            ),
            "live_minutes_ago": placements["live_synced_minutes_ago"],
            "status_chip": {"label": "Above PIP", "tone": "good"},
            "updated_at": updated,
            "source": "WJI TWC + WSAC",
        },
        "cash": {
            "drill_key": "reimbursement",
            "label": "Cash Position",
            "value": _fmt_usd(trailing_q1),
            "subtitle": "Q1 provider reimbursement pending from ESD",
            "status_chip": {"label": "Awaiting ESD", "tone": "watch"},
            "updated_at": updated,
            "source": source,
        },
        "flags": {
            "drill_key": "flags",
            "label": "Critical Flags",
            "value": str(high_count),
            "subtitle": "From v3 reconciliation Action Items · HIGH priority",
            "status_chip": {"label": "Action Needed", "tone": "critical"},
            "updated_at": updated,
            "source": "v3 Reconciliation · Action Items",
        },
    }


@app.get("/cockpit/decisions")
def decisions():
    """Decision list — 11 items today, sorted by priority then stable order."""
    data = _data()
    source = "v3 Reconciliation · Action Items (2026-03-27)"
    created_at = _now_iso()  # placeholder; the sheet doesn't carry timestamps
    items = []
    for i, item in enumerate(data["action_items"]):
        items.append({
            "id": f"decision-{i}",
            "drill_key": f"decision:{i}",
            "title": f"{item['area']} — {item['action']}",
            "area": item["area"],
            "action": item["action"],
            "owner": item["owner"],
            "priority": item["priority"],
            "priority_tone": _priority_tone(item["priority"]),
            "status": "open",
            "source": source,
            "created_at": created_at,
        })
    return {"items": items, "sorted_by": "priority", "total": len(items)}


# ---- Tab content ----------------------------------------------------------

@app.get("/cockpit/tabs/{tab_id}")
def tab_content(tab_id: str):
    """Per-tab slice of cockpit data. Only the fields the tab renders."""
    data = _data()
    handler = _TAB_HANDLERS.get(tab_id)
    if handler is None:
        raise HTTPException(
            status_code=404,
            detail=f"Unknown tab_id: {tab_id!r}. Valid: {sorted(_TAB_HANDLERS)}",
        )
    return handler(data)


def _tab_budget(data: dict) -> dict:
    s = data["summary"]
    total_spent = s["gjc_paid"] + s["cfa_contractor_paid"] + s["backbone_qb_paid"]
    return {
        "tab": "budget",
        "verdict": {
            "tone": "watch",
            "headline": "Backbone runway lands within ~$3k of the September 30 grant end.",
            "body": (
                "At current burn (~$78k/month across backbone + contractors), "
                "the four backbone categories run out roughly aligned with "
                "grant end. CFA Contractors finishes with ~$0 if AI Engage "
                "and Pete & Kelly stay at current pace. The $700k+ unspent "
                "in GJC Contractors is the lever — moving even $200k via "
                "budget amendment buys substantial recovery-work runway."
            ),
        },
        "categories": s["categories"],
        "totals": {
            "budget": s["grant_total_budget"],
            "spent": total_spent,
            "remaining": s["grant_total_budget"] - total_spent,
            "pct": (total_spent / s["grant_total_budget"] * 100) if s["grant_total_budget"] else 0,
        },
        "months_remaining": s["months_remaining"],
    }


def _tab_placements(data: dict) -> dict:
    p = data["placements"]
    return {
        "tab": "placements",
        "summary": {
            "confirmed_total": p["confirmed_total"],
            "grant_goal": p["grant_goal"],
            "pip_threshold": p["pip_threshold"],
            "coalition_reported": p["coalition_reported"],
            "cfa_verified": p["cfa_verified"],
            "q1_provider_actuals": p["q1_provider_actuals"],
            "recovery_target": p["recovery_target"],
        },
        "recovered_total": data["recovered"].get("total_validated", 0),
        "quarterly_placements": p["quarterly_placements"],
        "quarter_labels": p["quarter_labels"],
        "verdict": {
            "tone": "good",
            "headline": f"{p['confirmed_total']} confirmed of {p['grant_goal']:,} — PIP threshold cleared.",
            "body": (
                f"Coalition reported {p['coalition_reported']} placements through Q4 net of "
                f"retractions. CFA verified {p['cfa_verified']} additional Good Jobs via "
                f"LinkedIn outreach. {p['q1_provider_actuals']} more from Provider Q1 actuals. "
                f"Recovery target Q2-Q3: {p['recovery_target']} more to hit the {p['grant_goal']:,} goal."
            ),
        },
    }


def _tab_providers(data: dict) -> dict:
    groups = data["providers"]
    return {
        "tab": "providers",
        "stats": {
            "total_providers": sum(len(v) for v in groups.values()),
            "active": len(groups["active"]),
            "cfa_contractors": len(groups["cfa_contractors"]),
            "closed": (
                len(groups["closed_with_placements"])
                + len(groups["closed_support"])
                + len(groups["terminated"])
            ),
            "terminated": len(groups["terminated"]),
        },
        "groups": [
            {"id": "active", "label": "Active — closing out", "rows": groups["active"]},
            {"id": "closed_with_placements", "label": "Closed — placement-based",
             "rows": groups["closed_with_placements"]},
            {"id": "closed_support", "label": "Closed — support / engagement",
             "rows": groups["closed_support"]},
            {"id": "terminated", "label": "ESD-directed terminations",
             "rows": groups["terminated"]},
            {"id": "cfa_contractors", "label": "CFA Contractors — recovery engine",
             "rows": groups["cfa_contractors"]},
        ],
    }


def _tab_transactions(data: dict) -> dict:
    # Until production QB sync lands, transactions are the hand-curated sample
    # that the HTML mockup + React scaffold showed. Shape matches what the
    # frontend already renders — future QB integration fills transactions
    # from the real feed without changing this envelope.
    return {
        "tab": "transactions",
        "stats": {
            "mirrored_from_qb": 53,
            "tagged_with_class": {"tagged": 0, "total": 53},
            "anomalies_open": 2,
        },
        "transactions": [
            {"date": "2026-04-14", "type": "Bill", "vendor": "AI Engage Group LLC",
             "memo": "March recovery work — 47 candidates reviewed",
             "category": "CFA Contractors", "amount": 12000, "anomaly": False},
            {"date": "2026-04-12", "type": "Purchase", "vendor": "Brosnahan Insurance Agency",
             "memo": "Workers comp Q2 2026", "category": "Personnel — Benefits",
             "amount": 1847, "anomaly": False},
            {"date": "2026-04-10", "type": "Purchase", "vendor": "Unknown vendor ●",
             "memo": "Office supplies", "category": "Other Direct",
             "amount": 1243, "anomaly": True},
            {"date": "2026-04-08", "type": "Bill", "vendor": "Pete & Kelly Vargo",
             "memo": "March outreach contract", "category": "CFA Contractors",
             "amount": 18500, "anomaly": False},
            {"date": "2026-04-05", "type": "JE", "vendor": "Payroll Apr 1-15",
             "memo": "K8341 allocation", "category": "Personnel — Salaries",
             "amount": 17184, "anomaly": False},
            {"date": "2026-04-02", "type": "Bill", "vendor": "Code Day X MinT",
             "memo": "Q1 final invoice — 8 placements × $3,222",
             "category": "GJC Contractors", "amount": 25776, "anomaly": False},
        ],
        "total_count": 53,
        "note": "production QB sync pending",
    }


def _tab_reporting(data: dict) -> dict:
    return {
        "tab": "reporting",
        "cycle": [
            {"num": "01", "name": "March reconciled", "date": "Apr 5 · ✓", "state": "done"},
            {"num": "02", "name": "April advance drafted", "date": "Apr 17 · today", "state": "current"},
            {"num": "03", "name": "Submit to ESD", "date": "Apr 30 · due", "state": ""},
            {"num": "04", "name": "ESD funds advance", "date": "~May 21 · est.", "state": ""},
            {"num": "05", "name": "Spend through April", "date": "Apr 30 close", "state": ""},
            {"num": "06", "name": "Reconcile vs. actual", "date": "May 5 · est.", "state": ""},
        ],
    }


def _tab_audit(data: dict) -> dict:
    return {
        "tab": "audit",
        "verdict": {
            "tone": "watch",
            "headline": "73% audit-ready. Biggest gap is time & effort certifications.",
            "body": (
                "Single Audit covering K8341 spend will be due roughly September 2027. "
                "ESD monitoring visits can happen anytime with 2-4 weeks notice. Worth "
                "closing the documentation gaps now while institutional memory is fresh, "
                "not in a year when staff may have turned over."
            ),
        },
        "stats": {
            "overall": "73%",
            "doc_gap": 12,
            "te_certs": "0 / 9",
        },
        "dimensions": [
            {"id": "allowable_costs", "label": "Allowable costs",
             "what": "Every transaction maps to an allowable category",
             "pct": 96, "tone": "good", "owner": "Krista"},
            {"id": "transaction_documentation", "label": "Transaction documentation",
             "what": "Vendor invoices, receipts, approvals on file",
             "pct": 88, "tone": "watch", "owner": "Krista"},
            {"id": "time_effort", "label": "Time & effort certifications",
             "what": "Quarterly attestations from federally-funded staff",
             "pct": 0, "tone": "critical", "owner": "Ritu"},
            {"id": "procurement", "label": "Procurement & competition",
             "what": "Competitive process or sole-source justification per contract",
             "pct": 92, "tone": "good", "owner": "Ritu"},
            {"id": "subrecipient_monitoring", "label": "Subrecipient monitoring",
             "what": "Risk assessment, monitoring, follow-up per provider",
             "pct": 81, "tone": "watch", "owner": "Ritu · Bethany"},
            {"id": "performance_reporting", "label": "Performance reporting accuracy",
             "what": "Reported placements reconcilable to source data",
             "pct": 95, "tone": "good", "owner": "Bethany · Gage"},
        ],
    }


_TAB_HANDLERS = {
    "budget": _tab_budget,
    "placements": _tab_placements,
    "providers": _tab_providers,
    "transactions": _tab_transactions,
    "reporting": _tab_reporting,
    "audit": _tab_audit,
}


# ---- Drills --------------------------------------------------------------

@app.get("/cockpit/drills/{drill_key:path}")
def drill(drill_key: str):
    """Polymorphic drill content. Lookup into the registry built by
    build_drills(). The :path converter lets keys like
    'category:GJC Contractors — Training Providers' route cleanly."""
    data = _data()
    entry = data["drills"].get(drill_key)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"No drill content for key: {drill_key!r}",
        )
    return entry


# ---- Refresh -------------------------------------------------------------

@app.post("/cockpit/refresh")
def refresh():
    """Force re-read from the data source. Returns the new status."""
    _SOURCE.refresh()
    return status()


# ---------------------------------------------------------------------------
# Main entry — run directly for quick testing:  python -m agents.finance.cockpit_api
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    import uvicorn
    port = int(os.environ.get("COCKPIT_API_PORT", "8013"))
    uvicorn.run(
        "agents.finance.cockpit_api:app",
        host="127.0.0.1",
        port=port,
        reload=True,
    )
