"""Tests for the production+encryption_key startup guard in config.py.

See config.py `_refuse_production_without_encryption_key` for rationale.
The guard is intentional — do not remove or weaken these tests without
first reading CLAUDE.md "Enforced constraints".
"""

from __future__ import annotations

import pytest

from grant_compliance.config import Settings


def test_sandbox_without_encryption_key_is_allowed():
    """Default dev configuration — sandbox + plaintext tokens. Must work."""
    settings = Settings(qb_environment="sandbox", encryption_key="")
    assert settings.qb_environment == "sandbox"
    assert settings.encryption_key == ""


def test_production_with_encryption_key_is_allowed():
    """Correct production config — encryption key is set. Must work."""
    settings = Settings(
        qb_environment="production",
        encryption_key="some-fernet-key-placeholder",
    )
    assert settings.qb_environment == "production"
    assert settings.encryption_key == "some-fernet-key-placeholder"


def test_production_without_encryption_key_raises():
    """The critical guard: production with plaintext token storage is refused."""
    with pytest.raises(
        RuntimeError,
        match="REFUSING TO START.*ENCRYPTION_KEY is not set",
    ):
        Settings(qb_environment="production", encryption_key="")


def test_guard_error_mentions_escape_hatches():
    """Error message must tell the operator how to fix it — generate a Fernet
    key OR flip back to sandbox. Without both paths documented, people panic."""
    with pytest.raises(RuntimeError) as exc_info:
        Settings(qb_environment="production", encryption_key="")
    msg = str(exc_info.value)
    assert "Fernet" in msg, "Error must mention Fernet for key generation"
    assert "sandbox" in msg, "Error must mention the sandbox escape hatch"


def test_guard_does_not_block_default_construction():
    """Default Settings() — sandbox, blank key — must not raise. If it did,
    every test and every dev session would fail before doing anything."""
    settings = Settings()
    assert settings.qb_environment == "sandbox"
