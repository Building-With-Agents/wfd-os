"""Thin REST client for Microsoft Graph API v1.0.

Docs: https://learn.microsoft.com/en-us/graph/api/overview

Read-only methods only. Mutations (sending mail, posting to channels,
writing to SharePoint) are NOT exposed here yet — same principle as the
QuickBooks client. When write paths are added later, they go through a
separate module with its own approval gate.
"""

from __future__ import annotations

from typing import Any, Iterator
from urllib.parse import quote

import httpx

GRAPH_BASE = "https://graph.microsoft.com/v1.0"


class GraphClient:
    """Stateless wrapper. Pass an access_token at construction.

    The caller is responsible for refresh; if a 401 is returned, refresh
    the token and construct a new client.
    """

    def __init__(self, access_token: str, *, timeout: float = 30.0):
        self.access_token = access_token
        self._client = httpx.Client(
            base_url=GRAPH_BASE,
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
            timeout=timeout,
        )

    def __enter__(self) -> "GraphClient":
        return self

    def __exit__(self, *args) -> None:
        self._client.close()

    # ----- Low-level ----------------------------------------------------

    def get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        response = self._client.get(path, params=params)
        response.raise_for_status()
        return response.json()

    def get_paged(
        self, path: str, params: dict[str, Any] | None = None, max_pages: int = 50
    ) -> Iterator[dict]:
        """Iterate `value` items across paginated responses (`@odata.nextLink`)."""
        url: str | None = path
        page = 0
        while url and page < max_pages:
            if url.startswith("http"):
                response = httpx.get(
                    url,
                    headers=self._client.headers,
                    timeout=self._client.timeout,
                )
            else:
                response = self._client.get(url, params=params if page == 0 else None)
            response.raise_for_status()
            data = response.json()
            yield from data.get("value", [])
            url = data.get("@odata.nextLink")
            page += 1

    # ----- Identity -----------------------------------------------------

    def me(self) -> dict:
        return self.get("/me")

    # ----- Teams --------------------------------------------------------

    def list_my_teams(self) -> list[dict]:
        return list(self.get_paged("/me/joinedTeams"))

    def list_team_channels(self, team_id: str) -> list[dict]:
        return list(self.get_paged(f"/teams/{team_id}/channels"))

    def list_channel_messages(
        self, team_id: str, channel_id: str, top: int = 50
    ) -> list[dict]:
        return list(
            self.get_paged(
                f"/teams/{team_id}/channels/{channel_id}/messages",
                params={"$top": top},
            )
        )

    def search_messages(self, query: str, top: int = 25) -> list[dict]:
        """Cross-Teams chat + channel message search via the search endpoint."""
        body = {
            "requests": [
                {
                    "entityTypes": ["chatMessage"],
                    "query": {"queryString": query},
                    "from": 0,
                    "size": top,
                }
            ]
        }
        response = self._client.post("/search/query", json=body)
        response.raise_for_status()
        return response.json().get("value", [])

    # ----- SharePoint ---------------------------------------------------

    def list_sites(self, search: str | None = None) -> list[dict]:
        params = {"search": search} if search else None
        return list(self.get_paged("/sites", params=params))

    def get_site_by_path(self, hostname: str, site_path: str) -> dict:
        # site_path like "/sites/GrantCompliance"
        return self.get(f"/sites/{hostname}:{site_path}")

    def list_drive_items(self, drive_id: str, item_id: str = "root") -> list[dict]:
        return list(self.get_paged(f"/drives/{drive_id}/items/{item_id}/children"))

    def search_drive(self, drive_id: str, query: str) -> list[dict]:
        q = quote(query)
        return list(self.get_paged(f"/drives/{drive_id}/root/search(q='{q}')"))

    def download_file_content(self, drive_id: str, item_id: str) -> bytes:
        response = self._client.get(f"/drives/{drive_id}/items/{item_id}/content")
        response.raise_for_status()
        return response.content

    # ----- Outlook ------------------------------------------------------

    def list_messages(
        self,
        *,
        search: str | None = None,
        filter_clause: str | None = None,
        top: int = 50,
    ) -> list[dict]:
        params: dict[str, Any] = {"$top": top}
        if search:
            params["$search"] = f'"{search}"'
        if filter_clause:
            params["$filter"] = filter_clause
        # $search and $filter together require ConsistencyLevel: eventual
        headers = {"ConsistencyLevel": "eventual"} if (search or filter_clause) else {}
        response = self._client.get("/me/messages", params=params, headers=headers)
        response.raise_for_status()
        return response.json().get("value", [])

    def get_message(self, message_id: str) -> dict:
        return self.get(f"/me/messages/{message_id}")
