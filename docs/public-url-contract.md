# Public URL contract

**Purpose:** documents the stable URLs that marketing + external
integrations depend on. Any change to these routes — renaming, removing,
or changing response shape — breaks live CTAs in Squarespace, Apollo
sequences, email campaigns, and client-facing links. Treat every URL
here as part of the public API.

**Audience:** anyone editing Next.js routes in `portal/student/app/` or
a FastAPI service. If a route appears here and you're touching it,
follow the deprecation policy below before merging.

## Current state (2026-04-16)

Marketing (`thewaifinder.com`) lives on Squarespace — **not in this
repo**. The platform is at `platform.thewaifinder.com`. The agreement:

- Squarespace → platform = **one-way hyperlinks only**. No CORS, no
  session bleed, no iframes, no shared cookies.
- Squarespace CTA URLs point at the stable routes below.

Per-tenant white-label deployments (e.g. `talent.borderplexwfs.org`)
expose the same routes on their own hostname.

## The contract

### Auth

| URL                          | Method | Purpose                                  | Deprecation policy |
|------------------------------|--------|------------------------------------------|--------------------|
| `/auth/login`                | POST   | Magic-link issue                         | 90 days            |
| `/auth/verify?token=...`     | GET    | Magic-link verify + session cookie       | 90 days            |
| `/auth/logout`               | POST   | Clear session cookie                     | 90 days            |
| `/auth/me`                   | GET    | Current session inspection               | 90 days            |

### Portal marketing landing routes

These are the URLs Squarespace CTAs + Apollo outreach emails point at.
Changing them without a 90-day redirect breaks the funnel.

| URL                          | Purpose                                             | Deprecation policy |
|------------------------------|-----------------------------------------------------|--------------------|
| `/`                          | Portal home                                         | permanent          |
| `/careers`                   | Student agent (careers + jobs landing)              | 90 days            |
| `/showcase`                  | Employer-facing talent showcase browse              | 90 days            |
| `/for-employers`             | Employer landing + consulting entry                 | 90 days            |
| `/college`                   | College-partner landing                             | 90 days            |
| `/youth`                     | Under-18 / high-school program landing              | 90 days            |
| `/pricing`                   | Pricing summary (stub today; fleshed out with #32) | 90 days            |
| `/cfa/ai-consulting`         | Consulting service landing                          | 90 days            |
| `/cfa/ai-consulting/chat`    | Consulting intake agent (public)                    | 90 days            |
| `/laborpulse`                | Workforce-development director Q&A (auth required)  | 90 days            |
| `/api/laborpulse/query`      | SSE streaming Q&A proxy to JIE                      | 90 days            |
| `/api/laborpulse/feedback`   | Thumbs-up/down write to `qa_feedback`               | 90 days            |

### CTA routes (future)

These are reserved for #32 (signup + paid tier). They appear here so
marketing can link to them before the implementation lands, giving the
404 handler a chance to show a "coming soon" page that tracks the
conversion.

| URL                          | Purpose                                             | Status           |
|------------------------------|-----------------------------------------------------|------------------|
| `/register`                  | Sign-up page                                        | FUTURE WORK (#32)|
| `/pay/{plan}`                | Stripe checkout for `{plan}` (student / starter / pro) | FUTURE WORK (#32)|
| `/go/{campaign}`             | Campaign-specific vanity redirect                   | FUTURE WORK      |

### Health + ops

| URL                          | Purpose                                             | Deprecation policy |
|------------------------------|-----------------------------------------------------|--------------------|
| `/api/health`                | Per-service liveness (on every FastAPI service)     | permanent          |

## Deprecation policy

**When removing or renaming a contract URL:**

1. Open an issue labelled `public-url-change` with the contract change.
2. Add a `301` permanent redirect from the old URL to the new one.
3. Keep the redirect live for 90 days minimum, 180 days for anything
   appearing in Squarespace, Apollo sequences, or client contracts.
4. Update `docs/public-url-contract.md` with the new URL on the same
   PR that adds the redirect.
5. After the retention window, a follow-up PR removes the redirect and
   the old entry.

**When adding a contract URL:**

1. Add the entry here BEFORE merging the route itself.
2. Ship the route.
3. Announce to Jessica (marketing) + Jason (BD) so Squarespace + Apollo
   can start linking at it.

## CI enforcement

`packages/wfdos-common/tests/test_public_url_contract.py` parses this
doc, extracts every URL pattern, and asserts each one exists in at
least one service's registered routes. A PR that removes a contract
URL without updating the doc fails CI.

The check is deliberately **additive-only** — it doesn't require every
listed URL to respond 200 (some are future / stub / behind auth), just
that the route is registered somewhere. Live smoke against 200s belongs
in the deployment runbook, not in per-PR CI.

## Relationship to Squarespace → platform one-way

The apex `thewaifinder.com` is Squarespace and is **out of scope** for
this repo. CORS is not configured from Squarespace → platform; every
cross-origin interaction is a top-level link click, which is what the
URLs above catch. Session cookies never cross the apex/platform boundary
because the auth cookie is scoped to `platform.thewaifinder.com` (and
per-tenant white-label hosts).
