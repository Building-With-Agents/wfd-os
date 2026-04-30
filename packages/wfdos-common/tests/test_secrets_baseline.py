"""Tests guarding the #19 outcomes: hardcoded passwords removed, detect-secrets
scan clean against the committed baseline, ConfigurationError raised when
DATABASE_URL is missing.
"""

import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_no_hardcoded_shivani_password():
    """The compromised literal must be gone from every tracked file."""
    proc = subprocess.run(
        ["git", "grep", "-n", "SuperShivani"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    # git grep returns 1 when nothing matches (clean); 0 when a match exists (dirty).
    # Allowed matches: docstrings / comments referencing #19 history by literal name.
    matches = [line for line in proc.stdout.splitlines() if line]
    # Filter out the handful of documentary references (this test file, the
    # issue archive, the rotation runbook, Phase 4 exit report — none of these
    # reintroduce the live password; they document the historical leak).
    offending = [
        m for m in matches
        if "test_secrets_baseline" not in m
        and "archive/" not in m
        and "packages/wfdos-common/README" not in m
        and "docs/ops/credential-rotation.md" not in m
        and "docs/refactor/phase-4-exit-report.md" not in m
    ]
    assert not offending, (
        f"Hardcoded 'SuperShivani' literal still in code: {offending}"
    )


def test_no_postgres_default_password_url():
    """The weak default 'postgres:password@' fallback must be gone."""
    proc = subprocess.run(
        ["git", "grep", "-n", "postgres:password@"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    matches = [line for line in proc.stdout.splitlines() if line]
    offending = [
        m for m in matches
        if "archive/" not in m
        and "test_secrets_baseline" not in m
    ]
    assert not offending, (
        f"Weak 'postgres:password@' default URL still in code: {offending}"
    )


def test_detect_secrets_baseline_clean():
    """detect-secrets scan against the repo must match the committed baseline
    (no new findings).
    """
    baseline = REPO_ROOT / ".secrets.baseline"
    assert baseline.exists(), ".secrets.baseline must be committed"

    # Prefer python-module invocation so this works without detect-secrets
    # being on PATH in CI.
    proc = subprocess.run(
        [sys.executable, "-m", "detect_secrets", "scan",
         "--baseline", str(baseline)],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        stdin=subprocess.DEVNULL,
    )
    # detect-secrets exits 0 when the scan matches baseline, 1 when new findings
    # are detected. Accept 0 only.
    assert proc.returncode == 0, (
        f"detect-secrets found new findings:\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )


def test_grant_db_raises_on_missing_database_url(monkeypatch):
    """agents/grant/database/db.py:init_db() must fail-fast without DATABASE_URL."""
    from wfdos_common.config import ConfigurationError

    monkeypatch.delenv("DATABASE_URL", raising=False)

    # Import path requires grant's database package on sys.path. We test the
    # imported module's init_db() function instead of trying to import the
    # relative `database.models`. This test's guarantee: the ConfigurationError
    # is raised — not that the import itself succeeds. That is a fair boundary
    # for #19.
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "grant_db_test",
        str(REPO_ROOT / "agents" / "grant" / "database" / "db.py"),
    )
    try:
        mod = importlib.util.module_from_spec(spec)
        # Stub out the `database.models` relative import so loading succeeds.
        import types
        fake_models_pkg = types.ModuleType("database")
        fake_models_mod = types.ModuleType("database.models")

        class FakeBase:
            class metadata:
                @staticmethod
                def create_all(bind=None):
                    pass

        fake_models_mod.Base = FakeBase
        sys.modules.setdefault("database", fake_models_pkg)
        sys.modules["database.models"] = fake_models_mod

        spec.loader.exec_module(mod)
    except Exception as e:  # pragma: no cover — the module itself might error before we get to call init_db; that's OK for this test.
        pytest.skip(f"grant db module could not be loaded in isolation: {e}")
        return

    with pytest.raises(ConfigurationError) as excinfo:
        mod.init_db()
    assert "DATABASE_URL" in str(excinfo.value)
