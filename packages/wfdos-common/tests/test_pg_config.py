"""Tests for the `PG_CONFIG` shim in wfdos_common.config (#27).

The `PG_CONFIG` dict replaces the pre-#27 `scripts/pgconfig.py` module that
every service used to import via `sys.path.insert(0, ".../scripts")`. The new
home is `from wfdos_common.config import PG_CONFIG` — same dict shape, same
keys, so `psycopg2.connect(**PG_CONFIG)` keeps working at every migrated
call site without changes.

These tests pin the shape + lazy-load behavior so a future refactor of the
settings class can't silently break all services.
"""

from __future__ import annotations


def test_pg_config_importable_from_config_package():
    """The public surface for #27 — `from wfdos_common.config import PG_CONFIG`."""
    from wfdos_common.config import PG_CONFIG

    assert PG_CONFIG is not None


def test_pg_config_has_psycopg2_connect_kwargs():
    """psycopg2.connect(**PG_CONFIG) is the call site pattern that every
    migrated service uses. The dict must have exactly the keys psycopg2
    expects — no extras, all five present."""
    from wfdos_common.config import PG_CONFIG

    expected_keys = {"host", "database", "user", "password", "port"}
    assert set(PG_CONFIG.keys()) == expected_keys


def test_pg_config_values_match_settings():
    """PG_CONFIG is a lazy view over wfdos_common.config.settings.pg —
    updating one must reflect in the other."""
    from wfdos_common.config import PG_CONFIG, settings

    assert PG_CONFIG["host"] == settings.pg.host
    assert PG_CONFIG["database"] == settings.pg.database
    assert PG_CONFIG["user"] == settings.pg.user
    assert PG_CONFIG["port"] == settings.pg.port
    # Empty-password case: settings.pg.password may be None; PG_CONFIG
    # coerces to empty string so psycopg2 doesn't barf.
    assert PG_CONFIG["password"] == (settings.pg.password or "")


def test_pg_config_repr_masks_password():
    """Repr shouldn't leak the password to logs."""
    from wfdos_common.config import PG_CONFIG

    # Force a non-empty password so the mask actually activates.
    PG_CONFIG["password"] = "super-secret-123"  # type: ignore[index]
    repr_str = repr(PG_CONFIG)
    assert "super-secret-123" not in repr_str
    assert "***" in repr_str or "password" not in repr_str


def test_pg_config_is_dict_subclass():
    """Must remain a real dict so **PG_CONFIG unpacking works."""
    from wfdos_common.config import PG_CONFIG

    assert isinstance(PG_CONFIG, dict)

    # The unpack pattern services use:
    kwargs = {**PG_CONFIG}
    assert "host" in kwargs
    assert "database" in kwargs


def test_scripts_pgconfig_shim_reexports_same_object():
    """Scripts that still import by file path (scripts/pgconfig.py) must
    get the canonical PG_CONFIG, not a separate dict."""
    # Simulate a one-off CLI script loading scripts/pgconfig.py by path.
    import importlib.util
    import os

    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
    shim_path = os.path.join(repo_root, "scripts", "pgconfig.py")
    assert os.path.exists(shim_path), f"shim missing at {shim_path}"

    spec = importlib.util.spec_from_file_location("pgconfig_shim", shim_path)
    assert spec is not None and spec.loader is not None
    shim = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(shim)

    from wfdos_common.config import PG_CONFIG as canonical

    assert shim.PG_CONFIG is canonical
