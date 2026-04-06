"""
Blob Storage Discovery Script
Enumerates all containers and blobs in the Azure Storage account,
reporting sizes, file types, date ranges, and samples.
"""

import os
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from azure.storage.blob import BlobServiceClient

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
SAMPLE_LIMIT = 5
INTERESTING_EXTENSIONS = {
    "PDF files (resumes)": [".pdf"],
    "DOCX files": [".docx"],
    "Model files": [".pkl", ".bin", ".pt", ".onnx", ".h5", ".safetensors"],
    "CSV/JSON data exports": [".csv", ".json"],
}


def human_size(nbytes: int) -> str:
    """Return a human-readable size string."""
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(nbytes) < 1024:
            return f"{nbytes:,.1f} {unit}"
        nbytes /= 1024
    return f"{nbytes:,.1f} PB"


def discover():
    # Force UTF-8 output on Windows
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8")

    # Load connection string from .env
    load_dotenv(ENV_PATH)
    conn_str = os.getenv("BLOB_CONNECTION_STRING")
    if not conn_str:
        print(f"ERROR: BLOB_CONNECTION_STRING not found in {ENV_PATH}")
        sys.exit(1)

    print(f"Loaded connection string from {ENV_PATH}")
    # Extract account name for display (avoid printing the full key)
    for part in conn_str.split(";"):
        if part.startswith("AccountName="):
            print(f"Account: {part.split('=', 1)[1]}")
            break

    client = BlobServiceClient.from_connection_string(conn_str)

    # ------------------------------------------------------------------
    # Enumerate containers
    # ------------------------------------------------------------------
    containers = list(client.list_containers())
    print(f"\n{'='*72}")
    print(f"STORAGE ACCOUNT DISCOVERY")
    print(f"{'='*72}")
    print(f"Total containers: {len(containers)}\n")

    # Aggregate interesting-file stats across all containers
    global_interesting = defaultdict(list)  # category -> [(container, blob_name, size)]

    for cinfo in containers:
        cname = cinfo["name"]
        cc = client.get_container_client(cname)

        blob_count = 0
        total_size = 0
        ext_counts = defaultdict(int)
        ext_sizes = defaultdict(int)
        earliest = None
        latest = None
        samples = []

        for blob in cc.list_blobs():
            blob_count += 1
            size = blob.size or 0
            total_size += size

            # Extension
            ext = Path(blob.name).suffix.lower() if "." in blob.name else "(none)"
            ext_counts[ext] += 1
            ext_sizes[ext] += size

            # Date range
            lm = blob.last_modified
            if lm:
                if earliest is None or lm < earliest:
                    earliest = lm
                if latest is None or lm > latest:
                    latest = lm

            # Samples
            if len(samples) < SAMPLE_LIMIT:
                samples.append(blob.name)

            # Track interesting files
            for category, exts in INTERESTING_EXTENSIONS.items():
                if ext in exts:
                    global_interesting[category].append((cname, blob.name, size))

        # Print container summary
        print(f"{'─'*72}")
        print(f"CONTAINER: {cname}")
        print(f"{'─'*72}")
        print(f"  Total blobs : {blob_count:,}")
        print(f"  Total size  : {human_size(total_size)}")
        if earliest:
            print(f"  Earliest    : {earliest.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        if latest:
            print(f"  Latest      : {latest.strftime('%Y-%m-%d %H:%M:%S UTC')}")

        if ext_counts:
            print(f"\n  File extensions:")
            for ext, count in sorted(ext_counts.items(), key=lambda x: -x[1]):
                print(f"    {ext:12s}  {count:>6,} files  {human_size(ext_sizes[ext]):>12s}")

        if samples:
            print(f"\n  Sample blobs (up to {SAMPLE_LIMIT}):")
            for s in samples:
                print(f"    - {s}")
        print()

    # ------------------------------------------------------------------
    # Interesting files summary
    # ------------------------------------------------------------------
    print(f"\n{'='*72}")
    print(f"INTERESTING FILES SUMMARY")
    print(f"{'='*72}")
    for category, items in INTERESTING_EXTENSIONS.items():
        found = global_interesting.get(category, [])
        print(f"\n  {category}: {len(found)} files found")
        if found:
            total_cat_size = sum(s for _, _, s in found)
            print(f"    Total size: {human_size(total_cat_size)}")
            # Group by container
            by_container = defaultdict(list)
            for c, b, s in found:
                by_container[c].append((b, s))
            for c, blobs in by_container.items():
                print(f"    [{c}] {len(blobs)} files")
                for b, s in blobs[:5]:
                    print(f"      - {b}  ({human_size(s)})")
                if len(blobs) > 5:
                    print(f"      ... and {len(blobs) - 5} more")

    print(f"\n{'='*72}")
    print("Discovery complete.")


if __name__ == "__main__":
    discover()
