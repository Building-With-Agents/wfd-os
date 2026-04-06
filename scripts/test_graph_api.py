"""Test Microsoft Graph API credentials from wfd-os/.env"""
import os
import requests
from dotenv import load_dotenv

load_dotenv("C:/Users/ritub/projects/wfd-os/.env", override=True)

TENANT_ID = os.getenv("GRAPH_TENANT_ID")
CLIENT_ID = os.getenv("GRAPH_CLIENT_ID")
CLIENT_SECRET = os.getenv("GRAPH_CLIENT_SECRET")
INTERNAL_SITE_ID = os.getenv("INTERNAL_SITE_ID")


def get_token():
    url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    r = requests.post(url, data={
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": "https://graph.microsoft.com/.default",
    })
    r.raise_for_status()
    return r.json()["access_token"]


def main():
    print("=" * 60)
    print("Microsoft Graph API Credential Test")
    print("=" * 60)
    print(f"Tenant: {TENANT_ID}")
    print(f"Client: {CLIENT_ID}")
    print(f"Secret: {CLIENT_SECRET[:6]}...{CLIENT_SECRET[-4:]}")
    print()

    # Step 1: Get token
    print("[1] Getting OAuth token...")
    try:
        token = get_token()
        print(f"    OK - token acquired ({len(token)} chars)")
    except Exception as e:
        print(f"    FAIL: {e}")
        return

    headers = {"Authorization": f"Bearer {token}"}

    # Step 2: Test SharePoint site access (app-auth compatible)
    print("\n[2] Testing SharePoint site access (INTERNAL_SITE_ID)...")
    try:
        r = requests.get(
            f"https://graph.microsoft.com/v1.0/sites/{INTERNAL_SITE_ID}",
            headers=headers,
        )
        if r.ok:
            site = r.json()
            print(f"    OK - {site.get('displayName', site.get('name'))}")
            print(f"    URL: {site.get('webUrl')}")
        else:
            print(f"    FAIL ({r.status_code}): {r.text[:200]}")
    except Exception as e:
        print(f"    FAIL: {e}")

    # Step 3: Test Teams access
    print("\n[3] Testing Teams access (CFA_TEAM_ID)...")
    team_id = os.getenv("CFA_TEAM_ID")
    try:
        r = requests.get(
            f"https://graph.microsoft.com/v1.0/teams/{team_id}",
            headers=headers,
        )
        if r.ok:
            team = r.json()
            print(f"    OK - {team.get('displayName')}")
        else:
            print(f"    FAIL ({r.status_code}): {r.text[:200]}")
    except Exception as e:
        print(f"    FAIL: {e}")

    # Step 4: List a few SharePoint sites
    print("\n[4] Listing SharePoint sites (first 5)...")
    try:
        r = requests.get(
            "https://graph.microsoft.com/v1.0/sites?search=*&$top=5",
            headers=headers,
        )
        if r.ok:
            sites = r.json().get("value", [])
            print(f"    OK - found {len(sites)} sites")
            for s in sites[:5]:
                print(f"      - {s.get('displayName', s.get('name'))}")
        else:
            print(f"    FAIL ({r.status_code}): {r.text[:200]}")
    except Exception as e:
        print(f"    FAIL: {e}")

    print()
    print("=" * 60)
    print("Credential test complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
