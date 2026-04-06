"""
Dataverse API client — authenticated wrapper for Market Intelligence Agent.
"""
import os
import requests
from functools import lru_cache
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"), override=True)

DYNAMICS_URL = os.getenv("DYNAMICS_PRIMARY_URL", "https://cfahelpdesksandbox.crm.dynamics.com")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")

_token_cache = {"token": None, "expires_at": 0}


def get_token() -> str:
    import time
    if _token_cache["token"] and time.time() < _token_cache["expires_at"] - 60:
        return _token_cache["token"]

    resp = requests.post(
        f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": f"{DYNAMICS_URL}/.default",
        },
        timeout=15,
    )
    resp.raise_for_status()
    data = resp.json()
    import time
    _token_cache["token"] = data["access_token"]
    _token_cache["expires_at"] = time.time() + data.get("expires_in", 3600)
    return _token_cache["token"]


def query(entity: str, select: str = None, filter: str = None, top: int = None,
          orderby: str = None, count: bool = False) -> dict:
    """Run an OData query against Dataverse."""
    params = []
    if select:
        params.append(f"$select={select}")
    if filter:
        params.append(f"$filter={filter}")
    if top:
        params.append(f"$top={top}")
    if orderby:
        params.append(f"$orderby={orderby}")
    if count:
        params.append("$count=true")

    url = f"{DYNAMICS_URL}/api/data/v9.2/{entity}"
    if params:
        url += "?" + "&".join(params)

    headers = {
        "Authorization": f"Bearer {get_token()}",
        "OData-Version": "4.0",
        "Accept": "application/json",
        "Prefer": "odata.include-annotations=OData.Community.Display.V1.FormattedValue",
    }

    resp = requests.get(url, headers=headers, timeout=30)
    resp.raise_for_status()
    return resp.json()


def get_all(entity: str, select: str = None, filter: str = None, orderby: str = None) -> list[dict]:
    """Fetch all records for an entity (handles paging)."""
    results = []
    url = f"{DYNAMICS_URL}/api/data/v9.2/{entity}"
    params = []
    if select:
        params.append(f"$select={select}")
    if filter:
        params.append(f"$filter={filter}")
    if orderby:
        params.append(f"$orderby={orderby}")
    params.append("$top=1000")
    if params:
        url += "?" + "&".join(params)

    headers = {
        "Authorization": f"Bearer {get_token()}",
        "OData-Version": "4.0",
        "Accept": "application/json",
    }

    while url:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get("value", []))
        url = data.get("@odata.nextLink")

    return results
