import os
import sys
from azure.identity import ClientSecretCredential
import httpx

# Fix Windows console encoding for Unicode characters in HTTP responses
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


MONTHLY_FOLDER = os.getenv("SHAREPOINT_FOLDER", "WJI-Grant-Agent/monthly-uploads")
BASELINE_FOLDER = os.getenv("SHAREPOINT_BASELINE_FOLDER", "WJI-Grant-Agent/baseline")
SITE_HOSTNAME = "computinforall.sharepoint.com"
SITE_PATH = "/sites/CFAOperationsHRFinance"
SITE_ID_ENV = os.getenv("SHAREPOINT_SITE_ID")  # Pre-resolved site ID from .env
GRAPH_BASE = "https://graph.microsoft.com/v1.0"


def _get_token() -> str:
    credential = ClientSecretCredential(
        tenant_id=os.getenv("MICROSOFT_APP_TENANT_ID"),
        client_id=os.getenv("MICROSOFT_APP_ID"),
        client_secret=os.getenv("MICROSOFT_APP_PASSWORD"),
    )
    return credential.get_token("https://graph.microsoft.com/.default").token


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}"}


async def _get_site_and_drive() -> tuple[str, str]:
    """Resolve the SharePoint site and return (site_id, drive_id).
    Uses SHAREPOINT_SITE_ID from .env if available to skip the site lookup."""
    headers = _headers()

    if SITE_ID_ENV:
        site_id = SITE_ID_ENV
    else:
        r = httpx.get(f"{GRAPH_BASE}/sites/{SITE_HOSTNAME}:{SITE_PATH}", headers=headers)
        r.raise_for_status()
        site_id = r.json()["id"]

    r = httpx.get(f"{GRAPH_BASE}/sites/{site_id}/drives", headers=headers)
    r.raise_for_status()
    drive_id = r.json()["value"][0]["id"]
    return site_id, drive_id


async def list_folder_files(folder_path: str) -> list[dict]:
    """List all files in a SharePoint folder by path.
    Returns empty list if the folder does not exist (404)."""
    headers = _headers()
    _, drive_id = await _get_site_and_drive()

    r = httpx.get(f"{GRAPH_BASE}/drives/{drive_id}/root:/{folder_path}:/children", headers=headers)
    if r.status_code == 404:
        return []  # Folder does not exist yet
    r.raise_for_status()

    files = []
    for item in r.json().get("value", []):
        if "file" in item:
            files.append({
                "name": item["name"],
                "id": item["id"],
                "size": item["size"],
                "last_modified": item.get("lastModifiedDateTime", ""),
                "drive_id": drive_id,
            })
    return files


async def list_monthly_files() -> list[dict]:
    """List all files in the monthly-uploads folder."""
    return await list_folder_files(MONTHLY_FOLDER)


async def list_baseline_files() -> list[dict]:
    """List all files in the baseline folder."""
    return await list_folder_files(BASELINE_FOLDER)


async def download_file(drive_id: str, item_id: str) -> bytes:
    """Download a file by drive and item ID."""
    headers = _headers()
    r = httpx.get(
        f"{GRAPH_BASE}/drives/{drive_id}/items/{item_id}/content",
        headers=headers,
        follow_redirects=True,
    )
    r.raise_for_status()
    return r.content


async def _download_file_set(file_list: list[dict]) -> dict[str, bytes]:
    """Download a list of files and return {filename: file_bytes}."""
    result = {}
    for f in file_list:
        print(f"Downloading: {f['name']}")
        content = await download_file(f["drive_id"], f["id"])
        result[f["name"]] = content
    return result


async def get_monthly_file_set() -> dict[str, bytes]:
    """Download all files from the monthly-uploads folder."""
    files = await list_monthly_files()
    return await _download_file_set(files)


async def get_baseline_file_set() -> dict[str, bytes]:
    """Download all files from the baseline folder."""
    files = await list_baseline_files()
    return await _download_file_set(files)
