"""
Profile Agent — Step 1: Link resume blob paths to student records.

Reads all blob paths from Azure Blob Storage resume-storage container,
extracts the GUID from each path, and matches to students by
original_record_id (Dataverse contactid).
"""
import os, psycopg2
from azure.storage.blob import BlobServiceClient
import sys

from wfdos_common.config import settings

# wfdos_common.config auto-loads .env via find_dotenv (no hardcoded path).
sys.path.insert(0, str(settings.profile.resume_storage_path))
from pgconfig import PG_CONFIG  # noqa: E402

BLOB_CONN_STR = settings.blob.connection_string
CONTAINER = "resume-storage"


def get_resume_blobs():
    """List all resume PDFs in blob storage, return {guid: blob_path}."""
    print("Connecting to Azure Blob Storage...")
    client = BlobServiceClient.from_connection_string(BLOB_CONN_STR)
    container = client.get_container_client(CONTAINER)

    resume_map = {}
    count = 0
    for blob in container.list_blobs():
        name = blob.name
        # Pattern: {guid}/resume.pdf
        if name.endswith("/resume.pdf"):
            guid = name.split("/")[0].lower()
            resume_map[guid] = name
            count += 1

    print(f"  Found {count} resume PDFs in blob storage")
    return resume_map


def link_to_students(resume_map):
    """Match blob GUIDs to student original_record_id and update resume_blob_path."""
    print("\nConnecting to PostgreSQL...")
    conn = psycopg2.connect(**PG_CONFIG)
    cur = conn.cursor()

    # Get all students with their original_record_id
    cur.execute("SELECT id, original_record_id FROM students WHERE original_record_id IS NOT NULL")
    students = cur.fetchall()
    print(f"  {len(students)} students with original_record_id")

    # Build lookup: lowercase original_record_id -> student id
    student_lookup = {}
    for sid, orig_id in students:
        if orig_id:
            student_lookup[orig_id.lower()] = sid

    linked = 0
    no_match = 0
    already_linked = 0

    for guid, blob_path in resume_map.items():
        student_id = student_lookup.get(guid)
        if student_id:
            cur.execute(
                """UPDATE students
                   SET resume_blob_path = %s,
                       updated_at = NOW()
                   WHERE id = %s AND (resume_blob_path IS NULL OR resume_blob_path != %s)""",
                (blob_path, student_id, blob_path)
            )
            if cur.rowcount > 0:
                linked += 1
            else:
                already_linked += 1
        else:
            no_match += 1

    conn.commit()

    # Verify
    cur.execute("SELECT count(*) FROM students WHERE resume_blob_path IS NOT NULL")
    total_linked = cur.fetchone()[0]

    cur.execute("SELECT count(*) FROM students WHERE resume_blob_path IS NULL")
    total_unlinked = cur.fetchone()[0]

    conn.close()

    print(f"\nResults:")
    print(f"  Newly linked: {linked}")
    print(f"  Already linked: {already_linked}")
    print(f"  No matching student: {no_match}")
    print(f"  Total with resume: {total_linked}")
    print(f"  Total without resume: {total_unlinked}")
    print(f"  Resume coverage: {total_linked}/{total_linked + total_unlinked} = {total_linked/(total_linked+total_unlinked)*100:.1f}%")

    return total_linked


def main():
    print("=" * 60)
    print("Profile Agent: Link Resume Blob Paths")
    print("=" * 60)

    resume_map = get_resume_blobs()
    linked = link_to_students(resume_map)

    print("\n" + "=" * 60)
    print(f"Done. {linked} students now have resume_blob_path set.")
    print("=" * 60)


if __name__ == "__main__":
    main()
