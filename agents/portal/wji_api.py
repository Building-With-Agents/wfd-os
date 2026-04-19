"""
WJI Grant Closeout API.

Endpoints:
  POST /api/wji/upload/placements   multipart Excel (WSAC format)
  POST /api/wji/upload/payments     multipart CSV (QuickBooks export)
  GET  /api/wji/dashboard           aggregate stats + recent uploads
  GET  /api/wji/batches             list of upload batches
  GET  /api/wji/placements          paginated placements
  GET  /api/wji/payments            paginated payments

Run: uvicorn wji_api:app --reload --port 8007
"""
import io
import json
import os
import sys
from datetime import datetime, date
from decimal import Decimal, InvalidOperation

from fastapi import FastAPI, HTTPException, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
import psycopg2
import psycopg2.extras

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../scripts"))
from pgconfig import PG_CONFIG  # noqa: E402

app = FastAPI(title="WJI Grant Closeout API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_conn():
    """Raw DBAPI connection from the wfdos_common.db engine pool (#22c).

    Returns a psycopg2-compatible connection; conn.close() returns it
    to the shared pool instead of actually closing the socket.
    """
    from wfdos_common.db import get_engine
    return get_engine().raw_connection()


# ---------------------------------------------------------------------------
# Helpers: column name normalization + value coercion
# ---------------------------------------------------------------------------

def _norm(s: str) -> str:
    """Normalize a header: lower, alphanumeric only."""
    return "".join(ch for ch in (s or "").lower() if ch.isalnum())


# Case-insensitive, whitespace-insensitive header matching for WSAC placements.
PLACEMENT_COLUMN_ALIASES: dict[str, list[str]] = {
    "student_name": ["studentname", "name", "fullname", "participantname", "learner"],
    "student_id":   ["studentid", "id", "participantid", "ssid"],
    "program":      ["program", "programname", "track", "pathway", "course"],
    "placement_date": ["placementdate", "hiredate", "startdate", "dateofplacement", "placed"],
    "employer":     ["employer", "company", "employername", "hiringemployer"],
    "job_title":    ["jobtitle", "title", "position", "role", "occupation"],
    "wage":         ["wage", "hourlywage", "pay", "payrate", "hourlyrate", "wagerate", "salary"],
    "wage_basis":   ["wagebasis", "paytype", "salarytype"],
    "hours_per_week": ["hoursperweek", "weeklyhours", "hours"],
    "retention_status": ["retentionstatus", "retention", "employmentstatus", "status"],
    "naics_code":   ["naics", "naicscode", "industrycode"],
    "region":       ["region", "county", "workforceregion", "area"],
}

PAYMENT_COLUMN_ALIASES: dict[str, list[str]] = {
    "payment_date": ["date", "transactiondate", "paymentdate", "postdate", "postingdate"],
    "vendor":       ["vendor", "payee", "name", "vendorname", "recipient"],
    "amount":       ["amount", "paid", "paidamount", "total", "debit"],
    "category":     ["category", "class", "type", "expensecategory"],
    "account":      ["account", "accountname", "glaccount", "ledgeraccount"],
    "memo":         ["memo", "description", "note", "details", "memodescription"],
    "check_number": ["num", "number", "checknum", "checknumber", "reference", "ref"],
}


def _match_column(target: str, headers_normed: dict[str, str], aliases: dict[str, list[str]]) -> str | None:
    """Given a canonical field name, find the matching raw header. Returns raw header or None."""
    for alias in aliases.get(target, []):
        if alias in headers_normed:
            return headers_normed[alias]
    # fallback: exact match on canonical name
    if _norm(target) in headers_normed:
        return headers_normed[_norm(target)]
    return None


def _coerce_date(v) -> date | None:
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v
    if isinstance(v, datetime):
        return v.date()
    s = str(v).strip()
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y", "%Y/%m/%d", "%d-%b-%Y", "%b %d, %Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def _coerce_decimal(v) -> Decimal | None:
    if v is None or v == "":
        return None
    if isinstance(v, (int, float, Decimal)):
        try:
            return Decimal(str(v))
        except (InvalidOperation, ValueError):
            return None
    s = str(v).strip().replace("$", "").replace(",", "").replace("(", "-").replace(")", "")
    if not s:
        return None
    try:
        return Decimal(s)
    except (InvalidOperation, ValueError):
        return None


def _coerce_str(v, max_len: int | None = None) -> str | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    return s[:max_len] if max_len else s


def _row_to_dict_json_safe(row: dict) -> dict:
    """Convert a row dict into something JSON-serializable for jsonb storage."""
    out = {}
    for k, v in row.items():
        if v is None:
            out[k] = None
        elif isinstance(v, (str, int, float, bool)):
            out[k] = v
        elif isinstance(v, Decimal):
            out[k] = str(v)
        elif isinstance(v, (date, datetime)):
            out[k] = v.isoformat()
        else:
            out[k] = str(v)
    return out


# ---------------------------------------------------------------------------
# POST /api/wji/upload/placements  (Excel, WSAC format)
# ---------------------------------------------------------------------------

@app.post("/api/wji/upload/placements")
async def upload_placements(
    file: UploadFile = File(...),
    uploaded_by: str = Query("internal"),
):
    """Parse a WSAC placement Excel file and load into wji_placements.

    Accepts .xlsx or .xls. Header detection is flexible: scans the first
    sheet, treats row 1 as headers, and maps columns via PLACEMENT_COLUMN_ALIASES.
    Unknown columns are preserved in raw_data (jsonb).
    """
    if not file.filename or not file.filename.lower().endswith((".xlsx", ".xls", ".xlsm")):
        raise HTTPException(status_code=400, detail="File must be .xlsx, .xls, or .xlsm")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    # Parse Excel
    import openpyxl
    try:
        wb = openpyxl.load_workbook(io.BytesIO(content), data_only=True, read_only=True)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not read Excel file: {e}")

    ws = wb.active
    rows = ws.iter_rows(values_only=True)
    try:
        header_row = next(rows)
    except StopIteration:
        raise HTTPException(status_code=400, detail="Empty worksheet")

    headers = [str(h).strip() if h is not None else "" for h in header_row]
    headers_normed = {_norm(h): h for h in headers if h}
    # Build canonical_field -> header_raw map
    col_map: dict[str, str] = {}
    for canonical in PLACEMENT_COLUMN_ALIASES:
        matched = _match_column(canonical, headers_normed, PLACEMENT_COLUMN_ALIASES)
        if matched:
            col_map[canonical] = matched

    # Create batch
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO wji_upload_batches (upload_type, filename, uploaded_by, status)
        VALUES ('placements', %s, %s, 'processing')
        RETURNING id
    """, (file.filename, uploaded_by))
    batch_id = cur.fetchone()[0]
    conn.commit()

    success = 0
    errors: list[dict] = []
    row_num = 1  # header is row 1

    for raw_row in rows:
        row_num += 1
        if raw_row is None or all(v is None or v == "" for v in raw_row):
            continue
        row_dict = {headers[i]: raw_row[i] if i < len(raw_row) else None for i in range(len(headers))}

        try:
            values = {canonical: row_dict.get(raw_header) for canonical, raw_header in col_map.items()}
            cur.execute("""
                INSERT INTO wji_placements (
                    batch_id, source_row_num,
                    student_name, student_id, program, placement_date,
                    employer, job_title, wage, wage_basis, hours_per_week,
                    retention_status, naics_code, region, raw_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                batch_id,
                row_num,
                _coerce_str(values.get("student_name"), 200),
                _coerce_str(values.get("student_id"), 100),
                _coerce_str(values.get("program"), 200),
                _coerce_date(values.get("placement_date")),
                _coerce_str(values.get("employer"), 300),
                _coerce_str(values.get("job_title"), 200),
                _coerce_decimal(values.get("wage")),
                _coerce_str(values.get("wage_basis"), 32),
                _coerce_decimal(values.get("hours_per_week")),
                _coerce_str(values.get("retention_status"), 50),
                _coerce_str(values.get("naics_code"), 10),
                _coerce_str(values.get("region"), 100),
                json.dumps(_row_to_dict_json_safe(row_dict)),
            ))
            success += 1
        except Exception as e:
            errors.append({"row": row_num, "error": f"{type(e).__name__}: {e}"})
            conn.rollback()
            # Re-fetch batch id because rollback killed transaction state
            cur = conn.cursor()
            continue

    total_rows = row_num - 1  # minus header
    status = "processed" if not errors else ("partial" if success > 0 else "failed")
    cur.execute("""
        UPDATE wji_upload_batches
        SET row_count = %s, success_count = %s, error_count = %s, errors = %s, status = %s
        WHERE id = %s
    """, (total_rows, success, len(errors), json.dumps(errors), status, batch_id))
    conn.commit()
    conn.close()

    return {
        "batch_id": batch_id,
        "filename": file.filename,
        "total_rows": total_rows,
        "success_count": success,
        "error_count": len(errors),
        "status": status,
        "column_mapping": col_map,
        "unmapped_headers": [h for h in headers if h and h not in col_map.values()],
        "errors": errors[:20],
    }


