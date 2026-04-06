"""
WFD OS Migration Script — Dataverse -> Local PostgreSQL
Steps 2-7: contacts, accounts, studentdetails, lightcastjobs, journeys, programs

READ ONLY from Dataverse. WRITE ONLY to local PostgreSQL.
"""

import os
import json
import requests
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime, timezone
from dotenv import load_dotenv

# Load environment
load_dotenv("C:/Users/ritub/projects/wfd-os/.env")

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
DYNAMICS_URL = os.getenv("DYNAMICS_PRIMARY_URL")

from pgconfig import PG_CONFIG
PG_HOST = PG_CONFIG["host"]
PG_DB = PG_CONFIG["database"]
PG_USER = PG_CONFIG["user"]
PG_PASS = PG_CONFIG["password"]
PG_PORT = PG_CONFIG["port"]

MIGRATION_DATE = datetime.now(timezone.utc).isoformat()


def get_token():
    """Get OAuth token for Dataverse API."""
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": f"{DYNAMICS_URL}/.default"
    }
    r = requests.post(url, data=data)
    r.raise_for_status()
    return r.json()["access_token"]


def fetch_all(token, entity_set, select=None, top=5000):
    """Fetch all records from a Dataverse entity set with pagination."""
    headers = {
        "Authorization": f"Bearer {token}",
        "OData-MaxVersion": "4.0",
        "OData-Version": "4.0",
        "Accept": "application/json",
        "Prefer": "odata.maxpagesize=1000"
    }
    url = f"{DYNAMICS_URL}/api/data/v9.2/{entity_set}"
    params = {}
    if select:
        params["$select"] = select

    all_records = []
    page = 0
    while url and len(all_records) < top:
        page += 1
        print(f"  Fetching {entity_set} page {page}...")
        r = requests.get(url, headers=headers, params=params if page == 1 else None)
        r.raise_for_status()
        data = r.json()
        records = data.get("value", [])
        all_records.extend(records)
        url = data.get("@odata.nextLink")
        params = {}  # nextLink includes params

    print(f"  Total: {len(all_records)} records from {entity_set}")
    return all_records


def get_pg_conn():
    """Get PostgreSQL connection."""
    return psycopg2.connect(
        host=PG_HOST, database=PG_DB, user=PG_USER,
        password=PG_PASS, port=PG_PORT
    )


def safe(val, maxlen=None):
    """Safely extract a string value, truncate if needed."""
    if val is None:
        return None
    s = str(val).strip()
    if s == "":
        return None
    if maxlen:
        s = s[:maxlen]
    return s


def safe_bool(val):
    """Convert Dataverse boolean to Python bool."""
    if val is None:
        return None
    if isinstance(val, bool):
        return val
    if isinstance(val, (int, float)):
        return bool(val)
    return None


