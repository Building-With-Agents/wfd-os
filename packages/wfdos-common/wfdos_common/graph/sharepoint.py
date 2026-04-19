"""SharePoint operations — create client workspaces, portal pages, upload documents.

v1.3+ architecture:
- Internal workspace: /sites/wAIFinder/Clients/<CompanyName>/ (existing wAIFinder site)
- Client portal: ONE shared Communication Site 'CFA-Client-Portal', one page per client
- NEVER touches CFAOperationsHRFinance (Grant Agent's site)
"""

import httpx
from azure.identity import ClientSecretCredential
from wfdos_common.models.scoping import ScopingRequest
from wfdos_common.graph import config

GRAPH = "https://graph.microsoft.com/v1.0"
GRAPH_BETA = "https://graph.microsoft.com/beta"


def _get_token() -> str:
    credential = ClientSecretCredential(
        tenant_id=config.AZURE_TENANT_ID,
        client_id=config.AZURE_CLIENT_ID,
        client_secret=config.AZURE_CLIENT_SECRET,
    )
    return credential.get_token("https://graph.microsoft.com/.default").token


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}


async def _get_drive_id(site_id: str) -> str:
    """Get the default document library drive ID for a site."""
    headers = _headers()
    r = httpx.get(f"{GRAPH}/sites/{site_id}/drives", headers=headers)
    r.raise_for_status()
    return r.json()["value"][0]["id"]


async def _create_folder(drive_id: str, parent_path: str, folder_name: str) -> None:
    """Create a folder. Ignores if already exists."""
    headers = _headers()
    if not parent_path:
        url = f"{GRAPH}/drives/{drive_id}/root/children"
    else:
        url = f"{GRAPH}/drives/{drive_id}/root:/{parent_path}:/children"

    body = {
        "name": folder_name,
        "folder": {},
        "@microsoft.graph.conflictBehavior": "fail",
    }
    r = httpx.post(url, headers=headers, json=body)
    if r.status_code == 409:
        print(f"[SHAREPOINT] Folder already exists: {parent_path or 'root'}/{folder_name}")
    elif r.status_code in (200, 201):
        print(f"[SHAREPOINT] Created folder: {parent_path or 'root'}/{folder_name}")
    else:
        print(f"[SHAREPOINT] Error creating {parent_path or 'root'}/{folder_name}: {r.status_code} {r.text[:200]}")


# ---------------------------------------------------------------------------
# Step 3: Internal Client Workspace (in wAIFinder site under Clients/)
# ---------------------------------------------------------------------------

async def create_internal_client_site(company_name: str) -> str:
    """Create internal client folder structure in wAIFinder/Clients/<CompanyName>/."""
    site_id = config.INTERNAL_SITE_ID
    if not site_id:
        print("[SHAREPOINT] No INTERNAL_SITE_ID configured")
        return "(not configured)"

    drive_id = await _get_drive_id(site_id)

    # Ensure Clients/ exists, then create client subfolder tree
    folders = [
        ("", "Clients"),
        ("Clients", company_name),
        (f"Clients/{company_name}", "Scoping"),
        (f"Clients/{company_name}", "Proposal"),
        (f"Clients/{company_name}", "Delivery"),
        (f"Clients/{company_name}/Delivery", "Tasks"),
        (f"Clients/{company_name}/Delivery", "Deliverables"),
        (f"Clients/{company_name}", "Financials"),
    ]
    for parent, name in folders:
        await _create_folder(drive_id, parent, name)

    site_url = f"{config.SHAREPOINT_TENANT_URL}/sites/wAIFinder/Shared%20Documents/Clients/{company_name}"
    print(f"[SHAREPOINT] Internal workspace ready: {site_url}")
    return site_url


# ---------------------------------------------------------------------------
# Step 4: Client Portal Page (in shared CFA-Client-Portal site)
# ---------------------------------------------------------------------------

