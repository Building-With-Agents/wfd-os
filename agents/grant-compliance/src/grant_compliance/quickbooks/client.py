"""Thin REST client for the QuickBooks Online Accounting API.

Docs: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities

Read-only methods only for now. Write methods (creating journal entries) are
explicitly NOT included until we have a human-approval gate. See CLAUDE.md.
"""

from __future__ import annotations

from typing import Any

import httpx

from grant_compliance.config import get_settings

API_BASE_PRODUCTION = "https://quickbooks.api.intuit.com"
API_BASE_SANDBOX = "https://sandbox-quickbooks.api.intuit.com"


class QbClient:
    def __init__(self, access_token: str, realm_id: str):
        self.access_token = access_token
        self.realm_id = realm_id
        settings = get_settings()
        self.base = (
            API_BASE_SANDBOX if settings.qb_environment == "sandbox" else API_BASE_PRODUCTION
        )

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        url = f"{self.base}/v3/company/{self.realm_id}/{path}"
        response = httpx.get(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            },
            params=params,
            timeout=30,
        )
        response.raise_for_status()
        return response.json()

    def query(self, sql: str) -> dict:
        """QB has its own SQL-like query language. Examples:
            "SELECT * FROM Account WHERE Active = true"
            "SELECT * FROM Bill WHERE TxnDate >= '2025-01-01' MAXRESULTS 1000"
        """
        return self._get("query", params={"query": sql, "minorversion": "73"})

    # ----- Convenience wrappers (all read-only) ---------------------------

    def list_accounts(self) -> list[dict]:
        return self.query("SELECT * FROM Account WHERE Active = true").get("QueryResponse", {}).get("Account", [])

    def list_classes(self) -> list[dict]:
        return self.query("SELECT * FROM Class WHERE Active = true").get("QueryResponse", {}).get("Class", [])

    def list_vendors(self) -> list[dict]:
        return self.query("SELECT * FROM Vendor WHERE Active = true").get("QueryResponse", {}).get("Vendor", [])

    def list_bills_since(self, since_iso_date: str) -> list[dict]:
        return self.query(
            f"SELECT * FROM Bill WHERE TxnDate >= '{since_iso_date}' MAXRESULTS 1000"
        ).get("QueryResponse", {}).get("Bill", [])

    def list_purchases_since(self, since_iso_date: str) -> list[dict]:
        # "Purchase" covers Check, CreditCardCharge, Cash expense
        return self.query(
            f"SELECT * FROM Purchase WHERE TxnDate >= '{since_iso_date}' MAXRESULTS 1000"
        ).get("QueryResponse", {}).get("Purchase", [])

    def list_journal_entries_since(self, since_iso_date: str) -> list[dict]:
        return self.query(
            f"SELECT * FROM JournalEntry WHERE TxnDate >= '{since_iso_date}' MAXRESULTS 1000"
        ).get("QueryResponse", {}).get("JournalEntry", [])