# ============================================================
# STEP 2: Migrate contacts -> students
# ============================================================
def migrate_contacts(token, conn):
    print("\n=== STEP 2: Migrating contacts -> students ===")

    # Fetch all contacts without field filter — Dataverse will return all fields
    contacts = fetch_all(token, "contacts")

    if not contacts:
        print("  No contacts found!")
        return

    cur = conn.cursor()
    inserted = 0
    skipped = 0

    for c in contacts:
        contact_id = c.get("contactid")
        full_name = safe(c.get("fullname"), 255)

        if not full_name:
            # Try constructing from first + last
            fn = safe(c.get("firstname"), 100) or ""
            ln = safe(c.get("lastname"), 100) or ""
            full_name = f"{fn} {ln}".strip()

        if not full_name:
            skipped += 1
            continue

        # Build legacy_data from all fields not mapped to columns
        legacy_fields = {}
        for k, v in c.items():
            if v is not None and k not in (
                "contactid", "fullname", "firstname", "lastname",
                "emailaddress1", "telephone1", "mobilephone",
                "address1_city", "address1_stateorprovince", "address1_postalcode",
                "gendercode", "new_ethnicity", "new_veteranstatus",
                "new_linkedin", "new_github", "new_portfolio",
                "new_college", "new_degree", "new_fieldofstudy", "new_graduationyear",
                "new_enrollmentstatus", "new_programstage",
                "createdon", "modifiedon", "statecode"
            ) and not k.startswith("@") and not k.startswith("_"):
                legacy_fields[k] = v

        # Determine pipeline_status from statecode
        statecode = c.get("statecode")
        enrollment = safe(c.get("new_enrollmentstatus"), 50)
        if statecode == 1:
            pipeline_status = "inactive"
        elif enrollment:
            pipeline_status = enrollment.lower()
        else:
            pipeline_status = "unknown"

        # Determine engagement level from modified date
        modified = c.get("modifiedon")
        engagement = "none"
        if modified:
            try:
                mod_dt = datetime.fromisoformat(modified.replace("Z", "+00:00"))
                days_ago = (datetime.now(timezone.utc) - mod_dt).days
                if days_ago < 90:
                    engagement = "high"
                elif days_ago < 365:
                    engagement = "medium"
                elif days_ago < 730:
                    engagement = "low"
            except:
                pass

        gender_code = c.get("gendercode")
        gender_map = {1: "Male", 2: "Female", 3: "Non-binary"}
        gender = gender_map.get(gender_code)

        try:
            cur.execute("""
                INSERT INTO students (
                    full_name, email, phone,
                    gender, ethnicity, veteran_status,
                    city, state, zipcode,
                    institution, degree, field_of_study, graduation_year,
                    linkedin_url, github_url, portfolio_url,
                    pipeline_status, program_stage_reached,
                    source_system, original_record_id, migration_date,
                    data_quality, engagement_level, last_active_date,
                    re_engagement_eligible, re_engagement_status,
                    legacy_data, created_at, updated_at
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s, %s
                )
            """, (
                full_name,
                safe(c.get("emailaddress1"), 255),
                safe(c.get("telephone1") or c.get("mobilephone"), 50),
                gender,
                safe(c.get("new_ethnicity"), 100),
                safe_bool(c.get("new_veteranstatus")),
                safe(c.get("address1_city"), 100),
                safe(c.get("address1_stateorprovince"), 50),
                safe(c.get("address1_postalcode"), 20),
                safe(c.get("new_college"), 255),
                safe(c.get("new_degree"), 100),
                safe(c.get("new_fieldofstudy"), 255),
                c.get("new_graduationyear"),
                safe(c.get("new_linkedin"), 500),
                safe(c.get("new_github"), 500),
                safe(c.get("new_portfolio"), 500),
                pipeline_status,
                safe(c.get("new_programstage"), 100),
                "dataverse",
                contact_id,
                MIGRATION_DATE,
                "partial",  # will be recalculated after full merge
                engagement,
                modified,
                True if engagement in ("low", "medium") and pipeline_status not in ("placed", "alumni") else False,
                None,
                json.dumps(legacy_fields) if legacy_fields else None,
                c.get("createdon"),
                c.get("modifiedon") or c.get("createdon"),
            ))
            inserted += 1
        except Exception as e:
            print(f"  Error inserting {contact_id}: {e}")
            conn.rollback()
            continue

    conn.commit()
    print(f"  Inserted: {inserted}, Skipped (no name): {skipped}")


# ============================================================
# STEP 3: Migrate accounts -> employers
# ============================================================
def migrate_accounts(token, conn):
    print("\n=== STEP 3: Migrating accounts -> employers ===")

    select_fields = ",".join([
        "accountid", "name", "industrycode",
        "websiteurl", "address1_city", "address1_stateorprovince",
        "address1_postalcode", "numberofemployees", "description",
        "primarycontactid", "telephone1", "emailaddress1",
        "createdon", "modifiedon"
    ])

    accounts = fetch_all(token, "accounts", select=select_fields)

    if not accounts:
        print("  No accounts found!")
        return

    cur = conn.cursor()
    inserted = 0

    for a in accounts:
        name = safe(a.get("name"), 255)
        if not name:
            continue

        # Map industry code to text
        industry_code = a.get("industrycode")
        # Store code for now; can be mapped later
        industry = str(industry_code) if industry_code else None

        # Company size from number of employees
        num_emp = a.get("numberofemployees")
        if num_emp:
            if num_emp < 50:
                size = "small"
            elif num_emp < 500:
                size = "medium"
            else:
                size = "large"
        else:
            size = None

        legacy = {}
        for k, v in a.items():
            if v is not None and k not in (
                "accountid", "name", "industrycode", "websiteurl",
                "address1_city", "address1_stateorprovince", "address1_postalcode",
                "numberofemployees", "description", "telephone1", "emailaddress1",
                "createdon", "modifiedon"
            ) and not k.startswith("@") and not k.startswith("_"):
                legacy[k] = v

        try:
            cur.execute("""
                INSERT INTO employers (
                    company_name, industry, website,
                    city, state, zipcode,
                    company_size, description,
                    primary_contact_email, primary_contact_phone,
                    source_system, original_record_id, migration_date,
                    legacy_data, created_at, updated_at
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s, %s
                )
            """, (
                name, industry, safe(a.get("websiteurl"), 500),
                safe(a.get("address1_city"), 100),
                safe(a.get("address1_stateorprovince"), 50),
                safe(a.get("address1_postalcode"), 20),
                size, safe(a.get("description")),
                safe(a.get("emailaddress1"), 255),
                safe(a.get("telephone1"), 50),
                "dataverse", a.get("accountid"), MIGRATION_DATE,
                json.dumps(legacy) if legacy else None,
                a.get("createdon"), a.get("modifiedon") or a.get("createdon"),
            ))
            inserted += 1
        except Exception as e:
            print(f"  Error inserting account {a.get('accountid')}: {e}")
            conn.rollback()
            continue

    conn.commit()
    print(f"  Inserted: {inserted} employers")


