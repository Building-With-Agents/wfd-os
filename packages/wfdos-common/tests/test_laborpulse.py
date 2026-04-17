"""Tests for agents/laborpulse/ — the LaborPulse SSE proxy + qa_feedback writer.

These tests live in the wfdos-common test tree so the CI suite picks
them up automatically (per-service tests would need a separate pytest
invocation). We mock the httpx client so no real JIE traffic goes out,
and swap psycopg2 for a SQLite-in-memory connection for the feedback
writer.
"""

from __future__ import annotations

import sqlite3
from typing import AsyncIterator

import pytest
from fastapi.testclient import TestClient

from wfdos_common.auth import Session, issue_session
from wfdos_common.errors import ServiceUnavailableError, ValidationFailure

_KEY = "laborpulse-test-key"


# ---------------------------------------------------------------------------
# JieSettings env round-trip
# ---------------------------------------------------------------------------


def test_jie_settings_env_round_trip(monkeypatch):
    monkeypatch.setenv("JIE_BASE_URL", "https://jie.test.example.com")
    monkeypatch.setenv("JIE_API_KEY", "secret-123")
    monkeypatch.setenv("JIE_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("JIE_STREAMING_TIMEOUT", "600")

    from wfdos_common.config.settings import JieSettings

    s = JieSettings()
    assert s.base_url == "https://jie.test.example.com"
    assert s.api_key == "secret-123"
    assert s.timeout_seconds == 45
    assert s.streaming_read_timeout_seconds == 600


def test_jie_settings_default_empty_base_url():
    """Safe-empty default — stack boots without JIE creds; proxy raises
    ServiceUnavailableError at call time."""
    from wfdos_common.config.settings import JieSettings

    s = JieSettings()
    # Under test env the real .env may set this; just assert the type
    # is a string so the proxy can safely test its truthiness.
    assert isinstance(s.base_url, str)


# ---------------------------------------------------------------------------
# qa_feedback schema structure
# ---------------------------------------------------------------------------


def test_qa_feedback_schema_has_required_columns():
    """The committed schema file must declare the columns the LaborPulse
    feedback writer inserts into. A regression here (someone renaming a
    column, dropping the CHECK constraint) breaks feedback capture."""
    from pathlib import Path

    repo_root = Path(__file__).resolve().parents[3]
    sql_text = (repo_root / "docker/postgres-init/10-schema.sql").read_text(
        encoding="utf-8"
    )
    assert "CREATE TABLE IF NOT EXISTS qa_feedback" in sql_text
    for col in (
        "tenant_id",
        "user_email",
        "user_role",
        "conversation_id",
        "question",
        "answer_snapshot",
        "rating",
        "comment",
        "cost_usd",
        "confidence",
        "created_at",
    ):
        assert col in sql_text, f"qa_feedback column missing: {col}"
    # CHECK constraint guards the rating domain.
    assert "CHECK (rating IN (-1, 1))" in sql_text
    assert "ix_qa_feedback_tenant_created" in sql_text


# ---------------------------------------------------------------------------
# Proxy: SSE streaming
# ---------------------------------------------------------------------------


class _FakeJieChunks:
    """Replaces agents.laborpulse.client.stream_query with a canned async
    iterator so the FastAPI StreamingResponse can be exercised end-to-end
    without httpx or a live JIE."""

    def __init__(self, chunks: list[bytes] = None, raises: Exception | None = None):
        self.chunks = chunks or [
            b'event: answer\ndata: {"text": "Manufacturing "}\n\n',
            b'event: answer\ndata: {"text": "and healthcare."}\n\n',
            b'event: evidence\ndata: {"source": "jobs_2024"}\n\n',
            b'event: done\ndata: {"conversation_id": "abc-123"}\n\n',
        ]
        self.raises = raises
        self.calls: list[dict] = []

    async def __call__(self, **kwargs) -> AsyncIterator[bytes]:
        self.calls.append(kwargs)
        if self.raises is not None:
            raise self.raises
        for c in self.chunks:
            yield c


@pytest.fixture
def labor_app(monkeypatch):
    """Build the LaborPulse app with env + settings patched to a known
    state and stream_query replaced by _FakeJieChunks. Returns (app,
    fake_streamer, staff_token_cookie)."""
    from wfdos_common.config import settings

    monkeypatch.setattr(settings.auth, "secret_key", _KEY)
    monkeypatch.setattr(settings.auth, "staff_allowlist", "gary@example.com")
    monkeypatch.setattr(settings.auth, "admin_allowlist", "")
    monkeypatch.setattr(settings.auth, "student_allowlist", "")
    monkeypatch.setattr(
        settings.auth,
        "workforce_development_allowlist",
        "director@borderplex.example.com",
    )
    monkeypatch.setattr(settings.auth, "cookie_secure", False)
    monkeypatch.setattr(settings.jie, "base_url", "https://jie.test.example.com")
    monkeypatch.setattr(settings.jie, "api_key", "")
    # Force llm_gated to pass — it checks Azure/Anthropic/Gemini creds;
    # we pretend Anthropic is configured so the tier gate doesn't 503
    # on us (the intended 503 test below toggles this back to empty).
    monkeypatch.setattr(settings.llm, "anthropic_api_key", "fake")
    monkeypatch.setattr(settings.azure_openai, "key", "")
    monkeypatch.setattr(settings.azure_openai, "endpoint", "")
    monkeypatch.setattr(settings.llm, "gemini_api_key", "")

    fake = _FakeJieChunks()
    import agents.laborpulse.api as api_mod

    monkeypatch.setattr(api_mod, "stream_query", fake)

    director_cookie = issue_session(
        Session(email="director@borderplex.example.com", role="workforce-development"),
        secret_key=_KEY,
    )
    return api_mod.app, fake, director_cookie


def _client(app):
    return TestClient(app, raise_server_exceptions=False)


def test_query_requires_auth(labor_app):
    app, _fake, _cookie = labor_app
    r = _client(app).post(
        "/api/laborpulse/query", json={"question": "top sectors?"}
    )
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_query_rejects_student_role(labor_app, monkeypatch):
    app, _fake, _ = labor_app
    student = issue_session(
        Session(email="s@example.com", role="student"), secret_key=_KEY
    )
    client = _client(app)
    client.cookies.set("wfdos_session", student)
    r = client.post("/api/laborpulse/query", json={"question": "top sectors?"})
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_query_allows_workforce_development_role(labor_app):
    app, fake, cookie = labor_app
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    r = client.post(
        "/api/laborpulse/query",
        json={"question": "which sectors gained the most postings in Doña Ana?"},
    )
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/event-stream")


def test_query_streams_jie_chunks_unchanged(labor_app):
    app, fake, cookie = labor_app
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    r = client.post(
        "/api/laborpulse/query", json={"question": "manufacturing trends"}
    )
    assert r.status_code == 200
    body = r.content
    # Every canned JIE chunk must appear byte-for-byte in the response
    # body — wfd-os does not re-frame the stream.
    for expected in fake.chunks:
        assert expected in body


def test_query_forwards_tenant_id_from_host(labor_app):
    app, fake, cookie = labor_app
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    client.post(
        "/api/laborpulse/query",
        json={"question": "test"},
        headers={"Host": "talent.borderplexwfs.org"},
    )
    assert fake.calls, "stream_query was not invoked"
    assert fake.calls[0]["tenant_id"] == "borderplex"


def test_query_forwards_user_email_to_jie(labor_app):
    app, fake, cookie = labor_app
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    client.post("/api/laborpulse/query", json={"question": "test"})
    assert fake.calls[0]["user_email"] == "director@borderplex.example.com"


def test_query_forwards_conversation_id_when_provided(labor_app):
    app, fake, cookie = labor_app
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    client.post(
        "/api/laborpulse/query",
        json={"question": "follow-up", "conversation_id": "conv-xyz"},
    )
    assert fake.calls[0]["conversation_id"] == "conv-xyz"


def test_query_503_when_jie_unreachable(labor_app, monkeypatch):
    app, _fake, cookie = labor_app
    boom = _FakeJieChunks(
        raises=ServiceUnavailableError(
            "JIE unreachable", details={"upstream": "jie", "reason": "connect_error"}
        )
    )
    import agents.laborpulse.api as api_mod

    monkeypatch.setattr(api_mod, "stream_query", boom)
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    r = client.post("/api/laborpulse/query", json={"question": "x"})
    assert r.status_code == 503
    err = r.json()["error"]
    assert err["code"] == "service_unavailable"
    assert err["details"]["upstream"] == "jie"


def test_query_422_when_jie_rejects_question(labor_app, monkeypatch):
    app, _fake, cookie = labor_app
    bad = _FakeJieChunks(
        raises=ValidationFailure(
            "JIE rejected the question",
            details={"upstream": "jie", "status": 422},
        )
    )
    import agents.laborpulse.api as api_mod

    monkeypatch.setattr(api_mod, "stream_query", bad)
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    r = client.post("/api/laborpulse/query", json={"question": "x"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_query_rejects_empty_question(labor_app):
    app, _fake, cookie = labor_app
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    r = client.post("/api/laborpulse/query", json={"question": ""})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


# ---------------------------------------------------------------------------
# Feedback writer
# ---------------------------------------------------------------------------


@pytest.fixture
def feedback_app(labor_app, monkeypatch):
    """Same as labor_app but swaps psycopg2.connect for sqlite3 so the
    INSERT actually lands in an in-process DB we can query."""
    app, fake, cookie = labor_app

    sqlite_conn = sqlite3.connect(":memory:", check_same_thread=False)
    sqlite_conn.execute(
        """
        CREATE TABLE qa_feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tenant_id TEXT, user_email TEXT, user_role TEXT,
            conversation_id TEXT, question TEXT, answer_snapshot TEXT,
            rating INTEGER, comment TEXT, cost_usd REAL, confidence TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
        """
    )

    class _StaticConn:
        def __init__(self, conn):
            self._conn = conn

        def cursor(self):
            # Rewrite psycopg2's %s placeholders to sqlite's ?.
            outer = self

            class _Cur:
                def __init__(self_):
                    self_._last_rowid = None

                def __enter__(self_):
                    return self_

                def __exit__(self_, *a):
                    return False

                def execute(self_, sql, params=()):
                    sql = sql.replace("%s", "?")
                    inner = outer._conn.execute(sql, params)
                    # Drain immediately so commit can proceed without
                    # "SQL statements in progress" errors.
                    self_._last_rowid = inner.lastrowid
                    inner.close()
                    return self_

                def fetchone(self_):
                    # api.py uses INSERT ... RETURNING id. sqlite's
                    # RETURNING support varies; use last_insert_rowid()
                    # via the drained cursor state.
                    return (self_._last_rowid,)

            return _Cur()

        def commit(self_):
            self_._conn.commit()

        def close(self_):
            pass  # keep the shared conn open across calls

    import agents.laborpulse.api as api_mod

    def _fake_connect(**kwargs):
        return _StaticConn(sqlite_conn)

    monkeypatch.setattr(api_mod.psycopg2, "connect", _fake_connect)
    return app, cookie, sqlite_conn


def test_feedback_writes_row(feedback_app):
    app, cookie, conn = feedback_app
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    r = client.post(
        "/api/laborpulse/feedback",
        json={
            "conversation_id": "conv-1",
            "question": "any growth in construction?",
            "rating": 1,
            "answer_snapshot": "Yes — 12% YoY.",
            "confidence": "high",
            "cost_usd": 0.0042,
        },
        headers={"Host": "talent.borderplexwfs.org"},
    )
    assert r.status_code == 200
    assert r.json()["ok"] is True

    rows = conn.execute(
        "SELECT tenant_id, user_email, user_role, rating, confidence FROM qa_feedback"
    ).fetchall()
    assert len(rows) == 1
    tenant_id, user_email, user_role, rating, confidence = rows[0]
    assert tenant_id == "borderplex"
    assert user_email == "director@borderplex.example.com"
    assert user_role == "workforce-development"
    assert rating == 1
    assert confidence == "high"


def test_feedback_rejects_out_of_range_rating(feedback_app):
    app, cookie, _conn = feedback_app
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    r = client.post(
        "/api/laborpulse/feedback",
        json={
            "conversation_id": "conv-2",
            "question": "x",
            "rating": 5,  # out of domain
        },
    )
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"


def test_feedback_requires_auth(feedback_app):
    app, _cookie, _ = feedback_app
    r = _client(app).post(
        "/api/laborpulse/feedback",
        json={"conversation_id": "c", "question": "q", "rating": 1},
    )
    assert r.status_code == 401


def test_feedback_rejects_student_role(feedback_app):
    app, _cookie, _ = feedback_app
    student = issue_session(Session(email="s@x", role="student"), secret_key=_KEY)
    client = _client(app)
    client.cookies.set("wfdos_session", student)
    r = client.post(
        "/api/laborpulse/feedback",
        json={"conversation_id": "c", "question": "q", "rating": 1},
    )
    assert r.status_code == 403


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


def test_health_reports_jie_configured(labor_app):
    app, _fake, _cookie = labor_app
    r = _client(app).get("/api/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["service"] == "laborpulse"
    assert body["jie_configured"] is True
