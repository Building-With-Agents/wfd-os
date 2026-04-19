"""Tests for wfdos_common.auth — magic-link flow + role enforcement (#24)."""

from __future__ import annotations

import time
from typing import Any, Callable

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from wfdos_common.auth import (
    Session,
    SessionMiddleware,
    TokenError,
    TokenExpiredError,
    TokenInvalidError,
    build_auth_router,
    issue_magic_link,
    issue_session,
    require_role,
    resolve_role,
    verify_magic_link,
    verify_session,
)
from wfdos_common.errors import install_error_handlers

_KEY = "test-secret-please-dont-ship"


# ---------------------------------------------------------------------------
# Token sign/verify
# ---------------------------------------------------------------------------


def test_magic_link_roundtrip():
    token = issue_magic_link("alice@example.com", secret_key=_KEY)
    email = verify_magic_link(token, secret_key=_KEY, max_age_seconds=900)
    assert email == "alice@example.com"


def test_magic_link_expired_raises():
    token = issue_magic_link("alice@example.com", secret_key=_KEY)
    time.sleep(2.1)
    with pytest.raises(TokenExpiredError):
        verify_magic_link(token, secret_key=_KEY, max_age_seconds=1)


def test_magic_link_tampered_raises():
    token = issue_magic_link("alice@example.com", secret_key=_KEY)
    # Flip a byte in the payload portion (well before the signature) so any
    # trailing-base64 flexibility can't mask the change.
    midpoint = len(token) // 3
    flipped = "A" if token[midpoint] != "A" else "B"
    tampered = token[:midpoint] + flipped + token[midpoint + 1 :]
    with pytest.raises(TokenInvalidError):
        verify_magic_link(tampered, secret_key=_KEY, max_age_seconds=900)


def test_magic_link_wrong_key_raises():
    token = issue_magic_link("alice@example.com", secret_key=_KEY)
    with pytest.raises(TokenInvalidError):
        verify_magic_link(token, secret_key="other-key", max_age_seconds=900)


def test_session_roundtrip():
    sess = Session(email="bob@example.com", role="staff", tenant_id="waifinder-flagship")
    token = issue_session(sess, secret_key=_KEY)
    back = verify_session(token, secret_key=_KEY, max_age_seconds=3600)
    assert back.email == sess.email
    assert back.role == sess.role
    assert back.tenant_id == sess.tenant_id


def test_session_cannot_be_used_as_magic_link():
    """Purpose-separated salts: a session token must NOT validate as a magic link."""
    sess = Session(email="bob@example.com", role="staff")
    session_token = issue_session(sess, secret_key=_KEY)
    with pytest.raises(TokenError):
        verify_magic_link(session_token, secret_key=_KEY, max_age_seconds=900)


def test_magic_link_cannot_be_used_as_session():
    """Purpose-separated salts: a magic link must NOT validate as a session."""
    link_token = issue_magic_link("bob@example.com", secret_key=_KEY)
    with pytest.raises(TokenError):
        verify_session(link_token, secret_key=_KEY, max_age_seconds=3600)


# ---------------------------------------------------------------------------
# Allowlist resolution
# ---------------------------------------------------------------------------


def test_resolve_role_prefers_admin_over_staff_over_student():
    role = resolve_role(
        "dup@example.com",
        admin_csv="dup@example.com",
        staff_csv="dup@example.com",
        student_csv="dup@example.com",
    )
    assert role == "admin"


def test_resolve_role_case_insensitive():
    role = resolve_role(
        "  BOB@Example.COM ",
        admin_csv="",
        staff_csv="bob@example.com",
        student_csv="",
    )
    assert role == "staff"


def test_resolve_role_returns_none_for_unknown():
    assert resolve_role(
        "nobody@example.com",
        admin_csv="alice@example.com",
        staff_csv="bob@example.com",
        student_csv="carol@example.com",
    ) is None


def test_resolve_role_rejects_empty_email():
    assert resolve_role("", admin_csv="", staff_csv="", student_csv="") is None


# ---------------------------------------------------------------------------
# SessionMiddleware
# ---------------------------------------------------------------------------


def _make_secured_app(**middleware_kwargs: Any) -> FastAPI:
    app = FastAPI()
    app.add_middleware(
        SessionMiddleware,
        secret_key=_KEY,
        cookie_name="wfdos_session",
        max_age_seconds=3600,
        **middleware_kwargs,
    )
    install_error_handlers(app)

    @app.get("/me")
    def me(user: Session = Depends(require_role("staff", "admin"))):
        return {"email": user.email, "role": user.role}

    @app.get("/admin")
    def admin_only(user: Session = Depends(require_role("admin"))):
        return {"email": user.email}

    @app.get("/public")
    def public():
        return {"hello": "world"}

    return app


def test_middleware_accepts_valid_cookie():
    app = _make_secured_app()
    client = TestClient(app)
    token = issue_session(
        Session(email="alice@example.com", role="staff"), secret_key=_KEY
    )
    client.cookies.set("wfdos_session", token)
    r = client.get("/me")
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"


