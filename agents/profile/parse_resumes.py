"""
Profile Agent -- Resume Parser.

Downloads each resume PDF from Azure Blob Storage, sends to Gemini Flash
for structured extraction, then updates the student record in PostgreSQL.

Extracts: full_name, email, phone, education (institution, degree,
field_of_study, graduation_year), work experience, skills, location,
certifications, career_objective.

Calculates parse_confidence_score (0.0-1.0) based on extraction completeness.

LLM: Gemini 2.5 Flash (via google-generativeai SDK)
Previous: Anthropic Claude (migrated April 2026)

CLAUDE.md rules:
- READ from Blob Storage
- WRITE only to PostgreSQL
- No modifications to any legacy system
"""
import os, sys, json, time, base64, io, traceback
import psycopg2
import google.generativeai as genai
from azure.storage.blob import BlobServiceClient
from dotenv import load_dotenv

sys.path.insert(0, "C:/Users/ritub/projects/wfd-os/scripts")
from pgconfig import PG_CONFIG

load_dotenv("C:/Users/ritub/projects/wfd-os/.env", override=True)

BLOB_CONN_STR = os.getenv("BLOB_CONNECTION_STRING")
CONTAINER = "resume-storage"

# Configure Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

EXTRACTION_PROMPT = """Extract the following structured information from this resume PDF.
Return ONLY valid JSON with these fields (use null for missing fields):

{
  "full_name": "First Last",
  "email": "email@example.com",
  "phone": "555-123-4567",
  "city": "City name",
  "state": "State (2-letter code if US)",
  "zipcode": "12345",
  "institution": "Most recent school/university",
  "degree": "Degree type (e.g. BS, BA, MS, High School Diploma)",
  "field_of_study": "Major or field",
  "graduation_year": 2024,
  "linkedin_url": "https://linkedin.com/in/...",
  "github_url": "https://github.com/...",
  "portfolio_url": "https://...",
  "skills": ["skill1", "skill2", "skill3"],
  "certifications": ["cert1", "cert2"],
  "work_experience": [
    {
      "company": "Company Name",
      "title": "Job Title",
      "start_date": "2023-01",
      "end_date": "2024-06",
      "is_current": false
    }
  ],
  "career_objective": "Brief summary or objective if stated",
  "work_authorization": "US Citizen / Green Card / OPT / etc if mentioned"
}

Be thorough. Extract ALL skills mentioned anywhere in the resume.
For education, use the most recent or highest degree.
Return ONLY the JSON object, no other text."""


def get_blob_client():
    return BlobServiceClient.from_connection_string(BLOB_CONN_STR)


def download_resume_pdf(blob_client, blob_path):
    """Download resume PDF from blob storage, return bytes."""
    container = blob_client.get_container_client(CONTAINER)
    blob = container.get_blob_client(blob_path)
    return blob.download_blob().readall()


def parse_resume_with_gemini(pdf_bytes):
    """Send PDF to Gemini Flash for structured extraction.

    Uses Gemini's inline_data to pass the PDF directly as base64.
    """
    pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")

    model = genai.GenerativeModel(GEMINI_MODEL)
    response = model.generate_content([
        {
            "mime_type": "application/pdf",
            "data": pdf_b64,
        },
        EXTRACTION_PROMPT,
    ])

    # Extract JSON from response
    response_text = response.text.strip()

    # Handle potential markdown code blocks
    if response_text.startswith("```"):
        lines = response_text.split("\n")
        response_text = "\n".join(lines[1:-1])

    return json.loads(response_text)


def calculate_confidence(parsed):
    """Calculate parse_confidence_score (0.0-1.0) based on extraction completeness."""
    checks = [
        parsed.get("full_name") is not None,
        parsed.get("email") is not None,
        parsed.get("phone") is not None,
        parsed.get("city") is not None or parsed.get("state") is not None,
        parsed.get("institution") is not None,
        parsed.get("degree") is not None,
        bool(parsed.get("skills") and len(parsed["skills"]) >= 1),
        bool(parsed.get("skills") and len(parsed["skills"]) >= 3),
        bool(parsed.get("work_experience")),
        parsed.get("field_of_study") is not None,
    ]
    return round(sum(checks) / len(checks), 2)


