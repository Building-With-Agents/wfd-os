import io
import pandas as pd
import pdfplumber


# Provider payment rates
PROVIDER_RATES = {
    "Ada": 2500,
    "Vets2Tech": 2500,
    "Apprenti": 2500,
    "Code Day": 3222,
    "CodeDay": 3222,
    "Per Scholas": 3443,
    "PerScholas": 3443,
    "Year Up": 2623,
    "YearUp": 2623,
}

TERMINATED_PROVIDERS = {"WABS", "NCESD", "Riipen"}

# Budget categories and Amendment 1 baselines
BUDGET = {
    "GJC Contractors": 2315623,
    "CFA Contractors": 1020823,
    "Personnel Salaries": 1097662,
    "Personnel Benefits": 173170,
    "Other Direct Costs": 88921,
    "Indirect Costs": 178799,
}


def parse_quickbooks_csv(data: bytes) -> pd.DataFrame:
    """Parse QuickBooks Expenses by Vendor Summary CSV."""
    df = pd.read_csv(io.BytesIO(data))
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    # Normalize common QB column names
    rename_map = {}
    for col in df.columns:
        if "vendor" in col or "name" in col:
            rename_map[col] = "vendor"
        elif "amount" in col or "total" in col:
            rename_map[col] = "amount"
        elif "date" in col:
            rename_map[col] = "date"
        elif "memo" in col or "description" in col or "account" in col:
            rename_map[col] = "description"
    df = df.rename(columns=rename_map)

    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"].astype(str).str.replace(r"[\$,()]", "", regex=True), errors="coerce")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df["source"] = "quickbooks"
    return df.dropna(subset=["amount"])


def parse_bank_csv(data: bytes) -> pd.DataFrame:
    """Parse Bank of America bank statement CSV."""
    df = pd.read_csv(io.BytesIO(data))
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    rename_map = {}
    for col in df.columns:
        if "description" in col or "payee" in col or "memo" in col:
            rename_map[col] = "description"
        elif "amount" in col or "debit" in col or "credit" in col:
            rename_map[col] = "amount"
        elif "date" in col or "posted" in col:
            rename_map[col] = "date"
    df = df.rename(columns=rename_map)

    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"].astype(str).str.replace(r"[\$,]", "", regex=True), errors="coerce")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df["source"] = "bank"
    return df.dropna(subset=["amount"])


def parse_credit_card_csv(data: bytes) -> pd.DataFrame:
    """Parse Bank of America credit card statement CSV."""
    df = pd.read_csv(io.BytesIO(data))
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    rename_map = {}
    for col in df.columns:
        if "description" in col or "merchant" in col or "payee" in col:
            rename_map[col] = "description"
        elif "amount" in col:
            rename_map[col] = "amount"
        elif "date" in col or "posted" in col or "transaction" in col:
            rename_map[col] = "date"
    df = df.rename(columns=rename_map)

    if "amount" in df.columns:
        df["amount"] = pd.to_numeric(df["amount"].astype(str).str.replace(r"[\$,]", "", regex=True), errors="coerce")
    if "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df["source"] = "credit_card"
    return df.dropna(subset=["amount"])


def parse_invoice_pdf(data: bytes, filename: str) -> dict:
    """Extract key fields from a provider invoice PDF."""
    result = {"filename": filename, "vendor": None, "amount": None, "period": None, "raw_text": ""}
    with pdfplumber.open(io.BytesIO(data)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    result["raw_text"] = text

    # Try to identify provider name
    for provider in list(PROVIDER_RATES.keys()) + list(TERMINATED_PROVIDERS):
        if provider.lower() in text.lower():
            result["vendor"] = provider
            break

    # Try to extract dollar amount (largest $ value is likely the invoice total)
    import re
    amounts = re.findall(r"\$[\d,]+\.?\d*", text)
    if amounts:
        parsed = [float(a.replace("$", "").replace(",", "")) for a in amounts]
        result["amount"] = max(parsed)

    return result


def parse_wsac_excel(data: bytes) -> pd.DataFrame:
    """Parse WSAC placement data Excel file."""
    df = pd.read_excel(io.BytesIO(data))
    df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

    rename_map = {}
    for col in df.columns:
        if "provider" in col or "vendor" in col or "organization" in col or "agency" in col:
            rename_map[col] = "provider"
        elif "placement" in col or "count" in col or "total" in col:
            rename_map[col] = "placements"
        elif "date" in col or "period" in col or "month" in col:
            rename_map[col] = "period"
    df = df.rename(columns=rename_map)

    if "placements" in df.columns:
        df["placements"] = pd.to_numeric(df["placements"], errors="coerce").fillna(0).astype(int)

    return df


def detect_file_type(filename: str) -> str:
    """Guess file type from filename."""
    name_lower = filename.lower()
    if "quickbooks" in name_lower or "qb" in name_lower or "expense" in name_lower or "vendor" in name_lower:
        return "quickbooks"
    elif "bank" in name_lower and "credit" not in name_lower:
        return "bank"
    elif "credit" in name_lower or "card" in name_lower:
        return "credit_card"
    elif name_lower.endswith(".pdf"):
        return "invoice"
    elif "wsac" in name_lower or "placement" in name_lower or name_lower.endswith(".xlsx"):
        return "wsac"
    return "unknown"