# ---------------------------------------------------------------------------
# POST /api/wji/upload/payments  (CSV, QuickBooks export)
# ---------------------------------------------------------------------------

@app.post("/api/wji/upload/payments")
async def upload_payments(
    file: UploadFile = File(...),
    uploaded_by: str = Query("internal"),
):
    """Parse a QuickBooks CSV payment export into wji_payments.

    Accepts .csv. Row 1 = headers; maps via PAYMENT_COLUMN_ALIASES.
    Negative amounts kept as-is (QB refunds appear negative).
    """
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="File must be .csv")

    content = await file.read()
    if not content:
        raise HTTPException(status_code=400, detail="Empty file")

    # Decode — try utf-8, fall back to cp1252 (QB often exports cp1252)
    text: str | None = None
    for enc in ("utf-8-sig", "utf-8", "cp1252", "latin-1"):
        try:
            text = content.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise HTTPException(status_code=400, detail="Could not decode file as text")

    import csv as csvmod
    reader = csvmod.reader(io.StringIO(text))
    try:
        header_row = next(reader)
    except StopIteration:
        raise HTTPException(status_code=400, detail="Empty CSV")

    headers = [h.strip() for h in header_row]
    headers_normed = {_norm(h): h for h in headers if h}
    col_map: dict[str, str] = {}
    for canonical in PAYMENT_COLUMN_ALIASES:
        matched = _match_column(canonical, headers_normed, PAYMENT_COLUMN_ALIASES)
        if matched:
            col_map[canonical] = matched

    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO wji_upload_batches (upload_type, filename, uploaded_by, status)
        VALUES ('payments', %s, %s, 'processing')
        RETURNING id
    """, (file.filename, uploaded_by))
    batch_id = cur.fetchone()[0]
    conn.commit()

    success = 0
    errors: list[dict] = []
    row_num = 1

    for raw in reader:
        row_num += 1
        if not raw or all(v == "" for v in raw):
            continue
        row_dict = {headers[i]: (raw[i] if i < len(raw) else "") for i in range(len(headers))}

        try:
            values = {canonical: row_dict.get(raw_header) for canonical, raw_header in col_map.items()}
            cur.execute("""
                INSERT INTO wji_payments (
                    batch_id, source_row_num,
                    payment_date, vendor, amount, category, account, memo, check_number, raw_data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                batch_id,
                row_num,
                _coerce_date(values.get("payment_date")),
                _coerce_str(values.get("vendor"), 300),
                _coerce_decimal(values.get("amount")),
                _coerce_str(values.get("category"), 200),
                _coerce_str(values.get("account"), 200),
                _coerce_str(values.get("memo")),
                _coerce_str(values.get("check_number"), 50),
                json.dumps(_row_to_dict_json_safe(row_dict)),
            ))
            success += 1
        except Exception as e:
            errors.append({"row": row_num, "error": f"{type(e).__name__}: {e}"})
            conn.rollback()
            cur = conn.cursor()
            continue

    total_rows = row_num - 1
    status = "processed" if not errors else ("partial" if success > 0 else "failed")
    cur.execute("""
        UPDATE wji_upload_batches
        SET row_count = %s, success_count = %s, error_count = %s, errors = %s, status = %s
        WHERE id = %s
    """, (total_rows, success, len(errors), json.dumps(errors), status, batch_id))
    conn.commit()
    conn.close()

    return {
        "batch_id": batch_id,
        "filename": file.filename,
        "total_rows": total_rows,
        "success_count": success,
        "error_count": len(errors),
        "status": status,
        "column_mapping": col_map,
        "unmapped_headers": [h for h in headers if h and h not in col_map.values()],
        "errors": errors[:20],
    }


