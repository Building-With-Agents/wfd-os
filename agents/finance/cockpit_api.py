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

from agents.finance.audit_activity_labels import render_entries as render_activity_entries  # noqa: E402
from agents.finance.audit_dimension_display import display_name_for_role  # noqa: E402
from agents.finance.data_source import DataSource, default_source  # noqa: E402
from agents.finance.discussion_prompts import generate_discussion_prompts  # noqa: E402
from agents.finance.verdict_generator import generate_verdict  # noqa: E402


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
    """Metadata the top bar + refresh-timestamp + tab-count badges read."""
    data = _data()
    summary = data["summary"]
    info = _SOURCE.info()
    providers = data["providers"]
    return {
        "as_of": summary["today"],
        "months_remaining": summary["months_remaining"],
        "days_remaining": summary["days_remaining"],
        "last_sync": info.get("loaded_at"),
        "data_sources": [info],
        # Per-tab small-metadata counts that belong with the shell's first
        # paint. Keeps the tab-count badges ("Providers 9") fresh without
        # forcing the client to fetch every tab eagerly.
        "tab_counts": {
            "decisions": len(data["action_items"]),
            "providers": len(providers["active"]),
            "transactions": 53,  # static sample until QB sync lands
            "reporting": 2,      # April cycle + monthly placement report
            "audit": 6,          # dimensions
            "high_priority": _high_priority_count(data),
        },
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


@app.get("/cockpit/activity")
def cockpit_activity():
    """Rendered Recent Compliance Activity feed.

    Reads from data["audit_activity_from_engine"] (populated by
    extract_all's fetch of /compliance/activity on :8000), applies
    label translation via agents/finance/audit_activity_labels.py,
    and returns {entries, engine_status}.

    engine_status is "ok" when the last engine fetch succeeded and
    "unreachable" otherwise — drives the cockpit's degraded-state
    rendering per spec §v1.2.9.
    """
    data = _data()
    engine_response = data.get("audit_activity_from_engine") or {}
    engine_ok = engine_response.get("engine_ok", False)
    return {
        "entries": render_activity_entries(engine_response),
        "engine_status": "ok" if engine_ok else "unreachable",
    }


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
        # Personnel & Contractors sub-section. Already a serialized dict
        # (PersonnelExtract.to_dict shape) from cockpit_data._extract_personnel.
        # Per-person drills are merged into data["drills"] as `person:<id>`
        # so the existing /cockpit/drills/{key} route serves them unchanged.
        # See agents/finance/design/personnel_contractors_view_spec.md.
        "personnel": data.get("personnel", {
            "people": [],
            "rollups": [],
            "distinct_person_count": 0,
            "summary": {"paid_to_date": 0, "total_committed": 0, "variance_vs_amended": 0},
            "reconciliation_warnings": [],
            "extracted_at": None,
            "source_workbook": None,
        }),
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


def _tone_for_dimension(pct: Optional[int], status: str) -> str:
    """Map readiness pct + three-state status to a UI tone slug.

    Contract (from audit_readiness_tab_spec.md §v1.2.4):
      - placeholder, or computed + pct is None  → "neutral"
      - computed + pct >= 90                    → "good"
      - computed + pct >= 70                    → "watch"
      - computed + pct  < 70                    → "critical"
    """
    if status == "placeholder" or pct is None:
        return "neutral"
    if pct >= 90:
        return "good"
    if pct >= 70:
        return "watch"
    return "critical"


def _tab_audit(data: dict) -> dict:
    """Assemble the Audit Readiness tab payload.

    Both dimensions and stats come from the compliance engine via
    extract_all's audit_dimensions_from_engine fetch. When the engine
    is unreachable, the fetch already synthesizes fallback payloads for
    both — this function just flows them through and sets
    engine_status="unreachable" so the UI can render a visually
    distinct degraded state (per spec §v1.2.6).

    Verdict: hardcoded "happy path" copy in v1.2 step 3 (LLM-generated
    cached text comes in step 5). When engine_status=="unreachable",
    the verdict is overridden with a static "data unavailable" message
    per spec §v1.2.6.

    TODO(v1.2 cockpit-side step 2/3 follow-up): add pytest on this
    branch and cover the engine-response mapping, tone computation,
    subcopy selection, and unreachable fallback. Tests deferred per
    scope decision; see integration_notes.md on
    feature/compliance-engine-extract.
    """
    engine_response = data.get("audit_dimensions_from_engine") or {}
    engine_ok = engine_response.get("engine_ok", False)
    engine_status = "ok" if engine_ok else "unreachable"

    # Dimensions — unchanged from step 2 cockpit-side. Degraded-state
    # rendering is handled by the fetch helper's fallback payload.
    engine_dimensions = engine_response.get("dimensions", [])
    ui_dimensions: list[dict] = []
    for d in engine_dimensions:
        pct = d.get("readiness_pct")
        status = d.get("status", "placeholder")
        ui_dimensions.append({
            "id": d["id"],
            "label": d.get("title", d["id"]),
            "what": d.get("what_auditors_look_for", ""),
            "pct": pct,
            "status": status,
            "tone": _tone_for_dimension(pct, status),
            "owner": display_name_for_role(d.get("owner_role")),
        })

    # Stats — flowed through as-is from the engine response (or its
    # fallback when unreachable). Display formatting lives in the
    # React component; Python just passes the raw values.
    stats = engine_response.get("stats") or {}

    # Verdict — LLM-generated on the happy path, static fallback when
    # the engine is unreachable. Cached for 5 min by input hash.
    # See verdict_generator.generate_verdict for the three-layer fallback
    # and agents/grant-compliance/docs/audit_readiness_tab_spec.md §v1.2.8.
    # TODO(v1.2 cockpit-side step 5 follow-up): add pytest on this branch
    # and cover the cache key, LLM happy path, and static fallback branches.
    verdict_result = generate_verdict(
        engine_status=engine_status,
        stats=stats,
        dimensions=ui_dimensions,
    )
    verdict = {
        "tone": verdict_result["tone"],
        "headline": verdict_result["headline"],
        "body": verdict_result["body"],
        "source": verdict_result.get("source"),
    }

    return {
        "tab": "audit",
        "verdict": verdict,
        "stats": stats,
        "engine_status": engine_status,
        "dimensions": ui_dimensions,
    }


def _tab_compliance(data: dict) -> dict:
    """Compliance Requirements tab payload — proxies the engine's
    GET /compliance/requirements/current.

    Engine-side data lives in the grant_compliance.compliance_requirements_sets
    + compliance_requirements tables, populated by the Compliance Requirements
    Agent (Mode A run). When the engine is unreachable or no current set
    exists for K8341, this handler returns a degraded payload with
    engine_status set so the React UI can render a visually distinct
    degraded state (matching the audit-tab pattern in §v1.2.6).

    Spec: agents/finance/design/compliance_requirements_display_spec.md.
    Engine implementation: agents/grant-compliance/src/grant_compliance/
    compliance_requirements_agent/ (engine commit 4c1a566 on
    feature/compliance-engine-extract).
    """
    import httpx

    # Engine URL is overridable via env so dev environments where :8000 is
    # taken by another service (e.g., the Waifinder marketing site) can run
    # the engine on a free port. Default is the canonical 8000.
    engine_base = os.environ.get("GRANT_COMPLIANCE_ENGINE_URL", "http://127.0.0.1:8000").rstrip("/")
    timeout_seconds = 8.0

    # Resolve K8341's grant_id by listing grants and matching award_number.
    # Hardcoded UUID would be brittle (changes on DB rebuild). The lookup
    # adds one HTTP call to tab-load latency; acceptable for v1.
    try:
        resp = httpx.get(f"{engine_base}/grants", timeout=timeout_seconds)
        resp.raise_for_status()
        grants = resp.json()
        target = next(
            (g for g in grants if g.get("award_number") == "K8341"),
            None,
        )
        if target is None:
            return {
                "tab": "compliance",
                "current_set": None,
                "engine_status": "no_set_yet",
                "engine_error": "K8341 grant not found in engine database. "
                "Seed the grant before generating a requirements set.",
            }
        grant_id = target["id"]
    except Exception as exc:  # noqa: BLE001 — graceful degradation
        return {
            "tab": "compliance",
            "current_set": None,
            "engine_status": "unreachable",
            "engine_error": f"Engine /grants fetch failed: {type(exc).__name__}: {exc}",
        }

    # Fetch the current requirements set.
    try:
        resp = httpx.get(
            f"{engine_base}/compliance/requirements/current",
            params={"grant_id": grant_id},
            timeout=timeout_seconds,
        )
        if resp.status_code == 404:
            return {
                "tab": "compliance",
                "current_set": None,
                "engine_status": "no_set_yet",
                "engine_error": (
                    f"No current ComplianceRequirementsSet for K8341 "
                    f"(grant_id={grant_id}). Run "
                    "POST /compliance/requirements/generate first."
                ),
            }
        resp.raise_for_status()
        current_set = resp.json()
    except Exception as exc:  # noqa: BLE001 — graceful degradation
        return {
            "tab": "compliance",
            "current_set": None,
            "engine_status": "unreachable",
            "engine_error": f"Engine /compliance/requirements/current fetch failed: "
                            f"{type(exc).__name__}: {exc}",
        }

    return {
        "tab": "compliance",
        "current_set": current_set,
        "engine_status": "ok",
        "engine_error": None,
    }


_TAB_HANDLERS = {
    "budget": _tab_budget,
    "placements": _tab_placements,
    "providers": _tab_providers,
    "transactions": _tab_transactions,
    "reporting": _tab_reporting,
    "audit": _tab_audit,
    "compliance": _tab_compliance,
}


# ---- Drills --------------------------------------------------------------

@app.get("/cockpit/drills/{drill_key:path}")
def drill(drill_key: str):
    """Polymorphic drill content. Lookup into the registry built by
    build_drills(). The :path converter lets keys like
    'category:GJC Contractors — Training Providers' route cleanly.

    Augments the baked entry with a `discussion_prompts` array — three
    seeded prompts for the drill-chat surface, generated server-side per
    agents/finance/design/chat_spec.md §"Seeded prompts" (Surface 2)."""
    data = _data()
    entry = data["drills"].get(drill_key)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"No drill content for key: {drill_key!r}",
        )
    return {
        **entry,
        "discussion_prompts": generate_discussion_prompts(drill_key, entry),
    }


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
