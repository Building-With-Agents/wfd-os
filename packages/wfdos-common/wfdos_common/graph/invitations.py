"""SharePoint sharing invites via Microsoft Graph.

Grants folder-level access to a client by sending a sharing invitation email
directly from SharePoint. This is different from an Entra B2B guest invite
(`POST /invitations`) — this uses `POST /drives/{drive-id}/items/{item-id}/invite`
which creates a direct sharing permission on the target folder and emails the
recipient a link to accept.

For Phase 1 the target is:
  /sites/wAIFinder/Clients/<SafeName>/
"""

import httpx
from azure.identity import ClientSecretCredential
from wfdos_common.graph import config

GRAPH = "https://graph.microsoft.com/v1.0"


def _get_token() -> str:
    credential = ClientSecretCredential(
        tenant_id=config.AZURE_TENANT_ID,
        client_id=config.AZURE_CLIENT_ID,
        client_secret=config.AZURE_CLIENT_SECRET,
    )
    return credential.get_token("https://graph.microsoft.com/.default").token


def _headers() -> dict:
    return {"Authorization": f"Bearer {_get_token()}", "Content-Type": "application/json"}


def _get_drive_id_sync(site_id: str) -> str:
    r = httpx.get(f"{GRAPH}/sites/{site_id}/drives", headers=_headers())
    r.raise_for_status()
    return r.json()["value"][0]["id"]


def invite_to_client_folder(
    company_safe_name: str,
    email: str,
    display_name: str = "",
    message: str = "",
    roles: list[str] | None = None,
    require_sign_in: bool = True,
    send_invitation_email: bool = True,
) -> dict:
    """Grant a client access to their folder under wAIFinder/Clients/<SafeName>/.

    Args:
        company_safe_name: PascalCase company name (req.organization.safe_name)
        email:             Recipient email
        display_name:      Friendly name for the recipient
        message:           Message included in the SharePoint invitation email
        roles:             ["read"] (default) or ["write"]
        require_sign_in:   True = recipient must sign in (recommended)
        send_invitation_email: True = SharePoint sends the invitation email

    Returns:
        {"ok": bool, "status": int, "folder_path": str, "response": dict | str, "error": str | None}
    """
    if roles is None:
        roles = ["read"]

    site_id = config.INTERNAL_SITE_ID
    if not site_id:
        return {"ok": False, "status": 0, "folder_path": "", "response": "", "error": "INTERNAL_SITE_ID not configured"}

    folder_path = f"Clients/{company_safe_name}"

    try:
        drive_id = _get_drive_id_sync(site_id)
    except Exception as e:
        return {"ok": False, "status": 0, "folder_path": folder_path, "response": "", "error": f"drive lookup failed: {e}"}

    # Graph endpoint: POST /drives/{drive-id}/root:/{path}:/invite
    url = f"{GRAPH}/drives/{drive_id}/root:/{folder_path}:/invite"
    body: dict = {
        "requireSignIn": require_sign_in,
        "sendInvitation": send_invitation_email,
        "roles": roles,
        "recipients": [{"email": email}],
    }
    if message:
        body["message"] = message

    try:
        r = httpx.post(url, headers=_headers(), json=body, timeout=30.0)
        ok = r.status_code in (200, 201)
        try:
            resp_json = r.json()
        except Exception:
            resp_json = r.text[:500]
        if ok:
            print(f"[SHAREPOINT INVITE] Granted {roles} to {email} on {folder_path}")
        else:
            print(f"[SHAREPOINT INVITE] FAILED {r.status_code} on {folder_path}: {str(resp_json)[:300]}")
        return {
            "ok": ok,
            "status": r.status_code,
            "folder_path": folder_path,
            "response": resp_json,
            "error": None if ok else f"HTTP {r.status_code}",
        }
    except Exception as e:
        print(f"[SHAREPOINT INVITE] Exception: {type(e).__name__}: {e}")
        return {"ok": False, "status": 0, "folder_path": folder_path, "response": "", "error": f"{type(e).__name__}: {e}"}