# ---------------------------------------------------------------------------
# GET /api/wji/dashboard
# ---------------------------------------------------------------------------

@app.get("/api/wji/dashboard")
def get_dashboard():
    """Aggregate WJI grant close-out stats + recent uploads."""
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    # Placement totals
    cur.execute("""
        SELECT
            count(*)::int AS total_placements,
            count(DISTINCT student_name)::int AS unique_students,
            count(DISTINCT employer)::int AS unique_employers,
            count(DISTINCT program)::int AS unique_programs,
            AVG(wage)::numeric(10,2) AS avg_wage,
            MAX(placement_date) AS latest_placement
        FROM wji_placements
    """)
    placements = dict(cur.fetchone())

    # By program
    cur.execute("""
        SELECT program, count(*)::int AS placements, AVG(wage)::numeric(10,2) AS avg_wage
        FROM wji_placements
        WHERE program IS NOT NULL
        GROUP BY program
        ORDER BY placements DESC
        LIMIT 10
    """)
    by_program = [dict(r) for r in cur.fetchall()]

    # By month
    cur.execute("""
        SELECT
            to_char(placement_date, 'YYYY-MM') AS month,
            count(*)::int AS placements
        FROM wji_placements
        WHERE placement_date IS NOT NULL
        GROUP BY 1
        ORDER BY 1 DESC
        LIMIT 12
    """)
    placements_by_month = [dict(r) for r in cur.fetchall()]

    # Payment totals
    cur.execute("""
        SELECT
            count(*)::int AS total_payments,
            SUM(amount)::numeric(12,2) AS total_spent,
            count(DISTINCT vendor)::int AS unique_vendors,
            MAX(payment_date) AS latest_payment
        FROM wji_payments
    """)
    payments = dict(cur.fetchone())

    cur.execute("""
        SELECT category, count(*)::int AS payments, SUM(amount)::numeric(12,2) AS total
        FROM wji_payments
        WHERE category IS NOT NULL
        GROUP BY category
        ORDER BY total DESC NULLS LAST
        LIMIT 10
    """)
    by_category = [dict(r) for r in cur.fetchall()]

    # Recent uploads
    cur.execute("""
        SELECT id, upload_type, filename, uploaded_by, uploaded_at,
               row_count, success_count, error_count, status
        FROM wji_upload_batches
        ORDER BY uploaded_at DESC
        LIMIT 10
    """)
    recent_uploads = [dict(r) for r in cur.fetchall()]

    conn.close()

    # ISO-serialize dates/decimals
    def _ser(d):
        for k, v in list(d.items()):
            if isinstance(v, (date, datetime)):
                d[k] = v.isoformat()
            elif isinstance(v, Decimal):
                d[k] = float(v)
        return d

    return {
        "placements_summary": _ser(placements),
        "payments_summary": _ser(payments),
        "placements_by_program": [_ser(r) for r in by_program],
        "placements_by_month": [_ser(r) for r in placements_by_month],
        "payments_by_category": [_ser(r) for r in by_category],
        "recent_uploads": [_ser(r) for r in recent_uploads],
    }


