"""Tests enforcing the "QuickBooks is read-only by construction" constraint.

Six tests, matching the completion criteria in the Step 0 near-miss +
read-only enforcement instruction:

    test_qbclient_get_works             — GET requests flow through (MockTransport)
    test_qbclient_refuses_post          — POST raises NotImplementedError
    test_qbclient_refuses_put           — PUT raises NotImplementedError
    test_qbclient_refuses_patch         — PATCH raises NotImplementedError
    test_qbclient_refuses_delete        — DELETE raises NotImplementedError
    test_qbclient_has_no_write_method_names
                                        — introspect QbClient; fail if any
                                          public method name starts with any
                                          of the WRITE_METHOD_NAME_PREFIXES

See quickbooks/client.py module docstring and CLAUDE.md "Enforced constraints".
"""

from __future__ import annotations

import inspect

import httpx
import pytest

from grant_compliance.quickbooks.client import (
    WRITE_METHOD_NAME_PREFIXES,
    QbClient,
    _ReadOnlyHttpxClient,
)


# ---------------------------------------------------------------------------
# 1. GET still works
# ---------------------------------------------------------------------------


def test_qbclient_get_works():
    """GET requests are not intercepted by the read-only guard — they flow
    through to the underlying transport. We wire in httpx.MockTransport so
    the test exercises the full QbClient._get() path without touching
    Intuit's servers.
    """
    captured = {}

    def mock_handler(request: httpx.Request) -> httpx.Response:
        captured["method"] = request.method
        captured["url"] = str(request.url)
        return httpx.Response(
            status_code=200,
            json={"QueryResponse": {"Account": [{"Id": "1", "Name": "Checking"}]}},
        )

    client = QbClient(access_token="fake-token", realm_id="fake-realm-id")

    # Swap in a MockTransport-backed _ReadOnlyHttpxClient so the guard is
    # still in the call path but the transport never leaves the test.
    # Preserves the _ReadOnlyHttpxClient class identity for the guard.
    client._http.close()
    client._http = _ReadOnlyHttpxClient(transport=httpx.MockTransport(mock_handler))

    result = client.query("SELECT * FROM Account WHERE Active = true")

    assert captured["method"] == "GET"
    assert "/v3/company/fake-realm-id/query" in captured["url"]
    assert result == {"QueryResponse": {"Account": [{"Id": "1", "Name": "Checking"}]}}


# ---------------------------------------------------------------------------
# 2-5. Non-GET methods raise NotImplementedError through QbClient
# ---------------------------------------------------------------------------


def test_qbclient_refuses_post():
    """Attempting a POST via QbClient's httpx client raises NotImplementedError."""
    client = QbClient(access_token="fake", realm_id="fake-realm")
    with pytest.raises(NotImplementedError, match="read-only by construction"):
        client._http.post("https://sandbox-quickbooks.api.intuit.com/v3/company/fake-realm/bill")


def test_qbclient_refuses_put():
    """Attempting a PUT via QbClient's httpx client raises NotImplementedError."""
    client = QbClient(access_token="fake", realm_id="fake-realm")
    with pytest.raises(NotImplementedError, match="read-only by construction"):
        client._http.put("https://sandbox-quickbooks.api.intuit.com/v3/company/fake-realm/bill/1")


def test_qbclient_refuses_patch():
    """Attempting a PATCH via QbClient's httpx client raises NotImplementedError."""
    client = QbClient(access_token="fake", realm_id="fake-realm")
    with pytest.raises(NotImplementedError, match="read-only by construction"):
        client._http.patch("https://sandbox-quickbooks.api.intuit.com/v3/company/fake-realm/bill/1")


def test_qbclient_refuses_delete():
    """Attempting a DELETE via QbClient's httpx client raises NotImplementedError."""
    client = QbClient(access_token="fake", realm_id="fake-realm")
    with pytest.raises(NotImplementedError, match="read-only by construction"):
        client._http.delete("https://sandbox-quickbooks.api.intuit.com/v3/company/fake-realm/bill/1")


# ---------------------------------------------------------------------------
# 6. No public method name may suggest a write
# ---------------------------------------------------------------------------


def test_qbclient_has_no_write_method_names():
    """Introspect QbClient. Fail if any public method name starts with a
    write-suggestive prefix (create_, update_, delete_, post_, put_, patch_,
    insert_, upsert_, save_).

    If this test fails, someone has added a method to QbClient that appears
    intended to write. Do not relax the test — move the method to a
    separate qb_writeback module with its own approval gate, audit hooks,
    and a distinct QB user with write permissions. See CLAUDE.md
    "Enforced constraints".
    """
    public_method_names = [
        name
        for name, _ in inspect.getmembers(QbClient, predicate=callable)
        if not name.startswith("_")
    ]
    offenders = [
        name
        for name in public_method_names
        if any(name.startswith(prefix) for prefix in WRITE_METHOD_NAME_PREFIXES)
    ]
    assert offenders == [], (
        f"QbClient has methods whose names suggest writes: {offenders}. "
        f"Forbidden prefixes: {WRITE_METHOD_NAME_PREFIXES}. "
        f"Move write operations to a separate qb_writeback module."
    )
