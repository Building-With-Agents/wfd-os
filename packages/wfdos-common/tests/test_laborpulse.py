"""Tests for agents/laborpulse/ — JIE proxy + mock mode + qa_feedback writer.

All tests mock the JIE HTTP client so no real JIE traffic goes out; the
feedback writer uses a SQLite-in-memory connection standing in for
psycopg2.
"""

from __future__ import annotations

import sqlite3
from typing import Any

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
    """Safe-empty default — stack boots without JIE creds; the endpoint
    switches to mock mode instead of 503."""
    from wfdos_common.config.settings import JieSettings

    s = JieSettings()
    assert isinstance(s.base_url, str)


# ---------------------------------------------------------------------------
# qa_feedback schema structure
# ---------------------------------------------------------------------------


def test_qa_feedback_schema_has_required_columns():
    """The committed schema must declare the columns the LaborPulse
    feedback writer inserts into."""
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
    assert "CHECK (rating IN (-1, 1))" in sql_text
    assert "ix_qa_feedback_tenant_created" in sql_text


# ---------------------------------------------------------------------------
# JIE client event folding — unit tests on _fold_frame_into
# ---------------------------------------------------------------------------


def _fresh_acc() -> dict[str, Any]:
    from agents.laborpulse.client import _new_result

    return _new_result()


def test_fold_frame_appends_answer_chunks():
    from agents.laborpulse.client import _fold_frame_into

    acc = _fresh_acc()
    _fold_frame_into(acc, 'event: answer\ndata: {"text": "Manufacturing "}')
    _fold_frame_into(acc, 'event: answer\ndata: {"text": "and healthcare."}')
    assert acc["answer"] == "Manufacturing and healthcare."


def test_fold_frame_handles_plain_text_answer_chunks():
    """JIE sometimes emits bare tokens without JSON wrapping."""
    from agents.laborpulse.client import _fold_frame_into

    acc = _fresh_acc()
    _fold_frame_into(acc, "event: answer\ndata: raw text tokens")
    assert "raw text tokens" in acc["answer"]


def test_fold_frame_collects_evidence_items():
    from agents.laborpulse.client import _fold_frame_into

    acc = _fresh_acc()
    _fold_frame_into(acc, 'event: evidence\ndata: {"source": "jobs_2024", "text": "..."}')
    _fold_frame_into(acc, 'event: evidence\ndata: {"items": [{"source": "b"}, {"source": "c"}]}')
    assert len(acc["evidence"]) == 3
    assert acc["evidence"][0]["source"] == "jobs_2024"
    assert acc["evidence"][2]["source"] == "c"


def test_fold_frame_sets_confidence_and_followups():
    from agents.laborpulse.client import _fold_frame_into

    acc = _fresh_acc()
    _fold_frame_into(acc, 'event: confidence\ndata: {"level": "high"}')
    _fold_frame_into(acc, 'event: followup\ndata: {"question": "What about wages?"}')
    _fold_frame_into(
        acc, 'event: follow_up\ndata: {"questions": ["Which employers?", "What sectors?"]}'
    )
    assert acc["confidence"] == "high"
    assert acc["follow_up_questions"] == [
        "What about wages?",
        "Which employers?",
        "What sectors?",
    ]


def test_fold_frame_captures_conversation_id_and_cost_on_done():
    from agents.laborpulse.client import _fold_frame_into

    acc = _fresh_acc()
    _fold_frame_into(
        acc,
        'event: done\ndata: {"conversation_id": "conv-abc", "cost_usd": 0.0042}',
    )
    assert acc["conversation_id"] == "conv-abc"
    assert acc["cost_usd"] == 0.0042


def test_fold_frame_ignores_unknown_event_types():
    """Keeps wfd-os decoupled from JIE's event vocabulary evolution."""
    from agents.laborpulse.client import _fold_frame_into

    acc = _fresh_acc()
    _fold_frame_into(acc, 'event: brand_new_event\ndata: {"text": "surprise"}')
    assert acc["answer"] == ""
    assert acc["evidence"] == []


