import os
import json
from anthropic import Anthropic
from database.db import get_session
from database.models import MonthlySnapshot, Transaction, ProviderPayment, Anomaly, BaselineData

client = None


def get_client():
    global client
    if client is None:
        client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    return client


SYSTEM_PROMPT = """You are a grant financial analyst for Computing For All (CFA), managing the WJI grant from ESD Washington. Use the data context provided. Be precise with numbers and flag concerns.

BUDGET ($4,875,000 total, Amendment 1):
GJC Contractors $2,315,623 | CFA Contractors $1,020,823 | Personnel Salaries $1,097,662 | Personnel Benefits $173,170 | Other Direct $88,921 | Indirect $178,799

CURRENT POSITION (QB actuals as of 3/26/2026): $3,367,252 spent, $1,507,748 remaining. GJC $1,328,794 (57%), CFA $810,607 (79%), Overhead $1,227,851 (80% prorated). 423 net placements of 730 PIP threshold (57.9%). 6 months left (ends Sep 2026). Need 307 more placements (~51/month).

PROVIDER RATES: Ada/Vets2Tech/Apprenti $2,500 | Code Day $3,222 | Per Scholas $3,443 | Year Up $2,623. Terminated (no payments): WABS, NCESD, Riipen.

RULES: Flag budget categories at 90%+ (warning) or 100%+ (critical). Flag CC charges >$1,000 not in QuickBooks. Flag payments to terminated providers. Flag invoice vs placement mismatches >$500.

SHAREPOINT: monthly-uploads (current month files), baseline (historical Excel files). Use /files to list, /reconcile to process, /load-baseline for historical data.

Format for Teams: headers, bullets, bold key numbers. Concise but complete."""


def _baseline_budget_context() -> dict:
    """Confirmed QB actuals as of 3/26/2026 — used as fallback when no DB snapshot exists."""
    return {
        "data_source": "confirmed_qb_actuals_2026-03-26",
        "latest_month": "2026-03",
        "total_spent_to_date": 3367252,
        "total_remaining": 1507748,
        "placements_completed": 423,
        "placements_target": 730,
        "placements_remaining": 307,
        "budget_status": {
            "GJC Contractors": {"budget": 2315623, "spent": 1328794, "remaining": 986829, "pct_used": 57.4},
            "CFA Contractors": {"budget": 1020823, "spent": 810607, "remaining": 210216, "pct_used": 79.4},
            "Personnel Salaries": {"budget": 1097662, "spent": 876553, "remaining": 221109, "pct_used": 79.9},
            "Personnel Benefits": {"budget": 173170, "spent": 138277, "remaining": 34893, "pct_used": 79.9},
            "Other Direct Costs": {"budget": 88921, "spent": 70966, "remaining": 17955, "pct_used": 79.8},
            "Indirect Costs": {"budget": 178799, "spent": 142655, "remaining": 36144, "pct_used": 79.8},
        },
    }


