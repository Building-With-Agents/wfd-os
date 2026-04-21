"""wfdos_common.graph — Microsoft Graph API client and helpers.

Migrated from agents/graph/ in Building-With-Agents/wfd-os#17 — this is
the new home. The old path (agents/graph/) now re-exports from here for
one deprecation cycle.

Public API (preserved from the original module):
- auth.get_graph_client(): GraphServiceClient
- auth.graph_post(...): direct POST helper
- sharepoint.*: workspace/document operations
- teams.*: channel/meeting operations
- invitations.*: folder sharing
- transcript.*: meeting transcript retrieval

Implementation populated later in this same PR (commit: migrate agents/graph).
"""
