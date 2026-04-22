"""QuickBooks OAuth2 + sync routes.

Flow:
  1. User visits GET /qb/connect → we generate an authorize URL, store the
     CSRF state in-memory, and 307-redirect the browser to Intuit.
  2. User signs in at Intuit AS THE READ-ONLY QB USER (not admin), approves
     the scope, and is redirected back to GET /qb/callback?code=...&state=...&realmId=...
  3. We validate state, exchange the auth code for tokens, persist in
     qb_oauth_tokens, and render a plain success page.
  4. GET /qb/status shows current token state.
  5. POST /qb/sync runs the actual data sync against the stored tokens.

Note on the read-only enforcement: the OAuth token exchange here uses
module-level httpx.post() (in quickbooks/oauth.py), NOT QbClient's
_ReadOnlyHttpxClient. That's correct by design — the `client.py` guard is
scoped to the data plane (QB API queries). The OAuth token exchange is a
separate control-plane path that MUST issue a POST to Intuit's token
endpoint. The guard would mis-fire if it were global.
"""

from __future__ import annotations

import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from grant_compliance.audit.log import write_entry
from grant_compliance.config import get_settings
from grant_compliance.db.models import QbAccount, QbClass, QbOAuthToken, Transaction
from grant_compliance.db.session import get_db
from grant_compliance.quickbooks.client import QbClient
from grant_compliance.quickbooks.oauth import build_authorize_url, exchange_code
from grant_compliance.quickbooks.sync import (
    sync_accounts,
    sync_attachables,
    sync_classes,
    sync_transactions,
)

router = APIRouter(prefix="/qb", tags=["quickbooks"])


# ---------------------------------------------------------------------------
# In-memory CSRF state store. Keyed by state value → (created_at epoch).
# Purged entries older than 10 minutes on each access. Single-process only
# (fine for the local dev OAuth flow; would need Redis/DB in production).
# ---------------------------------------------------------------------------

_STATE_TTL_SECONDS = 10 * 60
_oauth_states: dict[str, float] = {}


def _issue_state() -> str:
    _purge_expired_states()
    state = secrets.token_urlsafe(24)
    _oauth_states[state] = time.time()
    return state


def _consume_state(state: str) -> bool:
    """Return True if state was present and not expired; removes it either way."""
    _purge_expired_states()
    created_at = _oauth_states.pop(state, None)
    if created_at is None:
        return False
    return (time.time() - created_at) <= _STATE_TTL_SECONDS


def _purge_expired_states() -> None:
    cutoff = time.time() - _STATE_TTL_SECONDS
    expired = [s for s, t in _oauth_states.items() if t < cutoff]
    for s in expired:
        _oauth_states.pop(s, None)


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/connect")
def qb_connect():
    """Kick off the OAuth flow. Redirects the browser to Intuit's authorize URL."""
    settings = get_settings()
    if not settings.qb_client_id or not settings.qb_client_secret:
        raise HTTPException(
            status_code=500,
            detail=(
                "QB_CLIENT_ID or QB_CLIENT_SECRET is not set. See README "
                "'Before Step 1' for the env chain setup."
            ),
        )
    state = _issue_state()
    url, _ = build_authorize_url(state=state)
    return RedirectResponse(url=url, status_code=307)


@router.get("/callback")
def qb_callback(
    code: str = Query(...),
    state: str = Query(...),
    realmId: str = Query(..., alias="realmId"),
    error: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """Intuit redirects here after authorization. Exchange code for tokens,
    persist, and render a plain success page."""
    if error:
        raise HTTPException(status_code=400, detail=f"Intuit returned error: {error}")

    if not _consume_state(state):
        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid or expired OAuth state. Go back to /qb/connect and "
                "start the flow again."
            ),
        )

    # Exchange the auth code for tokens.
    try:
        tokens = exchange_code(code)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token exchange failed: {e}")

    access_token = tokens["access_token"]
    refresh_token = tokens["refresh_token"]
    expires_in = int(tokens.get("expires_in", 3600))
    # Intuit's refresh token TTL is ~100 days. Use x_refresh_token_expires_in
    # when present; otherwise default to 100 days.
    refresh_expires_in = int(tokens.get("x_refresh_token_expires_in", 100 * 86400))

    now = datetime.now(timezone.utc)
    access_expires_at = now + timedelta(seconds=expires_in)
    refresh_expires_at = now + timedelta(seconds=refresh_expires_in)

    settings = get_settings()

    # Upsert by realm_id — if this realm was previously connected, update.
    existing = db.query(QbOAuthToken).filter(QbOAuthToken.realm_id == realmId).first()
    if existing:
        existing.access_token = access_token
        existing.refresh_token = refresh_token
        existing.access_token_expires_at = access_expires_at
        existing.refresh_token_expires_at = refresh_expires_at
        existing.environment = settings.qb_environment
        existing.authorized_by = settings.dev_user_email
        existing.updated_at = now
        existing.revoked_at = None
    else:
        db.add(
            QbOAuthToken(
                realm_id=realmId,
                access_token=access_token,
                refresh_token=refresh_token,
                access_token_expires_at=access_expires_at,
                refresh_token_expires_at=refresh_expires_at,
                environment=settings.qb_environment,
                authorized_by=settings.dev_user_email,
            )
        )
    db.commit()

    write_entry(
        db,
        actor=settings.dev_user_email,
        actor_kind="human",
        action="qb.oauth.authorized",
        target_type="qb_realm",
        target_id=realmId,
        outputs={
            "environment": settings.qb_environment,
            "access_expires_at": access_expires_at.isoformat(),
            "refresh_expires_at": refresh_expires_at.isoformat(),
        },
    )

    return HTMLResponse(
        f"""
        <!DOCTYPE html>
        <html><head><title>QB Connected</title></head>
        <body style="font-family: system-ui; max-width: 600px; margin: 40px auto; padding: 20px;">
            <h1>✓ QuickBooks connected</h1>
            <p><strong>Realm:</strong> <code>{realmId}</code></p>
            <p><strong>Environment:</strong> <code>{settings.qb_environment}</code></p>
            <p><strong>Access token expires:</strong> {access_expires_at.isoformat()}</p>
            <p><strong>Refresh token expires:</strong> {refresh_expires_at.isoformat()}</p>
            <p>You can close this tab. Next step: trigger a sync via
            <code>POST /qb/sync?since=YYYY-MM-DD</code> or via
            <a href="/qb/status">/qb/status</a> to see token state.</p>
        </body></html>
        """
    )