# ============================================================
# STEP 5: Migrate cfa_lightcastjobs -> job_listings
# ============================================================
def migrate_lightcast_jobs(token, conn):
    print("\n=== STEP 5: Migrating cfa_lightcastjobs -> job_listings ===")

    jobs = fetch_all(token, "cfa_lightcastjobs")

    if not jobs:
        print("  No Lightcast jobs found!")
        return

    cur = conn.cursor()
    inserted = 0

    # Inspect first record to find field names
    if jobs:
        print(f"  Sample fields: {list(jobs[0].keys())[:20]}")

    for j in jobs:
        record_id = j.get("cfa_lightcastjobsid") or j.get("cfa_lightcastjobid")
        title = safe(j.get("cfa_jobtitle") or j.get("cfa_name") or j.get("cfa_title"), 500)

        if not title:
            # Try to find any field that looks like a title
            for k, v in j.items():
                if "title" in k.lower() or "name" in k.lower():
                    title = safe(v, 500)
                    if title:
                        break

        if not title:
            title = "Untitled Lightcast Job"

        legacy = {}
        for k, v in j.items():
            if v is not None and not k.startswith("@") and not k.startswith("_"):
                legacy[k] = v

        try:
            cur.execute("""
                INSERT INTO job_listings (
                    source, title, description,
                    city, state, zipcode,
                    salary_min, salary_max,
                    soc_code, status,
                    source_system, original_record_id, migration_date,
                    legacy_data, created_at
                ) VALUES (
                    %s, %s, %s,
                    %s, %s, %s,
                    %s, %s,
                    %s, %s,
                    %s, %s, %s,
                    %s, %s
                )
            """, (
                "lightcast",
                title,
                safe(j.get("cfa_description") or j.get("cfa_jobdescription")),
                safe(j.get("cfa_city") or j.get("cfa_location"), 100),
                safe(j.get("cfa_state"), 50),
                safe(j.get("cfa_zipcode") or j.get("cfa_postalcode"), 20),
                j.get("cfa_salarymin") or j.get("cfa_minsalary"),
                j.get("cfa_salarymax") or j.get("cfa_maxsalary"),
                safe(j.get("cfa_soccode") or j.get("cfa_onetcode"), 20),
                "imported",
                "dataverse", record_id, MIGRATION_DATE,
                json.dumps(legacy) if legacy else None,
                j.get("createdon"),
            ))
            inserted += 1
        except Exception as e:
            print(f"  Error inserting job {record_id}: {e}")
            conn.rollback()
            continue

    conn.commit()
    print(f"  Inserted: {inserted} job listings")


# ============================================================
# STEP 6: Migrate cfa_studentjourneies -> student_journeys
# ============================================================
def migrate_journeys(token, conn):
    print("\n=== STEP 6: Migrating cfa_studentjourneies -> student_journeys ===")

    journeys = fetch_all(token, "cfa_studentjourneies")

    if not journeys:
        print("  No journeys found!")
        return

    cur = conn.cursor()
    inserted = 0
    no_match = 0

    if journeys:
        print(f"  Sample fields: {list(journeys[0].keys())[:20]}")

    for j in journeys:
        # Find the student by original_record_id
        # The journey should reference a contact
        contact_ref = (
            j.get("_cfa_student_value") or
            j.get("_cfa_contact_value") or
            j.get("_cfa_studentid_value")
        )

        if not contact_ref:
            no_match += 1
            continue

        # Look up student by original_record_id
        cur.execute(
            "SELECT id FROM students WHERE original_record_id = %s LIMIT 1",
            (contact_ref,)
        )
        row = cur.fetchone()
        if not row:
            no_match += 1
            continue

        student_id = row[0]
        stage = safe(j.get("cfa_stage") or j.get("cfa_name") or j.get("cfa_journeystage"), 50) or "unknown"

        legacy = {}
        for k, v in j.items():
            if v is not None and not k.startswith("@") and not k.startswith("_"):
                legacy[k] = v

        try:
            cur.execute("""
                INSERT INTO student_journeys (
                    student_id, stage, entered_at, notes, triggered_by
                ) VALUES (%s, %s, %s, %s, %s)
            """, (
                student_id,
                stage,
                j.get("createdon"),
                json.dumps(legacy) if legacy else None,
                "migration"
            ))
            inserted += 1
        except Exception as e:
            print(f"  Error inserting journey: {e}")
            conn.rollback()
            continue

    conn.commit()
    print(f"  Inserted: {inserted}, No student match: {no_match}")