async def create_client_portal_site(req: ScopingRequest) -> str:
    """Create a client page in the shared CFA-Client-Portal site."""
    company = req.organization.safe_name
    portal_site_id = config.CFA_CLIENT_PORTAL_SITE_ID

    if not portal_site_id:
        print("[SHAREPOINT] No CFA_CLIENT_PORTAL_SITE_ID configured - skipping portal page")
        return "(not configured)"

    headers = _headers()

    # Create page
    page_body = {
        "@odata.type": "#microsoft.graph.sitePage",
        "name": f"{company}.aspx",
        "title": f"{req.organization.name} - CFA Project",
        "pageLayout": "article",
    }

    url = f"{GRAPH_BETA}/sites/{portal_site_id}/pages"
    r = httpx.post(url, headers=headers, json=page_body)

    if r.status_code in (200, 201):
        page_data = r.json()
        page_id = page_data.get("id", "")
        page_web_url = page_data.get("webUrl", "")
        print(f"[SHAREPOINT] Portal page created: {company}.aspx (ID: {page_id})")

        # Publish
        publish_url = f"{GRAPH_BETA}/sites/{portal_site_id}/pages/{page_id}/microsoft.graph.sitePage/publish"
        pr = httpx.post(publish_url, headers=headers)
        if pr.status_code in (200, 204):
            print(f"[SHAREPOINT] Portal page published")

        portal_page_url = page_web_url or f"{config.SHAREPOINT_TENANT_URL}/sites/CFAClientPortal/SitePages/{company}.aspx"

        # Upload branded HTML content alongside the page
        await _upload_page_content(portal_site_id, req)

        # Save URL to internal workspace for reference
        await _save_portal_url(company, portal_page_url)

        return portal_page_url
    else:
        print(f"[SHAREPOINT] Page creation failed: {r.status_code} {r.text[:300]}")
        return await _create_fallback_page(portal_site_id, req)


async def _upload_page_content(portal_site_id: str, req: ScopingRequest) -> None:
    """Upload rich HTML content alongside the SharePoint page."""
    company = req.organization.safe_name
    drive_id = await _get_drive_id(portal_site_id)
    headers = _headers()
    headers["Content-Type"] = "text/html"

    html = f"""<!DOCTYPE html>
<html>
<head><title>{req.organization.name} - CFA Project Portal</title>
<style>
body {{ font-family: Segoe UI, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; }}
h1 {{ color: #003366; border-bottom: 2px solid #003366; padding-bottom: 10px; }}
h2 {{ color: #003366; margin-top: 30px; }}
.status {{ background: #e8f4f8; padding: 15px; border-radius: 8px; margin-top: 20px; }}
</style></head>
<body>
<h1>{req.organization.name}</h1>
<h2>About {req.organization.name}</h2>
<p>{req.organization.short_description or req.organization.name}</p>
<h2>Why This Project Matters</h2>
<p>CFA will work with {req.organization.name} to design and build an AI agent system
tailored to your operational needs, connecting your strategic priorities in
{req.organization.industry or 'your industry'} to practical, production-grade automation.</p>
<h2>Your Partner: Computing for All</h2>
<p>Computing for All is an agentic data engineering firm. We design, build, and operate
AI agent systems that unlock the intelligence in your data.</p>
<h2>Your CFA Team</h2>
<ul>
<li><strong>Ritu Bahl</strong> - Executive Director</li>
<li><strong>Gary</strong> - Technical Lead</li>
</ul>
<div class="status">
<h2>Project Status: Scoping in Progress</h2>
<p>We are currently in the scoping phase.</p>
</div>
</body></html>"""

    url = f"{GRAPH}/drives/{drive_id}/root:/{company}_content.html:/content"
    r = httpx.put(url, headers=headers, content=html.encode("utf-8"))
    if r.status_code in (200, 201):
        print(f"[SHAREPOINT] Page content HTML uploaded")


async def _save_portal_url(company_name: str, portal_url: str) -> None:
    """Save the client portal page URL to internal workspace for reference."""
    site_id = config.INTERNAL_SITE_ID
    if not site_id:
        return

    drive_id = await _get_drive_id(site_id)
    headers = _headers()
    headers["Content-Type"] = "text/plain"

    url = f"{GRAPH}/drives/{drive_id}/root:/Clients/{company_name}/Scoping/ClientPortalURL.txt:/content"
    r = httpx.put(url, headers=headers, content=portal_url.encode("utf-8"))
    if r.status_code in (200, 201):
        print(f"[SHAREPOINT] Saved portal URL to ClientPortalURL.txt")


async def _create_fallback_page(portal_site_id: str, req: ScopingRequest) -> str:
    """Fallback: upload an HTML page if the Pages API fails."""
    company = req.organization.safe_name
    drive_id = await _get_drive_id(portal_site_id)
    headers = _headers()
    headers["Content-Type"] = "text/html"

    html = f"""<!DOCTYPE html>
<html>
<head><title>{req.organization.name} - CFA Project Portal</title>
<style>
body {{ font-family: Segoe UI, sans-serif; max-width: 800px; margin: 40px auto; padding: 0 20px; color: #333; }}
h1 {{ color: #003366; border-bottom: 2px solid #003366; padding-bottom: 10px; }}
h2 {{ color: #003366; margin-top: 30px; }}
</style></head>
<body>
<h1>{req.organization.name}</h1>
<p><em>{req.organization.short_description or req.organization.name}</em></p>
<h2>Your Partner: Computing for All</h2>
<p>Computing for All is an agentic data engineering firm. We design, build, and operate
AI agent systems that unlock the intelligence in your data.</p>
<h2>Your CFA Team</h2>
<ul><li><strong>Ritu Bahl</strong> - Executive Director</li><li><strong>Gary</strong> - Technical Lead</li></ul>
<h2>Project Status: Scoping in Progress</h2>
</body></html>"""

    url = f"{GRAPH}/drives/{drive_id}/root:/{company}.html:/content"
    r = httpx.put(url, headers=headers, content=html.encode("utf-8"))
    if r.status_code in (200, 201):
        web_url = r.json().get("webUrl", "")
        print(f"[SHAREPOINT] Fallback HTML page uploaded: {company}.html")
        await _save_portal_url(company, web_url)
        return web_url
    print(f"[SHAREPOINT] Fallback page failed: {r.status_code}")
    return "(failed)"


