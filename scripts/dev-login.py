"""Dev-only: mint a magic-link token for an allowlisted email and open
the browser at `/auth/verify` so the user gets a real `wfdos_session`
cookie. Removes the manual "open DevTools, set x-test-user-* headers"
step from local LaborPulse testing.

Flow:

  1. Read `WFDOS_AUTH_SECRET_KEY` and the allowlist env vars from `.env`
     via `wfdos_common.config.settings`.
  2. Pick the dev's email (from `--email`, or the first entry in
     `WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST` / staff / admin).
  3. Mint a magic-link token via `issue_magic_link()`.
  4. Open `http://localhost:8012/auth/verify?token=...` in the default
     browser. The route validates the token, mints a session, sets the
     `wfdos_session` cookie (Domain=localhost, port-agnostic), and
     redirects to `/laborpulse` on the portal.

After the script completes, refresh `http://localhost:3000/laborpulse`
or just stay on the redirected page — the cookie is set for the whole
`localhost` host and travels to both port 3000 (portal) and 8012
(laborpulse-api).

Prereqs (all from the runbook):

  - `laborpulse-api` running on `:8012` (Step 6: `honcho start portal laborpulse-api`).
  - `.env` populated (Step 5) — at minimum `WFDOS_AUTH_SECRET_KEY` set
    AND your email in `WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST`.

Usage:

    python scripts/dev-login.py
    python scripts/dev-login.py --email gary@example.com
    python scripts/dev-login.py --email gary@example.com --no-open
    python scripts/dev-login.py --laborpulse-base http://localhost:8012

Failure modes:

  - "WFDOS_AUTH_SECRET_KEY is not set"  → fix `.env` (Step 5).
  - "no email provided and no allowlist..." → set
    `WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST=<your@email>` in `.env`
    OR pass `--email`.
  - Browser redirects to `?auth_error=1` → token expired (15 min TTL)
    or email not in any allowlist when `/verify` ran. Re-check `.env`.
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from urllib.parse import quote

from wfdos_common.auth.tokens import issue_magic_link
from wfdos_common.config import settings


def _resolve_email(arg_email: str | None) -> str:
    """Pick an email: CLI arg > workforce-dev allowlist[0] > staff[0] > admin[0]."""
    if arg_email:
        return arg_email.strip().lower()
    for csv in (
        settings.auth.workforce_development_allowlist,
        settings.auth.staff_allowlist,
        settings.auth.admin_allowlist,
    ):
        if csv and csv.strip():
            first = csv.split(",")[0].strip().lower()
            if first:
                return first
    sys.stderr.write(
        "FAIL: no email provided and no allowlist configured.\n"
        "      Set WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST in .env (Step 5)\n"
        "      OR pass --email <your@email>.\n"
    )
    sys.exit(2)


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--email",
        default=None,
        help="Email to authenticate as. Default: first entry in "
             "WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST.",
    )
    parser.add_argument(
        "--laborpulse-base",
        default="http://localhost:8012",
        help="Base URL of the laborpulse-api service hosting /auth/verify.",
    )
    parser.add_argument(
        "--no-open",
        action="store_true",
        help="Print the URL but don't open the browser. Useful for remote shells.",
    )
    args = parser.parse_args()

    email = _resolve_email(args.email)
    secret = settings.auth.secret_key
    if not secret or secret == "dev-only-secret-replace-in-production-do-not-ship":
        sys.stderr.write(
            "FAIL: WFDOS_AUTH_SECRET_KEY is not set in .env (or still has the\n"
            "      placeholder default). Step 5 of the runbook covers this:\n"
            '        python -c "import secrets; print(secrets.token_hex(32))"\n'
            "      Then put the output in .env as WFDOS_AUTH_SECRET_KEY=...\n"
        )
        sys.exit(2)

    token = issue_magic_link(email, secret_key=secret)
    url = f"{args.laborpulse_base}/auth/verify?token={quote(token, safe='')}"

    print(f"OK: minted magic-link token for {email!r}")
    print(f"    token TTL: {settings.auth.magic_link_ttl_seconds}s "
          f"(visit the URL within that window)")
    print(f"    /verify URL:")
    print(f"      {url}")
    print(f"    after the cookie is set, browser redirects to:")
    print(f"      {settings.platform.portal_base_url.rstrip('/')}/laborpulse")
    print()

    if args.no_open:
        print("--no-open passed; copy the URL above into your browser manually.")
        return

    opened = webbrowser.open(url)
    if not opened:
        print(
            "Browser did not auto-open (webbrowser.open returned False).\n"
            "Copy the URL above and paste it into your browser."
        )
    else:
        print(
            "Browser opened. Wait for the redirect to /laborpulse, then ask a\n"
            "question. To verify auth landed, open DevTools → Application →\n"
            "Cookies → look for `wfdos_session` on http://localhost:3000."
        )


if __name__ == "__main__":
    main()
