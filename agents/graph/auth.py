"""Microsoft Graph API authentication — shared across all Graph modules."""

import httpx
from azure.identity import ClientSecretCredential
from msgraph import GraphServiceClient
from agents.graph import config


_client: GraphServiceClient | None = None
_credential: ClientSecretCredential | None = None


def _get_credential() -> ClientSecretCredential:
    global _credential
    if _credential is None:
        _credential = ClientSecretCredential(
            tenant_id=config.AZURE_TENANT_ID,
            client_id=config.AZURE_CLIENT_ID,
            client_secret=config.AZURE_CLIENT_SECRET,
        )
    return _credential


def get_graph_client() -> GraphServiceClient:
    """Get or create the Graph API client (singleton)."""
    global _client
    if _client is None:
        _client = GraphServiceClient(_get_credential())
    return _client


async def graph_post(url: str, body: dict) -> dict:
    """Direct POST to Graph API with app token. Used for operations
    where the msgraph SDK requires delegated permissions (e.g. channel messages)."""
    credential = _get_credential()
    token = credential.get_token("https://graph.microsoft.com/.default")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            url,
            headers={
                "Authorization": f"Bearer {token.token}",
                "Content-Type": "application/json",
            },
            json=body,
        )
        if resp.status_code >= 400:
            print(f"[GRAPH] POST {url} failed ({resp.status_code}): {resp.text[:300]}")
        resp.raise_for_status()
        return resp.json()
