"""Tests that `agents.portal.email` correctly re-exports `wfdos_common.email` (#17)."""


def test_email_shim_identity():
    """Functions resolved through the shim are the same objects as canonical."""
    from agents.portal.email import notify_internal as shim_notify
    from agents.portal.email import send_email as shim_send
    from wfdos_common.email import notify_internal, send_email

    assert shim_send is send_email
    assert shim_notify is notify_internal


def test_email_constants_accessible_via_shim():
    """Module-level constants accessible through either path."""
    from agents.portal.email import DEFAULT_SENDER as shim_default, GRAPH_BASE as shim_base
    from wfdos_common.email import DEFAULT_SENDER, GRAPH_BASE

    assert shim_default == DEFAULT_SENDER
    assert shim_base == GRAPH_BASE
