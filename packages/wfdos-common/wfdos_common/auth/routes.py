"""Mountable `/login` + `/verify` router for any FastAPI service.

Usage on a service:

    from fastapi import FastAPI
    from wfdos_common.auth import build_auth_router

    app = FastAPI()
    app.include_router(build_auth_router())

This gives the service:

  POST /auth/login        {"email": ...}   → sends a magic link; always 200
  GET  /auth/verify?token=...               → sets cookie, redirects home
  POST /auth/logout                         → clears cookie
  GET  /auth/me                             → {"email", "role"} or 401

Factory-based so each service can configure its own post-verify redirect
target (the Next.js portal lives at localhost:3000, standalone services
may redirect elsewhere).
"""

from __future__ import annotations

from typing import Callable, Optional

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel, EmailStr
from starlette.responses import JSONResponse, RedirectResponse

from wfdos_common.auth.allowlist import resolve_role
from wfdos_common.auth.dependencies import current_user
from wfdos_common.auth.tokens import (
    Session,
    TokenError,
    issue_magic_link,
    issue_session,
    verify_magic_link,
)
from wfdos_common.errors import UnauthorizedError
from wfdos_common.logging import get_logger

log = get_logger(__name__)


class LoginBody(BaseModel):
    email: EmailStr


# Callable type used by build_auth_router to dispatch the magic-link email.
# Services can inject a mock in tests.
EmailSender = Callable[[str, str], None]


def _default_email_sender(to: str, link: str) -> None:
    """Default sender uses wfdos_common.email.send_email over Microsoft Graph.

    Swapped out via `email_sender=` in tests so no real email goes out.
    """
    from wfdos_common.email import send_email

    subject = "Your Waifinder sign-in link"
    html = (
        f"<p>Click the link below to sign in to the Waifinder platform.</p>"
        f'<p><a href="{link}">Sign in</a></p>'
        f"<p>This link expires in 15 minutes. If you didn't request it, ignore this email.</p>"
    )
    send_email(to, subject, html, html=True)


def build_auth_router(
    *,
    prefix: str = "/auth",
    post_verify_redirect: str = "/",
    email_sender: Optional[EmailSender] = None,
) -> APIRouter:
    """Return an APIRouter with the four magic-link routes mounted.

    Services include it via `app.include_router(build_auth_router())`.
    """
    from wfdos_common.config import settings  # lazy import for test patching

    router = APIRouter(prefix=prefix, tags=["auth"])
    sender = email_sender or _default_email_sender

    @router.post("/login")
    def login(body: LoginBody, request: Request):
        """Always returns 200 so unallowlisted emails can't be enumerated.

        If the email is allowlisted, a magic-link email is dispatched; if
        not, we log a warning but still return the same shape.
        """
        email = body.email.strip().lower()
        role = resolve_role(
            email,
            admin_csv=settings.auth.admin_allowlist,
            staff_csv=settings.auth.staff_allowlist,
            student_csv=settings.auth.student_allowlist,
            workforce_development_csv=settings.auth.workforce_development_allowlist,
        )
        if role is None:
            log.warning("auth.login.not_allowlisted", email=email)
            return {"status": "ok", "message": "If you're allowed in, a link is on the way."}

        token = issue_magic_link(email, secret_key=settings.auth.secret_key)
        base_url = settings.platform.portal_base_url.rstrip("/")
        link = f"{base_url}{prefix}/verify?token={token}"

        try:
            sender(email, link)
        except Exception:  # noqa: BLE001 — send_email already returns a dict, but be safe
            log.error("auth.login.email_send_failed", email=email, exc_info=True)
            # Still return ok so we don't leak whether email exists.

        log.info("auth.login.magic_link_issued", email=email, role=role)
        return {"status": "ok", "message": "If you're allowed in, a link is on the way."}

    @router.get("/verify")
    def verify(request: Request, token: str):
        """Validate `token`, set a session cookie, redirect to the portal.

        On invalid/expired token we redirect to the portal with `?auth_error=1`
        so the UI can show a friendly retry, rather than leaking details.
        """
        try:
            email = verify_magic_link(
                token,
                secret_key=settings.auth.secret_key,
                max_age_seconds=settings.auth.magic_link_ttl_seconds,
            )
        except TokenError:
            log.info("auth.verify.invalid_token")
            return RedirectResponse(
                url=f"{settings.platform.portal_base_url.rstrip('/')}/?auth_error=1",
                status_code=302,
            )

        role = resolve_role(
            email,
            admin_csv=settings.auth.admin_allowlist,
            staff_csv=settings.auth.staff_allowlist,
            student_csv=settings.auth.student_allowlist,
            workforce_development_csv=settings.auth.workforce_development_allowlist,
        )
        if role is None:
            # Allowlist changed between login + verify — treat as invalid.
            log.warning("auth.verify.email_no_longer_allowlisted", email=email)
            return RedirectResponse(
                url=f"{settings.platform.portal_base_url.rstrip('/')}/?auth_error=1",
                status_code=302,
            )

        session = Session(email=email, role=role)
        session_token = issue_session(session, secret_key=settings.auth.secret_key)

        redirect_url = post_verify_redirect
        if not redirect_url.startswith("http"):
            redirect_url = f"{settings.platform.portal_base_url.rstrip('/')}{redirect_url}"

        response = RedirectResponse(url=redirect_url, status_code=302)
        response.set_cookie(
            key=settings.auth.cookie_name,
            value=session_token,
            max_age=settings.auth.session_ttl_seconds,
            httponly=True,
            secure=settings.auth.cookie_secure,
            samesite=settings.auth.cookie_samesite,
        )
        log.info("auth.verify.session_established", email=email, role=role)
        return response

    @router.post("/logout")
    def logout():
        response = JSONResponse(content={"status": "ok"})
        response.delete_cookie(key=settings.auth.cookie_name)
        return response

    @router.get("/me")
    def me(user: Session | None = Depends(current_user)):
        if user is None:
            raise UnauthorizedError("authentication required")
        return {"email": user.email, "role": user.role, "tenant_id": user.tenant_id}

    return router


__all__ = ["LoginBody", "build_auth_router"]