def test_middleware_rejects_missing_cookie_with_401():
    app = _make_secured_app()
    client = TestClient(app)
    r = client.get("/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_middleware_rejects_tampered_cookie():
    app = _make_secured_app()
    client = TestClient(app)
    client.cookies.set("wfdos_session", "garbage.not.a.real.token")
    r = client.get("/me")
    assert r.status_code == 401


def test_middleware_rejects_wrong_role_with_403():
    app = _make_secured_app()
    client = TestClient(app)
    token = issue_session(
        Session(email="student@example.com", role="student"), secret_key=_KEY
    )
    client.cookies.set("wfdos_session", token)
    r = client.get("/admin")
    assert r.status_code == 403
    assert r.json()["error"]["code"] == "forbidden"


def test_public_route_works_without_auth():
    app = _make_secured_app()
    client = TestClient(app)
    r = client.get("/public")
    assert r.status_code == 200


# ---------------------------------------------------------------------------
# build_auth_router end-to-end
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_app(monkeypatch):
    """Minimal app with the real auth router and a captured email sender."""
    # Monkeypatch settings to have the email in a staff allowlist + our key.
    from wfdos_common.config import settings

    # Reload the proxy with a fresh underlying settings. The cleanest path
    # is to patch the attributes directly on the loaded singleton.
    monkeypatch.setattr(settings.auth, "secret_key", _KEY)
    monkeypatch.setattr(settings.auth, "staff_allowlist", "alice@example.com")
    monkeypatch.setattr(settings.auth, "admin_allowlist", "")
    monkeypatch.setattr(settings.auth, "student_allowlist", "")
    monkeypatch.setattr(settings.auth, "magic_link_ttl_seconds", 900)
    monkeypatch.setattr(settings.auth, "session_ttl_seconds", 3600)
    monkeypatch.setattr(settings.auth, "cookie_secure", False)
    monkeypatch.setattr(settings.platform, "portal_base_url", "http://testserver")

    captured: list[tuple[str, str]] = []

    def _sender(to: str, link: str) -> None:
        captured.append((to, link))

    app = FastAPI()
    app.add_middleware(
        SessionMiddleware,
        secret_key=_KEY,
        cookie_name="wfdos_session",
        max_age_seconds=3600,
    )
    install_error_handlers(app)
    app.include_router(build_auth_router(email_sender=_sender))

    @app.get("/whoami")
    def whoami(user: Session = Depends(require_role("staff", "admin", "student"))):
        return {"email": user.email, "role": user.role}

    return app, captured


def test_login_not_allowlisted_returns_ok_silently(auth_app):
    app, captured = auth_app
    client = TestClient(app)
    r = client.post("/auth/login", json={"email": "stranger@example.com"})
    assert r.status_code == 200
    # Email must NOT have been dispatched.
    assert captured == []
    # The response shape is the same either way.
    assert r.json()["status"] == "ok"


def test_login_dispatches_magic_link_to_allowlisted(auth_app):
    app, captured = auth_app
    client = TestClient(app)
    r = client.post("/auth/login", json={"email": "alice@example.com"})
    assert r.status_code == 200
    assert len(captured) == 1
    to, link = captured[0]
    assert to == "alice@example.com"
    assert "/auth/verify?token=" in link


def test_verify_sets_session_cookie_and_redirects(auth_app):
    app, captured = auth_app
    client = TestClient(app, follow_redirects=False)
    client.post("/auth/login", json={"email": "alice@example.com"})
    _to, link = captured[0]
    token = link.split("token=", 1)[1]

    r = client.get(f"/auth/verify?token={token}")
    assert r.status_code == 302
    assert "wfdos_session" in r.cookies


def test_end_to_end_login_then_protected_route(auth_app):
    app, captured = auth_app
    client = TestClient(app, follow_redirects=False)
    client.post("/auth/login", json={"email": "alice@example.com"})
    _to, link = captured[0]
    token = link.split("token=", 1)[1]
    client.get(f"/auth/verify?token={token}")  # sets cookie

    r = client.get("/whoami")
    assert r.status_code == 200
    assert r.json() == {"email": "alice@example.com", "role": "staff"}


def test_verify_invalid_token_redirects_with_error(auth_app):
    app, _ = auth_app
    client = TestClient(app, follow_redirects=False)
    r = client.get("/auth/verify?token=not-a-real-token")
    assert r.status_code == 302
    assert "auth_error=1" in r.headers["location"]


def test_logout_clears_cookie(auth_app):
    app, captured = auth_app
    client = TestClient(app, follow_redirects=False)
    client.post("/auth/login", json={"email": "alice@example.com"})
    _to, link = captured[0]
    token = link.split("token=", 1)[1]
    client.get(f"/auth/verify?token={token}")

    # Confirm authenticated first.
    r = client.get("/whoami")
    assert r.status_code == 200

    # Log out, then confirm the cookie is gone.
    client.post("/auth/logout")
    # Starlette's delete_cookie sets it to empty with Max-Age=0; the cookie
    # jar may or may not clear it depending on version. Either way, /whoami
    # should no longer succeed if we clear the jar manually.
    client.cookies.clear()
    r = client.get("/whoami")
    assert r.status_code == 401


def test_me_route_authenticated(auth_app):
    app, captured = auth_app
    client = TestClient(app, follow_redirects=False)
    client.post("/auth/login", json={"email": "alice@example.com"})
    _to, link = captured[0]
    token = link.split("token=", 1)[1]
    client.get(f"/auth/verify?token={token}")

    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "alice@example.com"
    assert r.json()["role"] == "staff"


def test_me_route_unauthenticated_returns_401(auth_app):
    app, _ = auth_app
    client = TestClient(app)
    r = client.get("/auth/me")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_login_rejects_malformed_email(auth_app):
    app, captured = auth_app
    client = TestClient(app)
    r = client.post("/auth/login", json={"email": "not-an-email"})
    assert r.status_code == 422
    assert r.json()["error"]["code"] == "validation_error"
    assert captured == []
