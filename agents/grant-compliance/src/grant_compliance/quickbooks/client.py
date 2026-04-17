"""QuickBooks Online REST client. READ-ONLY BY CONSTRUCTION.

This module is architecturally prevented from issuing non-GET HTTP requests.
Any attempt to POST, PUT, PATCH, or DELETE will raise NotImplementedError at
the transport layer, before the request reaches Intuit's servers.

Adding write paths requires ALL of the following:
  (a) Explicit human approval recorded in a design document
  (b) A separate `qb_writeback` module — do not add write methods here
  (c) A distinct OAuth credential (separate app registration or separate
      admin-authorized token) — this is audit separation at Intuit, NOT
      capability separation. The token's capabilities come from the
      OAuth scope, not from the authorizing user's role.
  (d) Its own approval gate and audit log entries for every write

See CLAUDE.md "Enforced constraints" section for the full three-layer
defense model (OAuth scope / _ReadOnlyHttpxClient / Intuit audit log).

QB Accounting API docs:
https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities
"""

from __future__ import annotations

from typing import Any

import httpx

from grant_compliance.config import get_settings

API_BASE_PRODUCTION = "https://quickbooks.api.intuit.com"
API_BASE_SANDBOX = "https://sandbox-quickbooks.api.intuit.com"


# --- Method name guards ----------------------------------------------------
# Tests in tests/test_quickbooks_readonly.py assert that no public method
# name on QbClient begins with any of these prefixes. A new developer
# naming a method `create_invoice`, `upsert_vendor`, or `save_journal_entry`
# will have a test fail at CI — before the method can be called against a
# real QB instance. This is redundant with the runtime NotImplementedError
# check below, but doubling the defense catches naming drift at PR time.
WRITE_METHOD_NAME_PREFIXES = (
    "create_",
    "update_",
    "delete_",
    "post_",
    "put_",
    "patch_",
    "insert_",
    "upsert_",
    "save_",
)


class _ReadOnlyHttpxClient(httpx.Client):
    """httpx.Client subclass that refuses non-GET requests at the transport layer."""

    def request(self, method, url, *args, **kwargs):  # type: ignore[override]
        if method.upper() != "GET":
            raise NotImplementedError(
                f"QbClient is read-only by construction. Attempted {method} to {url}. "
                "See quickbooks/client.py module docstring."
            )
        return super().request(method, url, *args, **kwargs)


class QbClient:
    """Read-only QuickBooks Online REST client.

    Every convenience method on this class is a SELECT against QB's SQL-like
    query API. No method may perform a non-GET request. See module docstring
    for the enforcement mechanism.
    """

    def __init__(self, access_token: str, realm_id: str):
        self.access_token = access_token
        self.realm_id = realm_id
        settings = get_settings()
        self.base = (
            API_BASE_SANDBOX if settings.qb_environment == "sandbox" else API_BASE_PRODUCTION
        )
        # The read-only wrapper. Every request issued by this client flows
        # through here. Directly constructing plain httpx.Client or calling
        # module-level httpx.get/post would bypass the guard, so we funnel
        # everything through self._http and review new code for that.
        self._http = _ReadOnlyHttpxClient(timeout=30)

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict:
        url = f"{self.base}/v3/company/{self.realm_id}/{path}"
        response = self._http.get(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "Accept": "application/json",
            },
            params=params,
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
