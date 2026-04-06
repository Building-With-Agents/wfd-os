"""
Dataverse Discovery Script
Queries Dynamics 365 / Dataverse Web API to catalog custom entities,
record counts, and field definitions.
"""

import os
import sys
import io
import json
import requests
from pathlib import Path
from dotenv import load_dotenv

# Force UTF-8 output on Windows
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# ---------------------------------------------------------------------------
# 1. Load credentials from .env
# ---------------------------------------------------------------------------
ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(ENV_PATH)

TENANT_ID = os.getenv("AZURE_TENANT_ID")
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
DYNAMICS_URL = os.getenv("DYNAMICS_PRIMARY_URL")  # e.g. https://cfahelpdesksandbox.crm.dynamics.com

if not all([TENANT_ID, CLIENT_ID, CLIENT_SECRET, DYNAMICS_URL]):
    sys.exit("ERROR: Missing one or more required env vars "
             "(AZURE_TENANT_ID, AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, DYNAMICS_PRIMARY_URL)")

# Strip trailing slash if present
DYNAMICS_URL = DYNAMICS_URL.rstrip("/")
API_BASE = f"{DYNAMICS_URL}/api/data/v9.2"

# ---------------------------------------------------------------------------
# 2. Get OAuth token (client_credentials flow)
# ---------------------------------------------------------------------------
def get_token() -> str:
    token_url = f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token"
    payload = {
        "grant_type": "client_credentials",
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "scope": f"{DYNAMICS_URL}/.default",
    }
    resp = requests.post(token_url, data=payload, timeout=30)
    if resp.status_code != 200:
        print(f"Token request failed ({resp.status_code}):")
        print(resp.text)
        sys.exit(1)
    return resp.json()["access_token"]


print("=" * 70)
print("DATAVERSE DISCOVERY")
print("=" * 70)
print(f"Environment : {DYNAMICS_URL}")
print(f"Tenant      : {TENANT_ID}")
print(f"Client App  : {CLIENT_ID}")
print()

print("Authenticating ...", end=" ", flush=True)
TOKEN = get_token()
print("OK")
print()

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "OData-MaxVersion": "4.0",
    "OData-Version": "4.0",
}

# ---------------------------------------------------------------------------
# 3a. List ALL custom entities
# ---------------------------------------------------------------------------
print("=" * 70)
print("CUSTOM ENTITIES (IsCustomEntity = true)")
print("=" * 70)

custom_url = (
    f"{API_BASE}/EntityDefinitions"
    "?$filter=IsCustomEntity eq true"
    "&$select=LogicalName,DisplayName,EntitySetName,Description"
)
resp = requests.get(custom_url, headers=HEADERS, timeout=60)
if resp.status_code != 200:
    print(f"  ERROR {resp.status_code}: {resp.text[:500]}")
else:
    entities = resp.json().get("value", [])
    entities.sort(key=lambda e: e.get("LogicalName", ""))
    print(f"  Total custom entities: {len(entities)}\n")

    # Separate CFA-specific entities from platform entities
    cfa_entities = [e for e in entities if e.get("LogicalName", "").startswith("cfa_")]
    other_prefixes = {}
    for e in entities:
        name = e.get("LogicalName", "")
        prefix = name.split("_")[0] if "_" in name else name
        if not name.startswith("cfa_"):
            other_prefixes[prefix] = other_prefixes.get(prefix, 0) + 1

    print(f"  CFA-specific entities: {len(cfa_entities)}")
    print(f"  Other entity prefixes: {', '.join(f'{k}({v})' for k, v in sorted(other_prefixes.items()))}")
    print()

    print(f"  --- CFA Custom Entities ---")
    print(f"  {'Logical Name':<45} {'Entity Set Name':<50} {'Display Name'}")
    print(f"  {'-'*45} {'-'*50} {'-'*40}")
    for e in cfa_entities:
        display = ""
        dn = e.get("DisplayName")
        if dn and dn.get("LocalizedLabels"):
            display = dn["LocalizedLabels"][0].get("Label", "")
        print(f"  {e.get('LogicalName',''):<45} {e.get('EntitySetName',''):<50} {display}")
    print()

# ---------------------------------------------------------------------------
# 3b. Record counts for key entities
# ---------------------------------------------------------------------------
KEY_ENTITIES = [
    "contacts",
    "accounts",
    "cfa_studentdetails",
    "cfa_employerdetails",
    "cfa_studentjourneies",
    "cfa_reactportalusers",
    "cfa_lightcastjobs",
    "cfa_cfajobpostings",
    "cfa_collegeprograms",
    "cfa_careerprograms",
    "cfa_educationdetails",
    "cfa_studentworkexperiences",
]

print("=" * 70)
print("RECORD COUNTS")
print("=" * 70)
print(f"  {'Entity Set':<40} {'Count':>10}")
print(f"  {'-'*40} {'-'*10}")

count_headers = {**HEADERS, "Prefer": "odata.include-annotations=\"*\""}

for entity_set in KEY_ENTITIES:
    # Use /$count path to get a plain integer count
    count_url = f"{API_BASE}/{entity_set}/$count"
    try:
        resp = requests.get(count_url, headers=count_headers, timeout=120)
        if resp.status_code == 200:
            # Strip BOM and whitespace from plain-text count response
            count = resp.content.decode("utf-8-sig").strip()
            print(f"  {entity_set:<40} {count:>10}")
        elif resp.status_code == 404:
            print(f"  {entity_set:<40} {'NOT FOUND':>10}")
        else:
            # Fallback: try fetchXml aggregate count
            print(f"  {entity_set:<40} {'ERR ' + str(resp.status_code):>10}")
    except Exception as ex:
        print(f"  {entity_set:<40} {'TIMEOUT':>10}")

print()

# ---------------------------------------------------------------------------
# 3c. Field definitions for contacts
# ---------------------------------------------------------------------------
print("=" * 70)
print("FIELD DEFINITIONS — contact entity")
print("=" * 70)

attr_url = (
    f"{API_BASE}/EntityDefinitions(LogicalName='contact')/Attributes"
    "?$select=LogicalName,AttributeType,DisplayName,RequiredLevel"
)
resp = requests.get(attr_url, headers=HEADERS, timeout=60)
if resp.status_code != 200:
    print(f"  ERROR {resp.status_code}: {resp.text[:500]}")
else:
    attrs = resp.json().get("value", [])
    attrs.sort(key=lambda a: a.get("LogicalName", ""))
    print(f"  Found {len(attrs)} attributes\n")
    print(f"  {'Logical Name':<45} {'Type':<20} {'Required':<18} {'Display Name'}")
    print(f"  {'-'*45} {'-'*20} {'-'*18} {'-'*40}")
    for a in attrs:
        display = ""
        dn = a.get("DisplayName")
        if dn and dn.get("LocalizedLabels"):
            display = dn["LocalizedLabels"][0].get("Label", "")
        req = ""
        rl = a.get("RequiredLevel")
        if rl and rl.get("Value"):
            req = rl["Value"]
        print(f"  {a.get('LogicalName',''):<45} {a.get('AttributeType',''):<20} {str(req):<18} {display}")

print()
print("=" * 70)
print("DISCOVERY COMPLETE")
print("=" * 70)