@router.get("/status")
def qb_status(db: Session = Depends(get_db)):
    """Show whether we're currently connected to any QB realm, and when tokens expire."""
    tokens = db.query(QbOAuthToken).filter(QbOAuthToken.revoked_at.is_(None)).all()
    settings = get_settings()
    return {
        "qb_environment": settings.qb_environment,
        "connected_realms": [
            {
                "realm_id": t.realm_id,
                "environment": t.environment,
                "authorized_by": t.authorized_by,
                "access_expires_at": t.access_token_expires_at.isoformat(),
                "refresh_expires_at": t.refresh_token_expires_at.isoformat(),
                "access_expired": t.access_token_expires_at < datetime.now(timezone.utc),
            }
            for t in tokens
        ],
    }


# ---------------------------------------------------------------------------
# Sync trigger
# ---------------------------------------------------------------------------


class SyncResponse(BaseModel):
    realm_id: str
    accounts_added: int
    classes_added: int
    transactions_added: int
    attachables_processed: int
    since: str


@router.post("/sync", response_model=SyncResponse)
def qb_sync(
    since: str = Query(..., description="ISO date string, e.g. 2024-04-01"),
    realm_id: Optional[str] = Query(None, description="If multiple realms, specify which"),
    db: Session = Depends(get_db),
):
    """Trigger a full sync: accounts, classes, transactions since `since`.

    Uses the currently-stored (non-revoked) OAuth token for the given realm
    (or the only realm if there's just one).
    """
    settings = get_settings()

    # Validate environment consistency — don't use a sandbox token against
    # production config, or vice versa.
    query = db.query(QbOAuthToken).filter(QbOAuthToken.revoked_at.is_(None))
    if realm_id:
        query = query.filter(QbOAuthToken.realm_id == realm_id)
    tokens = query.all()
    if not tokens:
        raise HTTPException(
            status_code=400,
            detail="No active QB OAuth token. Visit /qb/connect to authorize.",
        )
    if len(tokens) > 1 and not realm_id:
        raise HTTPException(
            status_code=400,
            detail=(
                "Multiple realms connected; pass ?realm_id=... to disambiguate. "
                f"Available: {[t.realm_id for t in tokens]}"
            ),
        )
    token = tokens[0]

    if token.environment != settings.qb_environment:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Token was authorized against QB_ENVIRONMENT={token.environment!r} "
                f"but current config is QB_ENVIRONMENT={settings.qb_environment!r}. "
                "Refusing to use cross-environment tokens. Re-authorize via /qb/connect."
            ),
        )

    if token.access_token_expires_at < datetime.now(timezone.utc):
        # TODO(Step 1b): auto-refresh using refresh_access_token(); raise
        # a clearer error for Step 1a so the operator re-authorizes manually.
        raise HTTPException(
            status_code=401,
            detail=(
                "Access token expired. Token refresh is not yet wired "
                "(pending Step 1b). Re-authorize via /qb/connect."
            ),
        )

    try:
        since_date = datetime.strptime(since, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid date: {since}. Use YYYY-MM-DD.")

    # Construct the read-only client and run the sync.
    client = QbClient(access_token=token.access_token, realm_id=token.realm_id)
    accounts_added = sync_accounts(db, client)
    classes_added = sync_classes(db, client)
    db.flush()  # so QbClass rows exist before transactions reference them
    transactions_added = sync_transactions(db, client, since_date)
    db.flush()  # so new transactions are visible to the attachable sync
    attachables_processed = sync_attachables(db, client)
    db.commit()

    return SyncResponse(
        realm_id=token.realm_id,
        accounts_added=accounts_added,
        classes_added=classes_added,
        transactions_added=transactions_added,
        attachables_processed=attachables_processed,
        since=since,
    )