def update_student(conn, student_id, parsed, confidence):
    """Update student record with parsed resume data."""
    cur = conn.cursor()

    skills = parsed.get("skills") or []
    work_exp = parsed.get("work_experience") or []
    certs = parsed.get("certifications") or []

    cur.execute("""
        UPDATE students SET
            full_name = COALESCE(NULLIF(%s, ''), full_name),
            email = COALESCE(email, %s),
            phone = COALESCE(phone, %s),
            city = COALESCE(city, %s),
            state = COALESCE(state, %s),
            zipcode = COALESCE(zipcode, %s),
            institution = COALESCE(institution, %s),
            degree = COALESCE(degree, %s),
            field_of_study = COALESCE(field_of_study, %s),
            graduation_year = COALESCE(graduation_year, %s),
            linkedin_url = COALESCE(linkedin_url, %s),
            github_url = COALESCE(github_url, %s),
            portfolio_url = COALESCE(portfolio_url, %s),
            work_authorization = COALESCE(work_authorization, %s),
            resume_parsed = TRUE,
            parse_confidence_score = %s,
            updated_at = NOW()
        WHERE id = %s
    """, (
        parsed.get("full_name"),
        parsed.get("email"),
        parsed.get("phone"),
        parsed.get("city"),
        parsed.get("state"),
        parsed.get("zipcode"),
        parsed.get("institution"),
        parsed.get("degree"),
        parsed.get("field_of_study"),
        parsed.get("graduation_year"),
        parsed.get("linkedin_url"),
        parsed.get("github_url"),
        parsed.get("portfolio_url"),
        parsed.get("work_authorization"),
        confidence,
        student_id,
    ))

    # Insert skills into student_skills (match against skills taxonomy)
    if skills:
        for skill_name in skills[:50]:  # Cap at 50 per student
            cur.execute("""
                INSERT INTO student_skills (student_id, skill_id, source)
                SELECT %s, skill_id, 'resume_parse'
                FROM skills
                WHERE LOWER(skill_name) = LOWER(%s)
                ON CONFLICT DO NOTHING
            """, (student_id, skill_name.strip()))

            # If no exact match, still record in legacy_data
            # (will be handled by taxonomy normalization later)

    # Insert work experience
    for exp in work_exp[:10]:
        if exp.get("company") or exp.get("title"):
            # Fix partial dates: "2022-10" -> "2022-10-01"
            start = exp.get("start_date")
            end = exp.get("end_date")
            if start and len(str(start)) == 7:  # YYYY-MM
                start = str(start) + "-01"
            if end and len(str(end)) == 7:
                end = str(end) + "-01"
            if start and len(str(start)) == 4:  # YYYY only
                start = str(start) + "-01-01"
            if end and len(str(end)) == 4:
                end = str(end) + "-01-01"
            # Validate dates are parseable, else null
            try:
                if start:
                    from datetime import date
                    date.fromisoformat(str(start))
            except:
                start = None
            try:
                if end:
                    from datetime import date
                    date.fromisoformat(str(end))
            except:
                end = None
            cur.execute("""
                INSERT INTO student_work_experience
                    (student_id, company, title, start_date, end_date, is_current)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                student_id,
                (exp.get("company") or "")[:255],
                (exp.get("title") or "")[:255],
                start,
                end,
                exp.get("is_current", False),
            ))

    # Store full parsed data and certs in legacy_data
    cur.execute("""
        UPDATE students SET
            legacy_data = COALESCE(legacy_data, '{}'::jsonb) ||
                jsonb_build_object(
                    'resume_parsed_data', %s::jsonb,
                    'certifications', %s::jsonb,
                    'career_objective', %s
                )
        WHERE id = %s
    """, (
        json.dumps({"skills_extracted": skills, "work_count": len(work_exp)}),
        json.dumps(certs),
        parsed.get("career_objective"),
        student_id,
    ))

    return True


def main():
    print("=" * 60)
    print("Profile Agent: Resume Parser")
    print("=" * 60)

    # Connect to services
    blob_client = get_blob_client()
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Get batch size from command line (default: all)
    batch_size = int(sys.argv[1]) if len(sys.argv) > 1 else 99999

    # Get students with resumes that haven't been parsed yet
    cur.execute("""
        SELECT id, resume_blob_path, full_name
        FROM students
        WHERE resume_blob_path IS NOT NULL
          AND resume_parsed = FALSE
        ORDER BY created_at
        LIMIT %s
    """, (batch_size,))
    students = cur.fetchall()
    print(f"\n{len(students)} resumes to parse\n")

    if not students:
        print("No unparsed resumes found.")
        conn.close()
        return

    parsed_count = 0
    error_count = 0
    high_confidence = 0
    medium_confidence = 0
    low_confidence = 0
    total_skills = 0

    for i, (student_id, blob_path, name) in enumerate(students):
        progress = f"[{i+1}/{len(students)}]"
        try:
            # Download PDF
            pdf_bytes = download_resume_pdf(blob_client, blob_path)
            size_kb = len(pdf_bytes) / 1024

            if len(pdf_bytes) < 500:
                print(f"  {progress} {name}: Skipped (too small: {size_kb:.0f}KB)")
                error_count += 1
                continue

            if len(pdf_bytes) > 10_000_000:
                print(f"  {progress} {name}: Skipped (too large: {size_kb:.0f}KB)")
                error_count += 1
                continue

            # Parse with Gemini
            parsed = parse_resume_with_gemini(pdf_bytes)
            confidence = calculate_confidence(parsed)

            # Update student record
            update_student(conn, student_id, parsed, confidence)
            conn.commit()

            skills_found = len(parsed.get("skills") or [])
            total_skills += skills_found
            parsed_count += 1

            if confidence >= 0.8:
                high_confidence += 1
                tier = "HIGH"
            elif confidence >= 0.5:
                medium_confidence += 1
                tier = "MED"
            else:
                low_confidence += 1
                tier = "LOW"

            print(f"  {progress} {name}: {tier} ({confidence}) | "
                  f"{skills_found} skills | {size_kb:.0f}KB")

            # Rate limiting for Gemini: ~15 requests/minute on paid tier
            time.sleep(4)

        except json.JSONDecodeError as e:
            print(f"  {progress} {name}: JSON parse error - {e}")
            error_count += 1
            conn.rollback()
        except Exception as rate_err:
            err_str = str(rate_err).lower()
            if "429" in err_str or "resource_exhausted" in err_str or "quota" in err_str:
                print(f"  {progress} Rate limited. Waiting 30s...")
                time.sleep(30)
                error_count += 1
                conn.rollback()
                continue
        except Exception as e:
            print(f"  {progress} {name}: Error - {str(e)[:100]}")
            error_count += 1
            conn.rollback()

    conn.close()

    # Summary
    print("\n" + "=" * 60)
    print("Resume Parsing Complete")
    print("=" * 60)
    print(f"  Parsed:           {parsed_count}")
    print(f"  Errors/Skipped:   {error_count}")
    print(f"  High confidence:  {high_confidence} (>= 0.8)")
    print(f"  Medium confidence:{medium_confidence} (0.5 - 0.8)")
    print(f"  Low confidence:   {low_confidence} (< 0.5)")
    print(f"  Total skills extracted: {total_skills}")
    print(f"  Avg skills/resume: {total_skills/max(parsed_count,1):.1f}")


if __name__ == "__main__":
    main()