# ---------------------------------------------------------------------------
# Document upload (to wAIFinder/Clients/ internal site)
# ---------------------------------------------------------------------------

def list_client_documents_sync(company_safe_name: str, recursive: bool = True) -> list[dict]:
    """List all files in /sites/wAIFinder/Clients/<SafeName>/ (sync version).

    Returns a flat list of file descriptors:
      [
        {
          "name": "Briefing_TestCompanyInc_2026-04-05.docx",
          "folder_path": "Clients/TestCompanyInc/Scoping",
          "size": 36976,
          "last_modified": "2026-04-05T18:24:11Z",
          "web_url": "https://...",
          "download_url": "https://...",
          "mime_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        },
        ...
      ]
    Folders are NOT returned — only files.
    Returns [] if SharePoint isn't configured or the folder doesn't exist yet.
    """
    site_id = config.INTERNAL_SITE_ID
    if not site_id:
        return []

    try:
        headers = {"Authorization": f"Bearer {_get_token()}"}
        r = httpx.get(f"{GRAPH}/sites/{site_id}/drives", headers=headers)
        r.raise_for_status()
        drive_id = r.json()["value"][0]["id"]
    except Exception as e:
        print(f"[SHAREPOINT] list drive lookup failed: {e}")
        return []

    root_path = f"Clients/{company_safe_name}"
    results: list[dict] = []

    def _walk(path: str) -> None:
        url = f"{GRAPH}/drives/{drive_id}/root:/{path}:/children"
        try:
            r = httpx.get(url, headers=headers, timeout=20.0)
        except Exception as e:
            print(f"[SHAREPOINT] list {path} exception: {e}")
            return
        if r.status_code == 404:
            return  # folder doesn't exist yet
        if r.status_code != 200:
            print(f"[SHAREPOINT] list {path}: HTTP {r.status_code} {r.text[:200]}")
            return
        for item in r.json().get("value", []):
            if "folder" in item:
                if recursive:
                    _walk(f"{path}/{item['name']}")
            else:
                file_info = item.get("file", {}) or {}
                results.append({
                    "name": item.get("name", ""),
                    "folder_path": path,
                    "relative_path": path[len(root_path) + 1:] if path != root_path else "",
                    "size": item.get("size", 0),
                    "last_modified": item.get("lastModifiedDateTime", ""),
                    "created": item.get("createdDateTime", ""),
                    "web_url": item.get("webUrl", ""),
                    "download_url": item.get("@microsoft.graph.downloadUrl", ""),
                    "mime_type": file_info.get("mimeType", ""),
                    "id": item.get("id", ""),
                })

    _walk(root_path)
    return results


async def upload_document(local_path: str, sharepoint_path: str) -> str:
    """Upload a file to the internal wAIFinder site under Clients/. Returns the URL."""
    site_id = config.INTERNAL_SITE_ID
    if not site_id:
        print(f"[SHAREPOINT] No INTERNAL_SITE_ID - skipping upload")
        return f"(not configured) {sharepoint_path}"

    drive_id = await _get_drive_id(site_id)
    headers = _headers()
    headers["Content-Type"] = "application/octet-stream"

    with open(local_path, "rb") as f:
        content = f.read()

    # All uploads go under Clients/
    full_path = f"Clients/{sharepoint_path}"
    url = f"{GRAPH}/drives/{drive_id}/root:/{full_path}:/content"
    r = httpx.put(url, headers=headers, content=content, timeout=60.0)

    if r.status_code in (200, 201):
        web_url = r.json().get("webUrl", sharepoint_path)
        print(f"[SHAREPOINT] Uploaded {local_path} -> {full_path}")
        return web_url
    else:
        print(f"[SHAREPOINT] Upload failed: {r.status_code} {r.text[:200]}")
        return f"(upload failed) {sharepoint_path}"
