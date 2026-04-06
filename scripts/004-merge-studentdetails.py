"""
Step 4: Merge cfa_studentdetails into existing student records.
Matches on contact ID and enriches with enrollment, education,
skills self-assessment, and enrollment form data.
"""
import os, json, requests, psycopg2
from dotenv import load_dotenv
from datetime import datetime, timezone
from pgconfig import PG_CONFIG

load_dotenv("C:/Users/ritub/projects/wfd-os/.env")

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
DYNAMICS_URL = os.getenv("DYNAMICS_PRIMARY_URL")


def get_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    r = requests.post(url, data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": f"{DYNAMICS_URL}/.default"
    })
    r.raise_for_status()
    return r.json()["access_token"]


def fetch_all(token, entity_set, top=5000):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json",
        "Prefer": "odata.maxpagesize=1000"
    }
    url = f"{DYNAMICS_URL}/api/data/v9.2/{entity_set}"
    all_records = []
    page = 0
    while url and len(all_records) < top:
        page += 1
        print(f"  Fetching page {page}...")
        r = requests.get(url, headers=headers)
        r.raise_for_status()
        data = r.json()
        all_records.extend(data.get("value", []))
        url = data.get("@odata.nextLink")
    print(f"  Total: {len(all_records)} records")
    return all_records


def safe(val, maxlen=None):
    if val is None:
        return None
    s = str(val).strip()
    if s == "":
        return None
    if maxlen:
        s = s[:maxlen]
    return s


def map_enrollment_status(code):
    """Map Dataverse option set code to readable status."""
    mapping = {
        100000000: "enrolled",
        100000001: "completed",
        100000002: "dropped",
        100000003: "deferred",
        100000004: "applied",
        100000005: "waitlisted",
    }
    return mapping.get(code, f"code_{code}" if code else None)


def map_race(code):
    mapping = {
        100000000: "White",
        100000001: "Black or African American",
        100000002: "American Indian or Alaska Native",
        100000003: "Native Hawaiian or Pacific Islander",
        100000004: "Asian",
        100000005: "Two or More Races",
        100000006: "Other",
    }
    return mapping.get(code, f"code_{code}" if code else None)


def main():
    print("=== Step 4: Merge cfa_studentdetails into students ===\n")

    token = get_token()
    print("Token acquired.\n")

    details = fetch_all(token, "cfa_studentdetails")
    if not details:
        print("No student details found!")
        return

    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    matched = 0
    no_match = 0
    errors = 0

    for d in details:
        contact_id = d.get("_cfa_contact_value")
        if not contact_id:
            no_match += 1
            continue

        # Find matching student
        cur.execute(
            "SELECT id FROM students WHERE original_record_id = %s LIMIT 1",
            (contact_id,)
        )
        row = cur.fetchone()
        if not row:
            no_match += 1
            continue

        student_id = row[0]

        # Extract enrichment fields
        enrollment_code = d.get("cfa_enrollmentstatus")
        enrollment_status = map_enrollment_status(enrollment_code)

        race_code = d.get("cfa_race")
        ethnicity = map_race(race_code)

        hispanic = d.get("cfa_hispanic")
        veteran = d.get("cfa_veteran")
        disability = d.get("cfa_disability")

        # Education fields
        institution = (safe(d.get("cfa_nameofhighschool"), 255) or
                       safe(d.get("cfa_cityschoolcollege"), 255) or
                       safe(d.get("cfa_form_trainingschoolname"), 255))

        # Determine program stage
        levels = []
        for i in range(1, 7):
            if d.get(f"cfa_islevel{i}"):
                levels.append(f"level_{i}")
        program_stage = levels[-1] if levels else None

        # Build skills self-assessment from tech fields
        tech_skills = {}
        skill_fields = {
            "cfa_codinginpython": "Python",
            "cfa_form_codinginhtml": "HTML",
            "cfa_form_codinginjavascript": "JavaScript",
            "cfa_webdesignhtmlcssjavascript": "Web Design",
            "cfa_graphicdesign": "Graphic Design",
            "cfa_digitalmedia": "Digital Media",
            "cfa_networkadministration": "Network Admin",
            "cfa_videoeditingsoftware": "Video Editing",
            "cfa_softwareinstallation": "Software Installation",
            "cfa_pcorappletroubleshooting": "PC Troubleshooting",
            "cfa_microsoftofficewordexceletcpowerpoint": "Microsoft Office",
            "cfa_computerability": "General Computer Skills",
        }
        for field, name in skill_fields.items():
            val = d.get(field)
            if val is not None:
                # 100000000=beginner, 100000001=intermediate, 100000002=advanced
                level_map = {100000000: "beginner", 100000001: "intermediate", 100000002: "advanced"}
                tech_skills[name] = level_map.get(val, str(val))

        # Build legacy data from remaining fields
        legacy = {}
        skip_keys = {"_cfa_contact_value", "cfa_studentdetailid", "cfa_name",
                      "cfa_enrollmentstatus", "cfa_race", "cfa_hispanic",
                      "cfa_veteran", "cfa_disability", "cfa_nameofhighschool",
                      "cfa_cityschoolcollege", "cfa_form_trainingschoolname",
                      "createdon", "modifiedon", "statecode", "statuscode",
                      "versionnumber", "timezoneruleversionnumber",
                      "utcconversiontimezonecode"}
        for k, v in d.items():
            if (v is not None and k not in skip_keys and
                not k.startswith("@") and not k.startswith("_") and
                k not in skill_fields):
                legacy[k] = v

        # Add tech skills to legacy
        if tech_skills:
            legacy["tech_skills_selfassessment"] = tech_skills

        try:
            cur.execute("""
                UPDATE students SET
                    ethnicity = COALESCE(ethnicity, %s),
                    veteran_status = COALESCE(veteran_status, %s),
                    disability_status = COALESCE(disability_status, %s),
                    institution = COALESCE(institution, %s),
                    pipeline_status = CASE
                        WHEN pipeline_status = 'unknown' AND %s IS NOT NULL THEN %s
                        ELSE pipeline_status
                    END,
                    program_stage_reached = COALESCE(program_stage_reached, %s),
                    data_quality = CASE
                        WHEN %s IS NOT NULL THEN 'enriched'
                        ELSE data_quality
                    END,
                    legacy_data = CASE
                        WHEN legacy_data IS NULL THEN %s::jsonb
                        ELSE legacy_data || %s::jsonb
                    END,
                    updated_at = NOW()
                WHERE id = %s
            """, (
                ethnicity,
                True if veteran == 1 else (False if veteran == 0 else None),
                True if disability == 1 else (False if disability == 0 else None),
                institution,
                enrollment_status, enrollment_status,
                program_stage,
                enrollment_status,
                json.dumps(legacy) if legacy else '{}',
                json.dumps(legacy) if legacy else '{}',
                student_id,
            ))
            matched += 1
        except Exception as e:
            print(f"  Error updating {student_id}: {e}")
            conn.rollback()
            errors += 1
            continue

    conn.commit()
    conn.close()

    print(f"\nResults:")
    print(f"  Matched and enriched: {matched}")
    print(f"  No matching student: {no_match}")
    print(f"  Errors: {errors}")
    print(f"  Total details processed: {len(details)}")


if __name__ == "__main__":
    main()
