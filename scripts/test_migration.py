"""Verify the Scoping/Grant agent migration by importing every module
and running a live Graph API call through the new package structure.
"""
import sys
import traceback
from pathlib import Path

# Add wfd-os root to sys.path so `from agents.graph...` works
WFD_OS_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(WFD_OS_ROOT))


def check(label, fn):
    try:
        result = fn()
        print(f"  [OK]   {label}")
        return result
    except Exception as e:
        print(f"  [FAIL] {label}")
        print(f"         {type(e).__name__}: {e}")
        traceback.print_exc()
        return None


def main():
    print("=" * 60)
    print("Migration Verification")
    print("=" * 60)

    print("\n[1] Import graph package config...")
    def _cfg():
        from agents.graph import config
        assert config.AZURE_TENANT_ID, "AZURE_TENANT_ID empty"
        assert config.AZURE_CLIENT_ID, "AZURE_CLIENT_ID empty"
        assert config.AZURE_CLIENT_SECRET, "AZURE_CLIENT_SECRET empty"
        assert config.INTERNAL_SITE_ID, "INTERNAL_SITE_ID empty"
        return config
    cfg = check("config loaded with Graph credentials", _cfg)

    print("\n[2] Import graph modules...")
    check("agents.graph.auth", lambda: __import__("agents.graph.auth", fromlist=["*"]))
    check("agents.graph.sharepoint", lambda: __import__("agents.graph.sharepoint", fromlist=["*"]))
    check("agents.graph.teams", lambda: __import__("agents.graph.teams", fromlist=["*"]))
    check("agents.graph.transcript", lambda: __import__("agents.graph.transcript", fromlist=["*"]))

    print("\n[3] Import scoping modules...")
    check("agents.scoping.models", lambda: __import__("agents.scoping.models", fromlist=["*"]))
    check("agents.scoping.research", lambda: __import__("agents.scoping.research", fromlist=["*"]))
    check("agents.scoping.briefing", lambda: __import__("agents.scoping.briefing", fromlist=["*"]))
    check("agents.scoping.proposal", lambda: __import__("agents.scoping.proposal", fromlist=["*"]))
    check("agents.scoping.transcript_analysis", lambda: __import__("agents.scoping.transcript_analysis", fromlist=["*"]))
    check("agents.scoping.pipeline", lambda: __import__("agents.scoping.pipeline", fromlist=["*"]))
    check("agents.scoping.postcall", lambda: __import__("agents.scoping.postcall", fromlist=["*"]))
    check("agents.scoping.webhook", lambda: __import__("agents.scoping.webhook", fromlist=["*"]))

    print("\n[4] Live Graph API call through migrated code...")
    def _live_call():
        from agents.graph.auth import _get_credential
        cred = _get_credential()
        token = cred.get_token("https://graph.microsoft.com/.default")
        assert token.token, "empty token"
        return len(token.token)
    token_len = check("get_graph_client() -> token acquired", _live_call)
    if token_len:
        print(f"         token length: {token_len} chars")

    def _site_call():
        import requests
        from agents.graph import config
        from agents.graph.auth import _get_credential
        cred = _get_credential()
        token = cred.get_token("https://graph.microsoft.com/.default").token
        r = requests.get(
            f"https://graph.microsoft.com/v1.0/sites/{config.INTERNAL_SITE_ID}",
            headers={"Authorization": f"Bearer {token}"},
        )
        r.raise_for_status()
        return r.json().get("displayName")
    site_name = check("fetch INTERNAL_SITE_ID from SharePoint", _site_call)
    if site_name:
        print(f"         site name: {site_name}")

    print("\n[5] Instantiate a ScopingRequest model...")
    def _model():
        from wfdos_common.models.scoping import ScopingRequest, Contact, Organization
        req = ScopingRequest(
            contact=Contact(first_name="Jane", last_name="Doe", email="jane@testcorp.com"),
            organization=Organization(name="Test Corp", industry="Data analytics"),
        )
        return f"{req.contact.full_name} at {req.organization.safe_name}"
    result = check("ScopingRequest instantiated", _model)
    if result:
        print(f"         {result}")

    print("\n" + "=" * 60)
    print("Migration verification complete.")
    print("=" * 60)


if __name__ == "__main__":
    main()
