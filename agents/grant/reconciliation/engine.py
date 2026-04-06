import pandas as pd
from datetime import date
from ingestion.file_parser import PROVIDER_RATES, TERMINATED_PROVIDERS, BUDGET


# Budget category keywords for auto-categorization
CATEGORY_KEYWORDS = {
    "Personnel Salaries": ["salary", "salaries", "payroll", "wages", "wage"],
    "Personnel Benefits": ["benefits", "insurance", "401k", "retirement", "fica", "health"],
    "GJC Contractors": ["ada", "vets2tech", "apprenti", "code day", "codeday", "per scholas", "perscholas", "year up", "yearup"],
    "CFA Contractors": ["ai engage", "vargo", "contractor", "consulting"],
    "Indirect Costs": ["indirect", "overhead", "administrative"],
    "Other Direct Costs": [],  # catch-all
}


def categorize_expense(vendor: str, description: str) -> str:
    text = f"{vendor or ''} {description or ''}".lower()
    for category, keywords in CATEGORY_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return category
    return "Other Direct Costs"


def match_transactions(qb: pd.DataFrame, bank: pd.DataFrame, cc: pd.DataFrame) -> dict:
    """
    Match QB transactions against bank and credit card statements.
    Returns matched/unmatched sets and flagged items.
    """
    results = {
        "qb_to_bank_matched": [],
        "qb_to_cc_matched": [],
        "qb_unmatched": [],
        "bank_unmatched": [],
        "cc_unmatched": [],
        "cc_over_1000_not_in_qb": [],
    }

    qb_matched = set()
    bank_matched = set()
    cc_matched = set()

    # Match QB to bank by amount (within $1 tolerance)
    for qi, qrow in qb.iterrows():
        matched = False
        for bi, brow in bank.iterrows():
            if bi in bank_matched:
                continue
            if abs(float(qrow.get("amount", 0)) - float(brow.get("amount", 0))) < 1.0:
                results["qb_to_bank_matched"].append({
                    "qb_vendor": qrow.get("vendor", ""),
                    "qb_amount": qrow.get("amount"),
                    "bank_description": brow.get("description", ""),
                    "bank_amount": brow.get("amount"),
                })
                qb_matched.add(qi)
                bank_matched.add(bi)
                matched = True
                break

        if not matched:
            # Try credit card
            for ci, crow in cc.iterrows():
                if ci in cc_matched:
                    continue
                if abs(float(qrow.get("amount", 0)) - float(crow.get("amount", 0))) < 1.0:
                    results["qb_to_cc_matched"].append({
                        "qb_vendor": qrow.get("vendor", ""),
                        "qb_amount": qrow.get("amount"),
                        "cc_description": crow.get("description", ""),
                        "cc_amount": crow.get("amount"),
                    })
                    qb_matched.add(qi)
                    cc_matched.add(ci)
                    matched = True
                    break

        if not matched:
            results["qb_unmatched"].append({
                "vendor": qrow.get("vendor", ""),
                "amount": qrow.get("amount"),
                "date": str(qrow.get("date", "")),
                "description": qrow.get("description", ""),
            })

    # Unmatched bank transactions
    for bi, brow in bank.iterrows():
        if bi not in bank_matched:
            results["bank_unmatched"].append({
                "description": brow.get("description", ""),
                "amount": brow.get("amount"),
                "date": str(brow.get("date", "")),
            })

    # Unmatched CC + flag over $1000
    for ci, crow in cc.iterrows():
        if ci not in cc_matched:
            row = {
                "description": crow.get("description", ""),
                "amount": crow.get("amount"),
                "date": str(crow.get("date", "")),
            }
            results["cc_unmatched"].append(row)
            if float(crow.get("amount", 0)) > 1000:
                results["cc_over_1000_not_in_qb"].append(row)

    return results


def reconcile_providers(invoices: list[dict], wsac: pd.DataFrame, month: str) -> list[dict]:
    """
    For each provider invoice, check placements and flag discrepancies.
    """
    results = []
    for invoice in invoices:
        vendor = invoice.get("vendor")
        if not vendor:
            continue

        rate = PROVIDER_RATES.get(vendor)
        if not rate:
            continue

        invoice_amount = invoice.get("amount", 0)

        # Look up WSAC placements
        placements = 0
        if "provider" in wsac.columns and "placements" in wsac.columns:
            match = wsac[wsac["provider"].str.contains(vendor, case=False, na=False)]
            if not match.empty:
                placements = int(match["placements"].sum())

        expected = placements * rate
        variance = invoice_amount - expected if invoice_amount else None

        flags = []
        if placements == 0 and invoice_amount and invoice_amount > 0:
            flags.append("Payment with zero placements reported")
        if variance is not None and abs(variance) > 500:
            flags.append(f"Invoice ${invoice_amount:,.2f} differs from expected ${expected:,.2f} by ${abs(variance):,.2f}")
        if vendor in TERMINATED_PROVIDERS:
            flags.append(f"{vendor} is a terminated provider — no further payments authorized")

        results.append({
            "month": month,
            "provider": vendor,
            "invoice_amount": invoice_amount,
            "placements": placements,
            "rate": rate,
            "expected_amount": expected,
            "variance": variance,
            "flagged": len(flags) > 0,
            "flags": flags,
        })

    return results


