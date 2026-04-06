"""Inspect cfa_studentdetails field names and sample data."""
import os, json, requests
from dotenv import load_dotenv

load_dotenv("C:/Users/ritub/projects/wfd-os/.env")

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
DYNAMICS_URL = os.getenv("DYNAMICS_PRIMARY_URL")

url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
r = requests.post(url, data={
    "grant_type": "client_credentials",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "scope": f"{DYNAMICS_URL}/.default"
})
token = r.json()["access_token"]
headers = {"Authorization": f"Bearer {token}", "Accept": "application/json",
           "Prefer": "odata.maxpagesize=3"}

# Fetch 3 sample student details
r = requests.get(f"{DYNAMICS_URL}/api/data/v9.2/cfa_studentdetailses",
                 headers=headers)
data = r.json()
records = data.get("value", [])

if records:
    print(f"=== cfa_studentdetails: {len(records)} sample records ===")
    print(f"\nAll field names ({len(records[0])} fields):")
    for k in sorted(records[0].keys()):
        v = records[0][k]
        if v is not None and not str(k).startswith("@"):
            print(f"  {k} = {str(v)[:100]}")
    print(f"\n--- Non-null fields in sample record ---")
    non_null = {k: v for k, v in records[0].items()
                if v is not None and not k.startswith("@") and not k.startswith("_")}
    for k, v in sorted(non_null.items()):
        print(f"  {k}: {str(v)[:120]}")
else:
    # Try alternate entity set name
    print("Trying cfa_studentdetails...")
    r2 = requests.get(f"{DYNAMICS_URL}/api/data/v9.2/cfa_studentdetails",
                      headers=headers)
    if r2.status_code == 200:
        data2 = r2.json()
        records2 = data2.get("value", [])
        if records2:
            print(f"Found via cfa_studentdetails: {len(records2)} samples")
            for k in sorted(records2[0].keys()):
                v = records2[0][k]
                if v is not None and not str(k).startswith("@"):
                    print(f"  {k} = {str(v)[:100]}")
    else:
        print(f"cfa_studentdetails status: {r2.status_code}")
        print(r2.text[:500])
