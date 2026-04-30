"""Microsoft Graph API client — DEPRECATED import path.

The canonical location is `wfdos_common.graph` (migrated in #17).
This package remains as a re-export shim for one deprecation cycle so
existing code keeps working without change. Each submodule below is a
star-import from the new location.

Flip importers to `wfdos_common.graph.*` when touching them. When no
known importer references `agents.graph` anymore, this shim is removed
in a follow-up PR.
"""