def calculate_budget_status(qb: pd.DataFrame, month: str) -> dict:
    """
    Categorize QB expenses and compute remaining budget per category.
    """
    status = {}
    for category, budget in BUDGET.items():
        status[category] = {"budget": budget, "spent": 0.0, "remaining": budget, "pct_used": 0.0}

    for _, row in qb.iterrows():
        cat = categorize_expense(str(row.get("vendor", "")), str(row.get("description", "")))
        amount = float(row.get("amount", 0) or 0)
        if cat in status:
            status[cat]["spent"] += amount

    for cat in status:
        status[cat]["remaining"] = status[cat]["budget"] - status[cat]["spent"]
        if status[cat]["budget"] > 0:
            status[cat]["pct_used"] = (status[cat]["spent"] / status[cat]["budget"]) * 100

    return status


def detect_anomalies(budget_status: dict, provider_results: list, match_results: dict, month: str) -> list[dict]:
    """Run all anomaly detection rules and return flagged items."""
    anomalies = []

    # Budget category exceeding 90%
    for cat, data in budget_status.items():
        if data["pct_used"] >= 90:
            anomalies.append({
                "type": "budget_threshold",
                "severity": "critical" if data["pct_used"] >= 100 else "warning",
                "description": f"{cat} is at {data['pct_used']:.1f}% of budget (${data['spent']:,.0f} of ${data['budget']:,.0f})",
            })

    # Provider anomalies
    for p in provider_results:
        for flag in p.get("flags", []):
            anomalies.append({
                "type": "provider_invoice",
                "severity": "warning",
                "description": f"{p['provider']}: {flag}",
            })

    # CC charges over $1000 not in QB
    for item in match_results.get("cc_over_1000_not_in_qb", []):
        anomalies.append({
            "type": "credit_card_unmatched",
            "severity": "warning",
            "description": f"Credit card charge ${item['amount']:,.2f} — {item['description']} — not found in QuickBooks",
        })

    return anomalies


def run_full_reconciliation(files: dict, month: str) -> dict:
    """
    Main entry point. Takes dict of {filename: bytes}, returns full reconciliation result.
    """
    from ingestion.file_parser import (
        parse_quickbooks_csv, parse_bank_csv, parse_credit_card_csv,
        parse_invoice_pdf, parse_wsac_excel, detect_file_type
    )

    qb_df = pd.DataFrame()
    bank_df = pd.DataFrame()
    cc_df = pd.DataFrame()
    invoices = []
    wsac_df = pd.DataFrame()

    for filename, content in files.items():
        ftype = detect_file_type(filename)
        if ftype == "quickbooks":
            qb_df = parse_quickbooks_csv(content)
        elif ftype == "bank":
            bank_df = parse_bank_csv(content)
        elif ftype == "credit_card":
            cc_df = parse_credit_card_csv(content)
        elif ftype == "invoice":
            invoices.append(parse_invoice_pdf(content, filename))
        elif ftype == "wsac":
            wsac_df = parse_wsac_excel(content)

    match_results = match_transactions(qb_df, bank_df, cc_df)
    provider_results = reconcile_providers(invoices, wsac_df, month)
    budget_status = calculate_budget_status(qb_df, month)
    anomalies = detect_anomalies(budget_status, provider_results, match_results, month)

    return {
        "month": month,
        "budget_status": budget_status,
        "match_results": match_results,
        "provider_results": provider_results,
        "anomalies": anomalies,
        "summary": {
            "total_qb_transactions": len(qb_df),
            "qb_bank_matched": len(match_results["qb_to_bank_matched"]),
            "qb_cc_matched": len(match_results["qb_to_cc_matched"]),
            "qb_unmatched": len(match_results["qb_unmatched"]),
            "bank_unmatched": len(match_results["bank_unmatched"]),
            "cc_unmatched": len(match_results["cc_unmatched"]),
            "providers_reviewed": len(provider_results),
            "providers_flagged": sum(1 for p in provider_results if p["flagged"]),
            "anomalies_detected": len(anomalies),
        },
    }