# ============================================================
# STEP 7: Migrate college + career programs
# ============================================================
def migrate_programs(token, conn):
    print("\n=== STEP 7: Migrating college + career programs ===")

    # College programs
    college_progs = fetch_all(token, "cfa_collegeprograms")
    print(f"  Fetched {len(college_progs)} college programs")

    if college_progs:
        print(f"  Sample fields: {list(college_progs[0].keys())[:20]}")

    cur = conn.cursor()
    inserted_cp = 0

    for p in college_progs:
        name = safe(p.get("cfa_name") or p.get("cfa_programname"), 255)
        if not name:
            continue

        legacy = {}
        for k, v in p.items():
            if v is not None and not k.startswith("@") and not k.startswith("_"):
                legacy[k] = v

        try:
            cur.execute("""
                INSERT INTO college_programs (
                    name, description, credential_type,
                    cip_code, source,
                    source_system, original_record_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                name,
                safe(p.get("cfa_description")),
                safe(p.get("cfa_credentialtype") or p.get("cfa_credential"), 100),
                safe(p.get("cfa_cipcode"), 20),
                "cfa_college",
                "dataverse",
                p.get("cfa_collegeprogramsid") or p.get("cfa_collegeprogramid"),
                p.get("createdon"),
            ))
            inserted_cp += 1
        except Exception as e:
            print(f"  Error: {e}")
            conn.rollback()
            continue

    conn.commit()
    print(f"  Inserted: {inserted_cp} college programs")

    # Career programs
    career_progs = fetch_all(token, "cfa_careerprograms")
    print(f"  Fetched {len(career_progs)} career programs")

    if career_progs:
        print(f"  Sample fields: {list(career_progs[0].keys())[:20]}")

    inserted_career = 0

    for p in career_progs:
        name = safe(p.get("cfa_name") or p.get("cfa_programname") or p.get("cfa_programtitle"), 255)
        if not name:
            continue

        legacy = {}
        for k, v in p.items():
            if v is not None and not k.startswith("@") and not k.startswith("_"):
                legacy[k] = v

        try:
            cur.execute("""
                INSERT INTO college_programs (
                    name, description, credential_type,
                    cip_code, source,
                    source_system, original_record_id, created_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """, (
                name,
                safe(p.get("cfa_description")),
                safe(p.get("cfa_credentialtype") or p.get("cfa_credential"), 100),
                safe(p.get("cfa_cipcode"), 20),
                "career_bridge",
                "dataverse",
                p.get("cfa_careerprogramsid") or p.get("cfa_careerprogramid"),
                p.get("createdon"),
            ))
            inserted_career += 1
        except Exception as e:
            print(f"  Error: {e}")
            conn.rollback()
            continue

    conn.commit()
    print(f"  Inserted: {inserted_career} career programs")


# ============================================================
# MAIN
# ============================================================
if __name__ == "__main__":
    print("=" * 60)
    print("WFD OS Migration: Dataverse -> Local PostgreSQL")
    print(f"Migration date: {MIGRATION_DATE}")
    print("=" * 60)

    # Get OAuth token
    print("\nAuthenticating with Dataverse...")
    token = get_token()
    print("  Token acquired.")

    # Connect to local PostgreSQL
    print("Connecting to local PostgreSQL...")
    conn = get_pg_conn()
    print("  Connected.")

    try:
        migrate_contacts(token, conn)       # Step 2
        migrate_accounts(token, conn)       # Step 3
        # Step 4 (merge studentdetails) will be a separate UPDATE pass
        migrate_lightcast_jobs(token, conn)  # Step 5
        migrate_journeys(token, conn)        # Step 6
        migrate_programs(token, conn)        # Step 7
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("Migration complete!")
    print("=" * 60)
    print("\nNext steps:")
    print("  - Step 4: Merge cfa_studentdetails into students (UPDATE pass)")
    print("  - Steps 8-10: BACPAC reference data")
    print("  - Run profile completeness calculation")
    print("  - Verify record counts match Dataverse")
