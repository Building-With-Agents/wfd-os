# CFA → Waifinder identity migration runbook

## Why this doc exists

Per cross-cutting constraint #2 in the refactor plan: CFA (Computing for All) and Waifinder are becoming separate business entities. When that flip happens, everything tenant-scoped must move by **config change, not code change**. No CFA identifier may be hardcoded in source.

This runbook enumerates the current CFA identifiers and says, for each, how to flip it when the Waifinder tenant is provisioned.

## Identifiers inventory (as of #18)

| Identifier | Where it lives today | How to flip |
|---|---|---|
| `ritu@computingforall.org` email sender | `settings.email.sender` (alias `EMAIL_SENDER`) — default literal in `wfdos_common/config/settings.py:EmailSettings` | Set `EMAIL_SENDER=<new>` in the Waifinder deployment's env. Default in code can be changed in a follow-up once Waifinder's sender mailbox exists. |
| `ritu@computingforall.org` notification recipient | `settings.email.notify` (alias `NOTIFY_EMAIL`) — same file | Set `NOTIFY_EMAIL=<new>` in env. |
| `https://computinforall.sharepoint.com` SharePoint tenant URL | `settings.sharepoint.tenant_url` (alias `SHAREPOINT_TENANT_URL`) | Set `SHAREPOINT_TENANT_URL=https://waifinder.sharepoint.com` (or wherever). |
| CFA Azure tenant GUID | `settings.graph.tenant_id` + `settings.azure.tenant_id` (aliases `GRAPH_TENANT_ID` / `AZURE_TENANT_ID`) | Set both env vars to the Waifinder Azure AD tenant GUID. |
| WFD-OS app registration IDs | `settings.azure.client_id` / `.client_secret` | Provision a new Waifinder app registration; replace env values. |
| Graph app registration (Scoping/Grant) | `settings.graph.client_id` / `.client_secret` | Same — new Waifinder-tenant Graph app. |
| `CFA_TEAM_ID` Teams ID | `settings.teams.cfa_team_id` (alias `CFA_TEAM_ID`) | TODO: rename alias to `TEAMS_DEFAULT_TEAM_ID` with dual-read; set env to Waifinder's team. |
| `CFA_CLIENT_PORTAL_SITE_ID` SharePoint site | `settings.sharepoint.cfa_client_portal_site_id` (alias `CFA_CLIENT_PORTAL_SITE_ID`) | TODO: rename alias to `CLIENT_PORTAL_SITE_ID` with dual-read; set env to Waifinder's site. |
| `cfa_grants` DB name fallback | `agents/grant/database/db.py:12` hardcoded default in connection string | Remove fallback (#19). Require `DATABASE_URL` to be set explicitly. |

## Aliases to rename (dual-read deprecation, deferred)

These two identifiers have "CFA" in the env-var name. Renaming them requires dual-read (both old and new names read with a deprecation warning on the old), which is straightforward but touches every deployment's env file. Done in a follow-up issue after #18 lands:

- `CFA_TEAM_ID` → `TEAMS_DEFAULT_TEAM_ID`
- `CFA_CLIENT_PORTAL_SITE_ID` → `CLIENT_PORTAL_SITE_ID`

Value literals (e.g., the current CFA team GUID in any `.env` file) don't need code changes — they're already env-driven.

## Flip sequence (when Waifinder entity is ready)

1. Provision the Waifinder Azure AD tenant + Graph app registration.
2. Provision the Waifinder SharePoint site + Teams team.
3. Update the Waifinder-flagship deployment's env (systemd `EnvironmentFile` on the VM) with the new GUIDs, URLs, and sender mailbox.
4. Restart services. Every identifier flows through `wfdos_common.config`, so no code deploy is needed.
5. Keep the CFA tenant env values available in the CFA-branded deployment (if one continues to run).

## Why not rename now

The rename requires both a code change and an `.env.example` change. Doing it in the middle of the #18 settings consolidation bloats that PR. The settings layer (this PR) has the right shape; the renames are a small follow-up that's safe to defer.

## Related

- wfd-os#18 — settings consolidation (this doc ships with it).
- wfd-os#9 — credential rotation (opportunity to rotate + rename in one pass).
- wfd-os#16 — white-label runtime config (per-tenant branding at the portal layer; complementary to this infra-level decoupling).
