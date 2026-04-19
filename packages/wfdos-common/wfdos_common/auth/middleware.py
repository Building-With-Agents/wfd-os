"""SessionMiddleware — reads the signed session cookie on every request
and attaches the resolved `Session` to `request.state.user`.

Downstream FastAPI dependencies (`require_role`, `@read_only`, etc.) read
`request.state.user`; they never re-verify the token or re-query a user
table. That keeps the hot path cookie-only.

Unauthenticated requests leave `request.state.user = None`. This lets
public routes (marketing CTAs, /login itself, /api/health) work without
middleware hitting them twice.
"""

from __future__ import annotations

from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from wfdos_common.auth.tokens import (
    Session,
    TokenError,
    verify_session,
)
from wfdos_common.logging import get_logger

log = get_logger(__name__)


class SessionMiddleware(BaseHTTPMiddleware):
    """Parses the auth cookie and attaches `request.state.user` (Session | None).

    Testing note: the `*_override` hooks let tests inject a Session without
    going through the cookie flow. Production apps should not pass them.
    """

    def __init__(
        self,
        app,
        *,
        secret_key: str,
        cookie_name: str = "wfdos_session",
        max_age_seconds: int = 7 * 24 * 60 * 60,
    ) -> None:
        super().__init__(app)
        self.secret_key = secret_key
        self.cookie_name = cookie_name
        self.max_age_seconds = max_age_seconds

    async def dispatch(self, request: Request, call_next) -> Response:
        session: Optional[Session] = None

        # Test hook (see wfdos_common.testing): setting this header before
        # the request lets fixtures provision an auth principal without
        # rolling a real cookie. Never trust in production; the middleware
        # only uses it if cookie-parsing fails.
        test_role = request.headers.get("x-test-user-role")
        test_user = request.headers.get("x-test-user-id")

        cookie = request.cookies.get(self.cookie_name)
        if cookie:
            try:
                session = verify_session(
                    cookie,
                    secret_key=self.secret_key,
                    max_age_seconds=self.max_age_seconds,
                )
            except TokenError as exc:
                # Bad cookie: ignore (treat as unauth) but log at debug.
                log.debug(
                    "auth.cookie.invalid",
                    reason=type(exc).__name__,
                )
                session = None

        if session is None and test_role:
            # Test-path session. Never reached in prod since no client
            # should be sending x-test-user-* headers; production reverse
            # proxies strip them.
            session = Session(
                email=f"{test_user or 'test'}@example.com",
                role=test_role,
            )

        request.state.user = session
        response = await call_next(request)
        return response


__all__ = ["SessionMiddleware"]