# ---------------------------------------------------------------------------
# API endpoint tests — mock the jie_query callable
# ---------------------------------------------------------------------------


class _FakeJieQuery:
    """Drop-in replacement for agents.laborpulse.api.jie_query. Captures
    the kwargs each call was made with; either returns a canned dict or
    raises a preset exception."""

    def __init__(
        self,
        *,
        result: dict[str, Any] | None = None,
        raises: Exception | None = None,
    ) -> None:
        self.result = result or {
            "conversation_id": "conv-1",
            "answer": "Manufacturing and healthcare led postings growth in Q1.",
            "evidence": [{"source": "jobs_2024"}],
            "confidence": "high",
            "follow_up_questions": ["Which employers drove that?"],
            "cost_usd": 0.012,
            "sql_generated": "SELECT ... FROM jobs_2024 WHERE ...",
        }
        self.raises = raises
        self.calls: list[dict[str, Any]] = []

    async def __call__(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        if self.raises is not None:
            raise self.raises
        return self.result


@pytest.fixture
def labor_app(monkeypatch):
    """Build the LaborPulse app with env + settings patched to a known
    state and `jie_query` replaced by _FakeJieQuery. The JIE base_url is
    populated so the endpoint runs the real-JIE branch (mock-mode tests
    unset it explicitly via their own monkeypatch)."""
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
    # Force llm_gated to pass — treat Anthropic as configured.
    monkeypatch.setattr(settings.llm, "anthropic_api_key", "fake")
    monkeypatch.setattr(settings.azure_openai, "key", "")
    monkeypatch.setattr(settings.azure_openai, "endpoint", "")
    monkeypatch.setattr(settings.llm, "gemini_api_key", "")

    fake = _FakeJieQuery()
    import agents.laborpulse.api as api_mod

    monkeypatch.setattr(api_mod, "jie_query", fake)

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


def test_query_rejects_student_role(labor_app):
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
    body = r.json()
    assert body["conversation_id"] == "conv-1"
    assert "Manufacturing" in body["answer"]
    assert body["confidence"] == "high"
    assert body["follow_up_questions"] == ["Which employers drove that?"]
    assert body["cost_usd"] == 0.012


def test_query_response_matches_pydantic_shape(labor_app):
    """Response model declares explicit keys; make sure none are dropped
    or renamed."""
    app, _fake, cookie = labor_app
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    r = client.post("/api/laborpulse/query", json={"question": "q"})
    body = r.json()
    assert set(body.keys()) == {
        "conversation_id",
        "answer",
        "evidence",
        "confidence",
        "follow_up_questions",
        "cost_usd",
        "sql_generated",
    }


def test_query_forwards_tenant_id_from_host(labor_app):
    app, fake, cookie = labor_app
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    client.post(
        "/api/laborpulse/query",
        json={"question": "test"},
        headers={"Host": "talent.borderplexwfs.org"},
    )
    assert fake.calls, "jie_query was not invoked"
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
    boom = _FakeJieQuery(
        raises=ServiceUnavailableError(
            "JIE unreachable",
            details={"upstream": "jie", "reason": "connect_error"},
        )
    )
    import agents.laborpulse.api as api_mod

    monkeypatch.setattr(api_mod, "jie_query", boom)
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    r = client.post("/api/laborpulse/query", json={"question": "x"})
    assert r.status_code == 503
    err = r.json()["error"]
    assert err["code"] == "service_unavailable"
    assert err["details"]["upstream"] == "jie"


def test_query_422_when_jie_rejects_question(labor_app, monkeypatch):
    app, _fake, cookie = labor_app
    bad = _FakeJieQuery(
        raises=ValidationFailure(
            "JIE rejected the question",
            details={"upstream": "jie", "status": 422},
        )
    )
    import agents.laborpulse.api as api_mod

    monkeypatch.setattr(api_mod, "jie_query", bad)
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
# Mock-mode tests — when settings.jie.base_url == ""
# ---------------------------------------------------------------------------


def test_query_returns_mock_when_jie_base_url_empty(labor_app, monkeypatch):
    """With JIE_BASE_URL empty, the endpoint returns a canned
    Borderplex-flavored answer tagged as mock."""
    app, fake, cookie = labor_app
    from wfdos_common.config import settings
    import agents.laborpulse.api as api_mod

    monkeypatch.setattr(settings.jie, "base_url", "")

    # Patch asyncio.sleep in the api module to a no-op so the test is fast.
    async def _no_sleep(_seconds):
        return None

    monkeypatch.setattr(api_mod.asyncio, "sleep", _no_sleep)

    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    r = client.post("/api/laborpulse/query", json={"question": "top sectors?"})
    assert r.status_code == 200
    body = r.json()
    assert body["conversation_id"].startswith("mock-")
    assert body["confidence"] == "mock"
    assert "[MOCK]" in body["answer"]
    assert len(body["evidence"]) >= 1
    assert len(body["follow_up_questions"]) >= 1
    # The user's question gets echoed into the mock answer so a demo feels
    # responsive rather than canned.
    assert "top sectors?" in body["answer"]
    # The real jie_query must NOT have been invoked.
    assert fake.calls == []


def test_query_mock_sleeps_between_8_and_12_seconds(labor_app, monkeypatch):
    """The mock path must feel like JIE synthesis — 8-12s latency."""
    app, _fake, cookie = labor_app
    from wfdos_common.config import settings
    import agents.laborpulse.api as api_mod

    monkeypatch.setattr(settings.jie, "base_url", "")

    captured: list[float] = []

    async def _recording_sleep(seconds):
        captured.append(seconds)

    monkeypatch.setattr(api_mod.asyncio, "sleep", _recording_sleep)

    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    r = client.post("/api/laborpulse/query", json={"question": "x"})
    assert r.status_code == 200
    assert len(captured) == 1
    # Inclusive on 8.0, exclusive on 12.0 per random.uniform semantics,
    # but we check a loose range so an off-by-epsilon isn't flaky.
    assert 8.0 <= captured[0] <= 12.0, (
        f"mock sleep out of range [8, 12]: {captured[0]}"
    )


def test_health_reports_jie_not_configured_when_base_url_empty(labor_app, monkeypatch):
    """/api/health is the production deploy-check signal for mock mode."""
    app, _fake, _cookie = labor_app
    from wfdos_common.config import settings

    monkeypatch.setattr(settings.jie, "base_url", "")

    r = _client(app).get("/api/health")
    assert r.status_code == 200
    assert r.json()["jie_configured"] is False


# ---------------------------------------------------------------------------
# Feedback writer
# ---------------------------------------------------------------------------


@pytest.fixture
def feedback_app(labor_app, monkeypatch):
    """Same as labor_app but swaps psycopg2.connect for sqlite3 so the
    INSERT actually lands in an in-process DB we can query."""
    app, _fake, cookie = labor_app

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
                    self_._last_rowid = inner.lastrowid
                    inner.close()
                    return self_

                def fetchone(self_):
                    return (self_._last_rowid,)

            return _Cur()

        def commit(self_):
            self_._conn.commit()

        def close(self_):
            pass

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


def test_feedback_accepts_mock_conversation_id(feedback_app):
    """Thumbs-up/down on a mock-mode answer must write normally. The
    `conversation_id` starts with `mock-` but is otherwise treated like
    any other id."""
    app, cookie, conn = feedback_app
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    r = client.post(
        "/api/laborpulse/feedback",
        json={
            "conversation_id": "mock-11111111-2222-3333-4444-555555555555",
            "question": "mock answer — is it useful?",
            "rating": 1,
            "confidence": "mock",
        },
    )
    assert r.status_code == 200
    rows = conn.execute(
        "SELECT conversation_id, confidence FROM qa_feedback"
    ).fetchall()
    assert rows[-1][0].startswith("mock-")
    assert rows[-1][1] == "mock"


def test_feedback_rejects_out_of_range_rating(feedback_app):
    app, cookie, _conn = feedback_app
    client = _client(app)
    client.cookies.set("wfdos_session", cookie)
    r = client.post(
        "/api/laborpulse/feedback",
        json={"conversation_id": "conv-2", "question": "x", "rating": 5},
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
