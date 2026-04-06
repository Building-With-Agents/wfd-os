# TODO — Delete Legacy Agent Projects After Migration Confirmed

**Status:** Migrated but NOT deleted. Keep as backup until WFD OS is
confirmed stable in production use.

## Context

On 2026-04-05, two standalone Claude Code projects were migrated into
wfd-os as proper WFD OS agents:

| Source | Destination |
|--------|-------------|
| `C:/Users/ritub/projects/cfa-scoping-agent/` | `wfd-os/agents/scoping/` + `wfd-os/agents/graph/` |
| `C:/Users/ritub/projects/cfa-grant-agent/` | `wfd-os/agents/grant/` |

Migration verified with `scripts/test_migration.py`:
- All imports resolve through the new `agents.graph.*` and `agents.scoping.*` paths
- Live Graph API call succeeds through migrated code (fetches `wAIFinder` SharePoint site)
- All models, pipelines, and utilities import cleanly

## When to Delete

Delete the legacy projects only after ALL of the following are true:

1. [ ] WFD OS Scoping Agent has successfully processed at least one
   real Apollo webhook end-to-end (Phase 1: prospect research,
   SharePoint workspace, Teams meeting, calendar invite)
2. [ ] WFD OS Scoping Agent has successfully processed at least one
   post-call transcript (Phase 2: retrieve, analyze, generate proposal .docx)
3. [ ] WFD OS Grant Agent has successfully ingested at least one
   monthly SharePoint upload from CFAOperationsHRFinance
4. [ ] WFD OS Grant Agent has run a reconciliation query against
   grant partner placements
5. [ ] 2 weeks have passed without regression or needing to reference
   the old projects for debugging

## Deletion Commands

Once the above is confirmed:

```powershell
# Back up first to OneDrive (paranoid but cheap)
Compress-Archive -Path C:\Users\ritub\projects\cfa-scoping-agent `
  -DestinationPath C:\Users\ritub\OneDrive\Backups\cfa-scoping-agent-archived.zip
Compress-Archive -Path C:\Users\ritub\projects\cfa-grant-agent `
  -DestinationPath C:\Users\ritub\OneDrive\Backups\cfa-grant-agent-archived.zip

# Then delete the working copies
Remove-Item -Path C:\Users\ritub\projects\cfa-scoping-agent -Recurse -Force
Remove-Item -Path C:\Users\ritub\projects\cfa-grant-agent -Recurse -Force
```

## What NOT to Delete

- The Azure app registration `60a49f2a-230a-4460-bd6d-c0e22bc32384`
  (shared by both agents, still in use from wfd-os/.env as GRAPH_*)
- The SharePoint sites (wAIFinder, CFAOperationsHRFinance, CFA-Client-Portal)
- The Power Automate workflow at SCOPING_WEBHOOK_URL (still triggers the
  Scoping Agent)
- The Teams channel SCOPING_NOTIFY_CHANNEL_ID (still used for notifications)