def get_latest_data_context() -> str:
    """Pull latest snapshot data to include in Claude prompt."""
    session = get_session()
    try:
        snapshot = session.query(MonthlySnapshot).order_by(MonthlySnapshot.month.desc()).first()
        anomalies = session.query(Anomaly).filter(Anomaly.resolved == False).order_by(Anomaly.created_at.desc()).limit(10).all()
        providers = session.query(ProviderPayment).order_by(ProviderPayment.month.desc()).limit(20).all()

        context = {}

        if snapshot:
            context["latest_month"] = snapshot.month
            context["budget_status"] = {
                "GJC Contractors": {"budget": snapshot.gjc_contractors_budget, "spent": snapshot.gjc_contractors_spent},
                "CFA Contractors": {"budget": snapshot.cfa_contractors_budget, "spent": snapshot.cfa_contractors_spent},
                "Personnel Salaries": {"budget": snapshot.personnel_salaries_budget, "spent": snapshot.personnel_salaries_spent},
                "Personnel Benefits": {"budget": snapshot.personnel_benefits_budget, "spent": snapshot.personnel_benefits_spent},
                "Other Direct Costs": {"budget": snapshot.other_direct_budget, "spent": snapshot.other_direct_spent},
                "Indirect Costs": {"budget": snapshot.indirect_costs_budget, "spent": snapshot.indirect_costs_spent},
            }
            for cat, data in context["budget_status"].items():
                data["remaining"] = data["budget"] - data["spent"]
                data["pct_used"] = round((data["spent"] / data["budget"] * 100), 1) if data["budget"] else 0
        else:
            # No reconciliation run yet — use baseline estimates from CLAUDE.md
            context = _baseline_budget_context()

        if anomalies:
            context["open_anomalies"] = [
                {"type": a.anomaly_type, "description": a.description, "severity": a.severity}
                for a in anomalies
            ]

        if providers:
            context["recent_provider_payments"] = [
                {
                    "month": p.month,
                    "provider": p.provider,
                    "invoice": p.invoice_amount,
                    "placements": p.placements_reported,
                    "expected": p.expected_amount,
                    "flagged": p.flagged,
                    "cumulative_paid": p.cumulative_paid,
                }
                for p in providers
            ]

        # Include baseline data — prioritize placement summaries and key metrics
        baseline_count = session.query(BaselineData).count()
        if baseline_count > 0:
            baseline_types = session.query(BaselineData.source_file, BaselineData.data_type).distinct().all()
            context["baseline_data"] = {
                "total_rows": baseline_count,
                "files": [{"file": bt[0], "type": bt[1]} for bt in baseline_types],
            }

            # Load placement summary and provider placement data first (most important)
            priority_sheets = ["placement_summary", "provider_placements"]
            priority_rows = session.query(BaselineData).filter(
                BaselineData.sheet_name.in_(priority_sheets)
            ).all()

            if priority_rows:
                context["placement_data"] = [
                    {"sheet": r.sheet_name, "data": r.row_data}
                    for r in priority_rows
                ]

            # Fill remaining context with other baseline rows
            other_rows = session.query(BaselineData).filter(
                ~BaselineData.sheet_name.in_(priority_sheets)
            ).limit(30).all()
            if other_rows:
                context["baseline_sample"] = [
                    {"source": r.source_file, "type": r.data_type, "sheet": r.sheet_name, "data": r.row_data}
                    for r in other_rows
                ]

        # SharePoint file listing info
        context["sharepoint_folders"] = {
            "monthly_uploads": "WJI-Grant-Agent/monthly-uploads",
            "baseline": "WJI-Grant-Agent/baseline",
            "note": "Use /files command to list files, or /reconcile to process monthly files, or /load-baseline to load historical data.",
        }

        return json.dumps(context, indent=2, default=str)

    finally:
        session.close()


async def answer_query(user_message: str, conversation_history: list) -> str:
    """Send user question to Claude with data context and conversation history."""
    data_context = get_latest_data_context()

    messages = conversation_history.copy()
    messages.append({
        "role": "user",
        "content": f"""Current grant data:
{data_context}

Question: {user_message}"""
    })

    response = get_client().messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=1500,
        system=SYSTEM_PROMPT,
        messages=messages,
    )

    answer = response.content[0].text

    # Return updated history (keep last 10 exchanges to manage context)
    updated_history = conversation_history + [
        {"role": "user", "content": f"Question: {user_message}"},
        {"role": "assistant", "content": answer},
    ]
    if len(updated_history) > 20:
        updated_history = updated_history[-20:]

    return answer, updated_history


def format_reconciliation_summary(recon_result: dict) -> str:
    """Format reconciliation results as a Teams-friendly message."""
    month = recon_result["month"]
    summary = recon_result["summary"]
    budget = recon_result["budget_status"]
    anomalies = recon_result["anomalies"]

    lines = [
        f"## Monthly Reconciliation Complete — {month}",
        "",
        "**Transaction Matching**",
    ]
    lines.append(f"- QB → Bank matched: {summary['qb_bank_matched']}")
    lines.append(f"- QB → Credit card matched: {summary['qb_cc_matched']}")
    lines.append(f"- QB unmatched: {summary['qb_unmatched']}")
    lines.append(f"- Bank unmatched: {summary['bank_unmatched']}")
    lines.append(f"- CC unmatched: {summary['cc_unmatched']}")

    lines.append("")
    lines.append("**Budget Status**")
    for cat, data in budget.items():
        bar = "🔴" if data["pct_used"] >= 90 else "🟡" if data["pct_used"] >= 75 else "🟢"
        lines.append(f"- {bar} {cat}: ${data['spent']:,.0f} / ${data['budget']:,.0f} ({data['pct_used']:.1f}%)")

    if recon_result["provider_results"]:
        lines.append("")
        lines.append("**Provider Invoices**")
        for p in recon_result["provider_results"]:
            status = "⚠️ FLAGGED" if p["flagged"] else "✅"
            lines.append(f"- {status} {p['provider']}: {p['placements']} placements × ${p['rate']:,} = ${p['expected_amount']:,.0f} (invoiced: ${p['invoice_amount']:,.0f})")
            for flag in p.get("flags", []):
                lines.append(f"  - ⚠️ {flag}")

    if anomalies:
        lines.append("")
        lines.append(f"**⚠️ Anomalies Detected ({len(anomalies)})**")
        for a in anomalies:
            lines.append(f"- {a['description']}")

    lines.append("")
    lines.append(f"*Processed {summary['total_qb_transactions']} QB transactions. {summary['providers_reviewed']} provider invoices reviewed.*")

    return "\n".join(lines)
