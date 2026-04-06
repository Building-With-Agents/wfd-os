"""
Deduplication module for job listings.
Uses normalized hash of title + company + location for exact dedup.
"""
import hashlib
import re


def normalize_text(text):
    """Normalize text for comparison: lowercase, strip whitespace, remove punctuation."""
    if not text:
        return ""
    text = text.lower().strip()
    text = re.sub(r'[^\w\s]', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text


def compute_job_hash(title, company, location):
    """Compute SHA-256 hash of normalized title + company + location."""
    parts = [
        normalize_text(title),
        normalize_text(company),
        normalize_text(location),
    ]
    combined = "|".join(parts)
    return hashlib.sha256(combined.encode('utf-8')).hexdigest()[:32]


def is_duplicate(conn, job_hash):
    """Check if a job with this hash already exists."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM job_listings WHERE job_hash = %s LIMIT 1", (job_hash,))
    return cur.fetchone() is not None


def check_source_id_exists(conn, source, source_id):
    """Check if a job from this source with this ID already exists."""
    if not source_id:
        return False
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM job_listings WHERE source = %s AND source_id = %s LIMIT 1",
        (source, source_id)
    )
    return cur.fetchone() is not None
