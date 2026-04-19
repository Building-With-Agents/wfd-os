"""Magic-link + session token sign/verify using itsdangerous.

The magic-link token carries an email address + a nonce + an issued-at
timestamp, signed with `settings.auth.secret_key`. `verify_magic_link`
returns the email if the token is valid and unexpired, or raises
`TokenError` subclasses for bad/expired/malformed input.

Session tokens carry email + role + issued-at, signed with the same key.
They live in an HttpOnly cookie set after a successful `/verify` round-trip.

Rotating `settings.auth.secret_key` invalidates every outstanding magic
link AND every session cookie — the intended response to a secret leak.
"""

from __future__ import annotations

import secrets
from dataclasses import dataclass
from typing import Any

from itsdangerous import BadSignature, SignatureExpired, TimestampSigner
from itsdangerous.serializer import Serializer


class TokenError(Exception):
    """Base for all token-validation failures."""


class TokenExpiredError(TokenError):
    """Token was valid at issue but has exceeded its TTL."""


class TokenInvalidError(TokenError):
    """Signature mismatch, malformed payload, or unknown purpose."""


# Purpose strings embedded in every token so a stolen magic-link can't be
# used as a session cookie (or vice versa). They're part of the signing
# salt, not just the payload.
_MAGIC_LINK_SALT = "wfdos-magic-link"
_SESSION_SALT = "wfdos-session"


def _make_serializer(secret_key: str, salt: str) -> Serializer:
    return Serializer(secret_key=secret_key, salt=salt)


# ---------------------------------------------------------------------------
# Magic-link tokens
# ---------------------------------------------------------------------------


def issue_magic_link(email: str, *, secret_key: str) -> str:
    """Return a signed magic-link token bound to this email.

    The payload is `{"email": ..., "nonce": ...}`. The nonce is a random
    16-byte value so two tokens issued to the same email within the same
    second are still distinguishable (useful for testing and for future
    revocation-list support).
    """
    serializer = _make_serializer(secret_key, _MAGIC_LINK_SALT)
    payload: dict[str, Any] = {
        "email": email,
        "nonce": secrets.token_urlsafe(16),
    }
    # itsdangerous.Serializer.dumps signs with HMAC-SHA1 over the JSON payload.
    token = serializer.dumps(payload)
    # Wrap with TimestampSigner so we can enforce max_age on verify. The
    # outer layer signs the inner token, giving us cryptographic TTL.
    ts_signer = TimestampSigner(secret_key=secret_key, salt=_MAGIC_LINK_SALT + ":ts")
    return ts_signer.sign(token.encode()).decode()


def verify_magic_link(token: str, *, secret_key: str, max_age_seconds: int) -> str:
    """Validate `token`; return the email it was issued for. Raises
    `TokenExpiredError` or `TokenInvalidError` on failure.
    """
    ts_signer = TimestampSigner(secret_key=secret_key, salt=_MAGIC_LINK_SALT + ":ts")
    try:
        inner = ts_signer.unsign(token.encode(), max_age=max_age_seconds)
    except SignatureExpired as e:
        raise TokenExpiredError("magic link has expired") from e
    except BadSignature as e:
        raise TokenInvalidError("magic link signature invalid") from e

    serializer = _make_serializer(secret_key, _MAGIC_LINK_SALT)
    try:
        payload = serializer.loads(inner.decode())
    except BadSignature as e:
        raise TokenInvalidError("magic link payload signature invalid") from e

    if not isinstance(payload, dict) or "email" not in payload:
        raise TokenInvalidError("magic link payload malformed")
    return payload["email"]


# ---------------------------------------------------------------------------
# Session tokens
# ---------------------------------------------------------------------------


@dataclass
class Session:
    """Successfully-verified session state. Attached to request.state.user
    by SessionMiddleware so downstream handlers can use it without a DB call.
    """

    email: str
    role: str  # "student" | "staff" | "admin"
    tenant_id: str | None = None


def issue_session(session: Session, *, secret_key: str) -> str:
    """Return a signed session token (stored in the session cookie)."""
    serializer = _make_serializer(secret_key, _SESSION_SALT)
    payload: dict[str, Any] = {
        "email": session.email,
        "role": session.role,
        "tenant_id": session.tenant_id,
    }
    token = serializer.dumps(payload)
    ts_signer = TimestampSigner(secret_key=secret_key, salt=_SESSION_SALT + ":ts")
    return ts_signer.sign(token.encode()).decode()


def verify_session(token: str, *, secret_key: str, max_age_seconds: int) -> Session:
    """Return the Session the cookie encodes, or raise `TokenError`."""
    ts_signer = TimestampSigner(secret_key=secret_key, salt=_SESSION_SALT + ":ts")
    try:
        inner = ts_signer.unsign(token.encode(), max_age=max_age_seconds)
    except SignatureExpired as e:
        raise TokenExpiredError("session has expired") from e
    except BadSignature as e:
        raise TokenInvalidError("session signature invalid") from e

    serializer = _make_serializer(secret_key, _SESSION_SALT)
    try:
        payload = serializer.loads(inner.decode())
    except BadSignature as e:
        raise TokenInvalidError("session payload signature invalid") from e

    if not isinstance(payload, dict) or "email" not in payload or "role" not in payload:
        raise TokenInvalidError("session payload malformed")
    return Session(
        email=payload["email"],
        role=payload["role"],
        tenant_id=payload.get("tenant_id"),
    )


__all__ = [
    "Session",
    "TokenError",
    "TokenExpiredError",
    "TokenInvalidError",
    "issue_magic_link",
    "verify_magic_link",
    "issue_session",
    "verify_session",
]
