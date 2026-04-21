"""Tests that the deprecated `agents.graph` shim correctly re-exports from
`wfdos_common.graph` (the new canonical location, migrated in #17).

Ensures the migration invariant — no breaking changes — is satisfied: every
pre-migration importer continues to work without modification.
"""


def test_auth_shim_identity():
    """agents.graph.auth functions are the same objects as wfdos_common.graph.auth."""
    from agents.graph.auth import get_graph_client as shim_client
    from agents.graph.auth import graph_post as shim_post
    from wfdos_common.graph.auth import get_graph_client, graph_post

    assert shim_client is get_graph_client
    assert shim_post is graph_post


def test_config_shim_has_expected_constants():
    """agents.graph.config exposes the same constants as wfdos_common.graph.config."""
    from agents.graph import config as shim_config
    from wfdos_common.graph import config

    # Spot-check constants that callers use
    assert shim_config.AZURE_TENANT_ID == config.AZURE_TENANT_ID
    assert shim_config.SCOPING_NOTIFY_CHANNEL_ID == config.SCOPING_NOTIFY_CHANNEL_ID
    assert shim_config.SHAREPOINT_TENANT_URL == config.SHAREPOINT_TENANT_URL
    assert shim_config.CLAUDE_MODEL == config.CLAUDE_MODEL


def test_all_graph_submodules_importable_via_both_paths():
    """Every Graph submodule importable via old and new paths."""
    submodules = ["auth", "config", "invitations", "sharepoint", "teams", "transcript"]
    for name in submodules:
        __import__(f"wfdos_common.graph.{name}")
        __import__(f"agents.graph.{name}")
