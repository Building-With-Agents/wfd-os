"""Evidence Collector: pulls audit-relevant evidence from Microsoft 365.

For a given grant and date range, this gathers:
  - Teams messages mentioning the grant
  - SharePoint files in the grant's documentation library
  - Outlook emails to/from the funder

The output is a structured `Evidence` record that can be attached to a
transaction, allocation, or report draft as supporting documentation.

NOTHING is auto-attached. The collector returns evidence; a human (via the
review queue) decides what counts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from typing import Any

from grant_compliance.integrations.msgraph.client import GraphClient


@dataclass
class EvidenceItem:
    source: str  # "teams" | "sharepoint" | "outlook"
    item_type: str  # "message" | "file" | "email"
    identifier: str  # platform-specific id (graph object id, web URL, etc.)
    title: str
    snippet: str
    occurred_at: datetime | None = None
    url: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EvidenceBundle:
    grant_id: str
    period_start: date
    period_end: date
    items: list[EvidenceItem] = field(default_factory=list)
    collected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class EvidenceCollector:
    """Stateless collector. Construct with a GraphClient; call methods to gather."""

    def __init__(self, graph: GraphClient):
        self.graph = graph

    # ----- Teams --------------------------------------------------------

    def collect_teams_mentions(
        self, query: str, top: int = 25
    ) -> list[EvidenceItem]:
        """Find Teams chat/channel messages matching `query`. Use the grant
        name, award number, or program code as the query.
        """
        results = self.graph.search_messages(query, top=top)
        items: list[EvidenceItem] = []
        for hits in results:
            for container in hits.get("hitsContainers", []):
                for hit in container.get("hits", []):
                    resource = hit.get("resource", {})
                    items.append(
                        EvidenceItem(
                            source="teams",
                            item_type="message",
                            identifier=resource.get("id", ""),
                            title=(resource.get("subject") or "(no subject)")[:200],
                            snippet=(hit.get("summary") or "")[:500],
                            occurred_at=_parse_dt(resource.get("createdDateTime")),
                            url=resource.get("webUrl"),
                            metadata={
                                "from": (
                                    resource.get("from", {}).get("user", {}).get("displayName")
                                ),
                                "channel_id": resource.get("channelIdentity", {}).get("channelId"),
                                "team_id": resource.get("channelIdentity", {}).get("teamId"),
                            },
                        )
                    )
        return items

    # ----- SharePoint ---------------------------------------------------

    def collect_sharepoint_docs(
        self, drive_id: str, query: str
    ) -> list[EvidenceItem]:
        """Search the named drive (typically the grant's documentation library)
        for files matching `query`.
        """
        results = self.graph.search_drive(drive_id, query)
        items: list[EvidenceItem] = []
        for f in results:
            items.append(
                EvidenceItem(
                    source="sharepoint",
                    item_type="file",
                    identifier=f.get("id", ""),
                    title=f.get("name", ""),
                    snippet=f.get("description") or f.get("file", {}).get("mimeType", ""),
                    occurred_at=_parse_dt(f.get("lastModifiedDateTime")),
                    url=f.get("webUrl"),
                    metadata={
                        "size": f.get("size"),
                        "created_by": (
                            f.get("createdBy", {}).get("user", {}).get("displayName")
                        ),
                        "drive_id": drive_id,
                    },
                )
            )
        return items

    # ----- Outlook ------------------------------------------------------

    def collect_funder_emails(
        self, funder_domain: str, since: date, until: date
    ) -> list[EvidenceItem]:
        """Pull emails from anyone at funder_domain in the date range. Useful
        for documenting funder approvals, prior-approval requests, and
        award-letter exchanges.
        """
        # Graph $filter on date range + from-domain
        filter_clause = (
            f"receivedDateTime ge {since.isoformat()}T00:00:00Z "
            f"and receivedDateTime le {until.isoformat()}T23:59:59Z "
            f"and contains(from/emailAddress/address, '@{funder_domain}')"
        )
        msgs = self.graph.list_messages(filter_clause=filter_clause, top=100)
        items: list[EvidenceItem] = []
        for m in msgs:
            items.append(
                EvidenceItem(
                    source="outlook",
                    item_type="email",
                    identifier=m.get("id", ""),
                    title=(m.get("subject") or "(no subject)")[:200],
                    snippet=(m.get("bodyPreview") or "")[:500],
                    occurred_at=_parse_dt(m.get("receivedDateTime")),
                    url=m.get("webLink"),
                    metadata={
                        "from": m.get("from", {}).get("emailAddress", {}).get("address"),
                        "to": [
                            r.get("emailAddress", {}).get("address")
                            for r in m.get("toRecipients", [])
                        ],
                        "has_attachments": m.get("hasAttachments", False),
                    },
                )
            )
        return items

    # ----- Bundle for a grant ------------------------------------------

    def bundle_for_grant(
        self,
        *,
        grant_id: str,
        grant_name: str,
        award_number: str | None,
        funder_email_domain: str | None,
        sharepoint_drive_id: str | None,
        period_start: date,
        period_end: date,
    ) -> EvidenceBundle:
        bundle = EvidenceBundle(
            grant_id=grant_id, period_start=period_start, period_end=period_end
        )
        # Teams: search both name and award number
        for q in filter(None, [grant_name, award_number]):
            bundle.items.extend(self.collect_teams_mentions(q))
        # SharePoint: search the drive for any file mentioning the grant name
        if sharepoint_drive_id and grant_name:
            bundle.items.extend(
                self.collect_sharepoint_docs(sharepoint_drive_id, grant_name)
            )
        # Outlook: funder correspondence in period
        if funder_email_domain:
            bundle.items.extend(
                self.collect_funder_emails(funder_email_domain, period_start, period_end)
            )
        return bundle


def _parse_dt(s: str | None) -> datetime | None:
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace("Z", "+00:00"))
    except ValueError:
        return None
