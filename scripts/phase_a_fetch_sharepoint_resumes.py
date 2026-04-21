"""Phase A — Task 2, Step 1/2: Download Cohort 1 apprentice resumes from SharePoint.

Reads from the CFA tech-sector-leadership SharePoint site, locates the
"Feb 23rd 2026 Cohort Resumes" folder, downloads all files into
data/cohort1_resumes/.

READ-ONLY on SharePoint. Uses Microsoft Graph API via the existing
agents/graph credentials (GRAPH_*). Does not modify, create, or delete
anything on SharePoint.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

import httpx
from azure.identity import ClientSecretCredential
from dotenv import load_dotenv


WORKTREE = Path(r"C:\Users\ritub\Projects\wfd-os\.claude\worktrees\stupefied-tharp-41af25")
ENV_PATH = Path(r"C:\Users\ritub\Projects\wfd-os\.env")
load_dotenv(ENV_PATH, override=True)

# Prefer GRAPH_* (Scoping/Grant agent creds, known to have Graph permissions)
# and fall back to AZURE_* for parity with agents/graph/config.py
TENANT_ID = os.getenv("GRAPH_TENANT_ID") or os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("GRAPH_CLIENT_ID") or os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GRAPH_CLIENT_SECRET") or os.getenv("AZURE_CLIENT_SECRET")

GRAPH = "https://graph.microsoft.com/v1.0"

SITE_HOSTNAME = "computinforall.sharepoint.com"  # note: one 'g', matches actual M365 tenant
SITE_PATH = "sites/cfatechsectorleadership"
TARGET_FOLDER_NAME = "Feb 23rd 2026 Cohort Resumes"

OUT_DIR = WORKTREE / "data" / "cohort1_resumes"


def get_token() -> str:
    cred = ClientSecretCredential(
        tenant_id=TENANT_ID, client_id=CLIENT_ID, client_secret=CLIENT_SECRET
    )
    return cred.get_token("https://graph.microsoft.com/.default").token


def headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}


def resolve_site(token: str) -> str:
    url = f"{GRAPH}/sites/{SITE_HOSTNAME}:/{SITE_PATH}"
    r = httpx.get(url, headers=headers(token), timeout=30)
    r.raise_for_status()
    site = r.json()
    return site["id"]


def get_default_drive_id(token: str, site_id: str) -> str:
    url = f"{GRAPH}/sites/{site_id}/drive"
    r = httpx.get(url, headers=headers(token), timeout=30)
    r.raise_for_status()
    return r.json()["id"]


def list_children(token: str, drive_id: str, path: str = "") -> list[dict]:
    """List children at a path within a drive. Empty path = drive root."""
    if not path:
        url = f"{GRAPH}/drives/{drive_id}/root/children"
    else:
        # url-safe path: callers pass raw path; Graph tolerates URL-encoded colons
        url = f"{GRAPH}/drives/{drive_id}/root:/{path}:/children"
    r = httpx.get(url, headers=headers(token), params={"$top": 200}, timeout=30)
    r.raise_for_status()
    return r.json().get("value", [])


def find_folder_recursive(token: str, drive_id: str, target_name: str, path: str = "", depth: int = 0, max_depth: int = 3) -> str | None:
    """Depth-first search for a folder by name. Returns the path if found."""
    if depth > max_depth:
        return None
    try:
        children = list_children(token, drive_id, path)
    except httpx.HTTPStatusError as e:
        print(f"    ! cannot list {path or '/'}: HTTP {e.response.status_code}")
        return None
    for ch in children:
        if "folder" in ch:
            name = ch["name"]
            sub = f"{path}/{name}" if path else name
            if name == target_name:
                return sub
        elif "folder" in ch or ch.get("folder"):
            pass
    # Not found at this level — recurse into subfolders
    for ch in children:
        if "folder" in ch:
            name = ch["name"]
            sub = f"{path}/{name}" if path else name
            found = find_folder_recursive(token, drive_id, target_name, sub, depth + 1, max_depth)
            if found:
                return found
    return None


def download_file(token: str, drive_id: str, item_id: str, out_path: Path) -> int:
    url = f"{GRAPH}/drives/{drive_id}/items/{item_id}/content"
    with httpx.stream("GET", url, headers={"Authorization": f"Bearer {token}"}, follow_redirects=True, timeout=120) as r:
        r.raise_for_status()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        size = 0
        with out_path.open("wb") as f:
            for chunk in r.iter_bytes():
                f.write(chunk)
                size += len(chunk)
        return size


def main() -> int:
    print("=" * 60)
    print("Phase A Task 2 — Step 1: Fetch SharePoint resumes")
    print("=" * 60)

    if not (TENANT_ID and CLIENT_ID and CLIENT_SECRET):
        print("ERROR: missing GRAPH_* or AZURE_* credentials in .env")
        return 2

    print(f"Site:   https://{SITE_HOSTNAME}/{SITE_PATH}")
    print(f"Folder: {TARGET_FOLDER_NAME}")
    print(f"Out:    {OUT_DIR}")
    print()

    try:
        token = get_token()
    except Exception as e:
        print(f"ERROR acquiring token: {e}")
        return 3

    try:
        site_id = resolve_site(token)
        print(f"site_id: {site_id}")
    except httpx.HTTPStatusError as e:
        print(f"ERROR resolving site: HTTP {e.response.status_code}")
        print(f"  body: {e.response.text[:500]}")
        return 4

    try:
        drive_id = get_default_drive_id(token, site_id)
        print(f"drive_id: {drive_id}")
    except httpx.HTTPStatusError as e:
        print(f"ERROR getting drive: HTTP {e.response.status_code}")
        print(f"  body: {e.response.text[:500]}")
        return 5

    print()
    print("root-level contents:")
    root = list_children(token, drive_id)
    for ch in root:
        kind = "folder" if "folder" in ch else "file  "
        print(f"  {kind}  {ch['name']}")

    print()
    print(f"searching for folder: '{TARGET_FOLDER_NAME}' ...")
    folder_path = find_folder_recursive(token, drive_id, TARGET_FOLDER_NAME)
    if not folder_path:
        print(f"  NOT FOUND within 3 levels.")
        print("  Will stop here so Ritu can point to exact path.")
        return 6
    print(f"  found at: {folder_path}")

    print()
    print("files in target folder:")
    items = list_children(token, drive_id, folder_path)
    files = [x for x in items if "file" in x]
    folders = [x for x in items if "folder" in x]
    for f in files:
        sz = f.get("size", 0)
        mtype = f.get("file", {}).get("mimeType", "?")
        print(f"  {sz:>10,} B  {mtype:<60}  {f['name']}")
    for d in folders:
        print(f"  (subfolder)  {d['name']}  — NOT recursing; flagging")

    print()
    print(f"total files: {len(files)}  (expected 7-9 per Ritu)")
    if not (6 <= len(files) <= 12):
        print(f"  WARNING: count outside plausible range, pausing without downloading")
        return 7

    # Download
    print()
    print("downloading...")
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    # Clear any prior downloads (so re-runs are clean)
    for p in OUT_DIR.iterdir():
        if p.is_file():
            p.unlink()

    ok = 0
    for f in files:
        out = OUT_DIR / f["name"]
        try:
            n = download_file(token, drive_id, f["id"], out)
            print(f"  OK   {n:>10,} B   {f['name']}")
            ok += 1
        except Exception as e:
            print(f"  FAIL  {f['name']}: {e}")

    print()
    print(f"downloaded {ok}/{len(files)} files to {OUT_DIR}")
    return 0 if ok == len(files) else 8


if __name__ == "__main__":
    sys.exit(main())