@app.get("/api/wji/placements")
def list_placements(limit: int = Query(50, le=500), offset: int = 0, batch_id: int | None = None):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    where = "WHERE batch_id = %s" if batch_id else ""
    params = (batch_id,) if batch_id else ()
    cur.execute(f"SELECT count(*)::int AS c FROM wji_placements {where}", params)
    total = cur.fetchone()["c"]
    cur.execute(f"""
        SELECT id, batch_id, student_name, student_id, program, placement_date,
               employer, job_title, wage, hours_per_week, retention_status, region
        FROM wji_placements
        {where}
        ORDER BY placement_date DESC NULLS LAST, id DESC
        LIMIT %s OFFSET %s
    """, params + (limit, offset))
    rows = []
    for r in cur.fetchall():
        d = dict(r)
        for k, v in list(d.items()):
            if isinstance(v, (date, datetime)):
                d[k] = v.isoformat()
            elif isinstance(v, Decimal):
                d[k] = float(v)
        rows.append(d)
    conn.close()
    return {"total": total, "limit": limit, "offset": offset, "rows": rows}


@app.get("/api/wji/payments")
def list_payments(limit: int = Query(50, le=500), offset: int = 0, batch_id: int | None = None):
    conn = get_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    where = "WHERE batch_id = %s" if batch_id else ""
    params = (batch_id,) if batch_id else ()
    cur.execute(f"SELECT count(*)::int AS c FROM wji_payments {where}", params)
    total = cur.fetchone()["c"]
    cur.execute(f"""
        SELECT id, batch_id, payment_date, vendor, amount, category, account, memo, check_number
        FROM wji_payments
        {where}
        ORDER BY payment_date DESC NULLS LAST, id DESC
        LIMIT %s OFFSET %s
    """, params + (limit, offset))
    rows = []
    for r in cur.fetchall():
        d = dict(r)
        for k, v in list(d.items()):
            if isinstance(v, (date, datetime)):
                d[k] = v.isoformat()
            elif isinstance(v, Decimal):
                d[k] = float(v)
        rows.append(d)
    conn.close()
    return {"total": total, "limit": limit, "offset": offset, "rows": rows}


@app.delete("/api/wji/batches/{batch_id}")
def delete_batch(batch_id: int):
    """Undo an upload — deletes the batch and all its rows (cascade)."""
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM wji_upload_batches WHERE id = %s RETURNING upload_type, filename", (batch_id,))
    row = cur.fetchone()
    conn.commit()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Batch not found")
    return {"success": True, "batch_id": batch_id, "upload_type": row[0], "filename": row[1]}


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "wji-api", "port": 8007}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8007)
