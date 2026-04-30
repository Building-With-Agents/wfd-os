"""Test resume parser on 3 resumes before running the full batch."""
import os, json, base64
import psycopg2
import anthropic
from azure.storage.blob import BlobServiceClient

from wfdos_common.config import PG_CONFIG, settings

BLOB_CONN_STR = settings.blob.connection_string
ANTHROPIC_KEY = settings.llm.anthropic_api_key
# TODO(#20): model ID will be routed through wfdos_common.llm tier mapping.
MODEL = "claude-sonnet-4-20250514"

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
Return ONLY the JSON object, no other text."""


def main():
    print("=== Resume Parser Test (3 resumes) ===\n")

    blob_client = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
    claude_client = anthropic.Anthropic(api_key=ANTHROPIC_KEY)
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    cur.execute("""
        SELECT id, resume_blob_path, full_name
        FROM students
        WHERE resume_blob_path IS NOT NULL
          AND resume_parsed = FALSE
        LIMIT 3
    """)
    students = cur.fetchall()

    for student_id, blob_path, name in students:
        print(f"\n--- Parsing: {name} ---")
        print(f"  Blob: {blob_path}")

        # Download
        container = blob_client.get_container_client("resume-storage")
        blob = container.get_blob_client(blob_path)
        pdf_bytes = blob.download_blob().readall()
        print(f"  Size: {len(pdf_bytes)/1024:.0f} KB")

        # Parse
        pdf_b64 = base64.standard_b64encode(pdf_bytes).decode("utf-8")
        message = claude_client.messages.create(
            model=MODEL,
            max_tokens=2000,
            messages=[{
                "role": "user",
                "content": [
                    {
                        "type": "document",
                        "source": {
                            "type": "base64",
                            "media_type": "application/pdf",
                            "data": pdf_b64,
                        },
                    },
                    {"type": "text", "text": EXTRACTION_PROMPT}
                ]
            }]
        )

        response_text = message.content[0].text.strip()
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            response_text = "\n".join(lines[1:-1])

        parsed = json.loads(response_text)

        # Show results
        print(f"  Name: {parsed.get('full_name')}")
        print(f"  Email: {parsed.get('email')}")
        print(f"  Phone: {parsed.get('phone')}")
        print(f"  Location: {parsed.get('city')}, {parsed.get('state')} {parsed.get('zipcode')}")
        print(f"  Education: {parsed.get('degree')} in {parsed.get('field_of_study')} from {parsed.get('institution')}")
        print(f"  Skills: {len(parsed.get('skills', []))} found")
        if parsed.get('skills'):
            print(f"    -> {', '.join(parsed['skills'][:10])}")
        print(f"  Work exp: {len(parsed.get('work_experience', []))} entries")
        print(f"  Certs: {parsed.get('certifications')}")
        print(f"  Usage: {message.usage}")

    conn.close()
    print("\n=== Test complete ===")


if __name__ == "__main__":
    main()
