# Credential rotation runbook

**Audience:** Gary + any future ops owner with access to Azure Portal,
Anthropic Console, Apollo, QuickBooks, and the SharePoint admin center.

**Scope:** every secret that lands in `.env` + every secret the deployed
services reach for at runtime. A compromise of `.env` or any
`EnvironmentFile` on the production VM is the trigger for executing
this runbook end-to-end; individual rotations (e.g. an API key leak)
follow just the relevant section.

## Team secret store — the decision

**Current state (2026-04-16):** secrets live in `.env` files on developer
laptops + the production VM's systemd `EnvironmentFile`. There is no
shared secret store yet.

**Chosen direction:** **1Password teams vault** per the `WFDOS_SECRET_BACKEND`
options declared in `wfdos-common[onepassword]` (#18). Trade-offs considered:

| Backend              | Pro                                                            | Con                                                         |
|---------------------|----------------------------------------------------------------|-------------------------------------------------------------|
| **1Password teams** | Lowest-friction handoff, already used by Gary personally        | Requires paid seat per developer                            |
| Doppler             | Generous free tier, CI integration out of the box               | One more SaaS surface; Gary not already on it               |
| Azure Key Vault     | Zero-cost within our Azure subscription                         | Rejected in Ritu's 2026-04-14 review as overcomplicating dev loops |
| HashiCorp Vault     | Industry standard                                               | Self-hosting or HCP bill; overkill for this team size       |
| Infisical           | OSS-friendly; self-hostable                                     | Smaller ecosystem; fewer guardrails                         |

Nothing about the runbook below requires 1Password — the value columns
name the secret, not the store. When 1Password adoption lands, this doc
gets a "Where to find it" appendix pointing at the vault items.

## Rotation cadence

- **Monthly** — any credential suspected of exposure, plus any previously
  committed in source before detect-secrets went in (#19 already did this
  for `SuperShivani1`).
- **Quarterly** — Anthropic, Gemini, Apollo personal-access tokens.
- **On developer departure** — every credential on every service.
- **On visible incident** — immediately, end-to-end.

## Credentials inventory

| # | Credential                                           | Lives in                              | Rotation source system                                       | Env var(s)                                            |
|---|------------------------------------------------------|---------------------------------------|---------------------------------------------------------------|-------------------------------------------------------|
| 1 | Azure AD client secret (WFD-OS app)                 | `.env`, prod VM, CI                   | Azure Portal → App Registrations → WFD-OS → Certs & secrets   | `AZURE_CLIENT_SECRET`                                 |
| 2 | Microsoft Graph client secret                        | `.env`, prod VM                       | Same app registration as #1                                   | `GRAPH_CLIENT_SECRET`                                 |
| 3 | Azure OpenAI API key                                 | `.env`, prod VM                       | Azure Portal → Azure OpenAI → Keys and Endpoint → Rotate      | `AZURE_OPENAI_KEY`                                    |
| 4 | Anthropic API key                                    | `.env`, prod VM                       | console.anthropic.com → API keys → Create + delete            | `ANTHROPIC_API_KEY`                                   |
| 5 | Gemini API key                                       | `.env`, prod VM                       | aistudio.google.com/app/apikey                                | `GEMINI_API_KEY`                                      |
| 6 | Apollo API key                                       | `.env`, prod VM                       | apollo.io → Settings → Integrations → API                     | `APOLLO_API_KEY`                                      |
| 7 | Postgres application password (JIE mirror)           | `.env`, prod VM                       | Azure Portal → pg-jobintel-cfa-dev → Reset admin password     | `PG_PASSWORD`                                         |
| 8 | Postgres market-intelligence password                | `.env`, prod VM                       | Azure Postgres flexible server → Reset password               | `MARKET_INTELLIGENCE_PG_PASSWORD`                     |
| 9 | WFDOS auth signing key                               | `.env`, prod VM                       | Generated locally: `python -c "import secrets; print(secrets.token_urlsafe(64))"` | `WFDOS_AUTH_SECRET_KEY`               |
| 10 | Azure Blob Storage connection string                | `.env`, prod VM                       | Azure Portal → Storage account → Access keys → Rotate         | `AZURE_BLOB_CONNECTION_STRING`                        |
| 11 | Azure Function key (JIE matching endpoint)          | `.env`, prod VM                       | Azure Portal → Function app → App keys                        | `AZURE_FUNCTION_KEY`                                  |
| 12 | Microsoft Bot Framework app password                | `.env`, prod VM                       | Azure Portal → Bot resource → Configuration                   | `MICROSOFT_APP_PASSWORD`                              |
| 13 | Dataverse client secret                             | `.env`                                | Azure Portal → App Registrations → Dataverse app              | `DATAVERSE_CLIENT_SECRET`                             |

## Per-credential playbook

The steps below use a uniform structure: **generate** new secret, **stage**
it alongside the old (dual-key), **deploy** the new to the VM, **cut
traffic** to it, **revoke** the old, **audit** that no service is still
pointing at the old. Every credential supports at least one old-and-new
live at the same time — rotations never require a stack restart.

### 1. `AZURE_CLIENT_SECRET` + 2. `GRAPH_CLIENT_SECRET`

These are the same Azure AD app registration (WFD-OS) used for both
Graph API + Dataverse. Treat as a pair.

1. Azure Portal → Azure Active Directory → App registrations → WFD-OS app.
2. Certificates & secrets → **New client secret**. 24-month expiry.
   Copy the **Value** (not the ID); you only see it once.
3. Local `.env` + prod VM `/etc/systemd/system/wfdos-*.service.d/env.conf`
   (or equivalent): set both `AZURE_CLIENT_SECRET=<new>` and
   `GRAPH_CLIENT_SECRET=<new>`.
4. Restart the services that read these (`systemctl restart wfdos-*`).
5. Verify: hit one Graph-dependent endpoint (`/api/scoping/trigger`) and
   one Dataverse-dependent endpoint (market-intelligence/dataverse path).
6. Revoke the old secret in the Azure Portal (same Certificates & secrets
   panel — click the trash icon).
7. Audit: `rg -n 'AZURE_CLIENT_SECRET\|GRAPH_CLIENT_SECRET' .env*` on every
   dev box to make sure nobody still has the old value locally.

### 3. `AZURE_OPENAI_KEY`

Azure OpenAI has two keys (Key1 + Key2) for zero-downtime rotation.

1. Azure Portal → Azure OpenAI resource → **Keys and Endpoint**.
2. Copy Key2 value, update `.env` + prod VM to use it, restart services.
3. Click **Regenerate Key1** (now unused). Wait a few minutes.
4. The old Key1 is now invalid; Key2 remains as the current secret
   until the next rotation, when we flip back to Key1.

### 4. `ANTHROPIC_API_KEY`

Anthropic supports any number of active keys per account.

1. console.anthropic.com → API keys → **Create Key**. Label:
   `wfdos-prod-YYYYMMDD`. Copy once.
2. Add to `.env` + prod VM, restart services, verify with a cheap
   completion (e.g. `wfdos_common.llm.complete` with `tier="default"`).
3. Return to the console → **Revoke** the old key.

### 5. `GEMINI_API_KEY`

Same model as Anthropic (multi-key account).

1. aistudio.google.com/app/apikey → **Create API key**.
2. Update `.env` + prod VM, restart, verify.
3. Return to the key list → delete the old key.

### 6. `APOLLO_API_KEY`

Apollo supports exactly one API key per user. **There is a zero-downtime
technique:** generate the new key under a *second user* first, stage
the deploy, then swap. For a non-zero-downtime rotation, accept a
10-minute Apollo-integration blip.

1. apollo.io → Settings → Integrations → API → **Regenerate**.
2. Immediately update `.env` + prod VM + restart.
3. Apollo webhook verification depends on the shared secret, NOT the
   API key — it rotates separately via the Webhooks tab if needed.

### 7. `PG_PASSWORD` + 8. `MARKET_INTELLIGENCE_PG_PASSWORD`

The Azure Postgres flexible server admin password.

1. Azure Portal → Postgres flexible server → **Reset password**.
   Generate a new value (48+ chars, mixed character classes).
2. Update `.env` + prod VM + CI pipeline variables.
3. Restart every service that opens a DB connection. Since the
   multi-tenant engine factory (#22) caches connections, the engine
   must be re-initialized — in practice that's `systemctl restart`.
4. If using `cfa_readonly` user for the JIE mirror, rotate that
   password via `ALTER ROLE cfa_readonly WITH PASSWORD '...';` rather
   than the server admin.

### 8b. Allowlists (`WFDOS_AUTH_*_ALLOWLIST`)

Four comma-separated lists control who can get a magic link: `ADMIN`,
`STAFF`, `WORKFORCE_DEVELOPMENT` (new in #59 — external customer users
of a Waifinder deployment like the Borderplex WFD director), and
`STUDENT`. First match wins admin > staff > workforce-development >
student.

Rotation = removing an email from the list. No signing-key churn needed.
Live session cookies for the removed email stay valid until their TTL
expires (7 days by default); for immediate revocation, rotate
`WFDOS_AUTH_SECRET_KEY` (section 9) to invalidate every outstanding
cookie.

### 9. `WFDOS_AUTH_SECRET_KEY` (the magic-link + session signing key)

Rotating this invalidates **every active magic link + every live
session cookie**. That's the intended emergency response to a signing-
key leak but also means the next user to hit a protected endpoint gets
a redirect to `/auth/login?reauth=1`.

1. Generate: `python -c "import secrets; print(secrets.token_urlsafe(64))"`.
2. Update `.env` + prod VM `WFDOS_AUTH_SECRET_KEY`.
3. Restart every service that installs the SessionMiddleware.
4. Communicate to users who were signed in: "please sign in again."
   (Magic-link emails sent within the last 15 minutes are also voided.)

### 10. `AZURE_BLOB_CONNECTION_STRING`

Azure Blob has two keys, rotate like Azure OpenAI.

1. Azure Portal → Storage account → **Access keys**.
2. Copy Key2, update env, restart.
3. Regenerate Key1.

### 11. `AZURE_FUNCTION_KEY`

1. Azure Portal → Function app → **App keys** tab.
2. Rotate the key the function is called with (typically `default`).
3. Update env, restart consumers (agents that call the JIE matching endpoint).

### 12. `MICROSOFT_APP_PASSWORD` (Bot Framework)

1. Azure Portal → Bot resource → Configuration → Manage password.
2. Generate a new client secret, update env, restart the market-
   intelligence + grant bots.
3. Revoke the old secret in the portal.

### 13. `DATAVERSE_CLIENT_SECRET`

Identical to #1 — same app registration pattern if a separate app is
used. Verify against the app registration listed in the `.env` comments.

## Post-rotation audit checklist

After every rotation (full or partial):

```bash
# 1. Repo scan — no reintroduced secrets?
detect-secrets scan --baseline .secrets.baseline

# 2. .env audit — does the new value live in exactly one place (the VM)?
ssh <prod-vm> "grep -l '<first 8 chars of new secret>' /etc/systemd/system/wfdos-*.service.d/env.conf | wc -l"

# 3. Service smoke — exercise every service that consumes the rotated key.
# (See the #24 / #29 smoke sections in docs/refactor/phase-4-exit-report.md)

# 4. Confirm old secret is dead — the old value should return 401/403
# from the source system. Any still-working 200 means the revoke didn't
# take; redo.

# 5. Close out — post the rotation date + credential name in
# #team-security (or the equivalent team channel).
```

## Relationship to the original #9 incident response

Issue #9 opened because `SuperShivani1` was committed in source. #19
removed the hardcode; this runbook documents the rotation that must
follow. Once Gary confirms the rotation via the GitHub issue comment,
#9 can close — the code change was independent, but closing the issue
waits on the actual source-system rotation.

**Status as of 2026-04-16:** code change landed in #19 (PR #35).
Rotation pending Gary's next pass against Azure Postgres.
