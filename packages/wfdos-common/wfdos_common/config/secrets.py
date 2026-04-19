"""Pluggable secret-backend protocol for wfdos_common.config.

Default: EnvBackend — reads secrets from process env / `.env`. This is what
runs today and what will run in prod on the VM (systemd EnvironmentFile) and
in CI (GitHub Actions secrets).

Opt-in plugins (declared as extras in pyproject.toml, lazy-imported here):
    KeyVaultBackend, OnePasswordBackend, DopplerBackend, InfisicalBackend, VaultBackend

Backend selection:
    WFDOS_SECRET_BACKEND=env              # default
    WFDOS_SECRET_BACKEND=keyvault         # requires `pip install wfdos-common[keyvault]`
    WFDOS_SECRET_BACKEND=onepassword      # requires `pip install wfdos-common[onepassword]`
    ... etc.

Per Gary's direction (2026-04-14): no Azure Key Vault default. The platform
stays decoupled from Azure-specific services so the CFA → Waifinder
subscription migration stays config-only.
"""

from __future__ import annotations

import os
from typing import Optional, Protocol


class SecretBackend(Protocol):
    """Protocol for secret-retrieval backends.

    Implementations pull secrets from some external store (env, Key Vault,
    1Password, Doppler, etc.) and return them as strings. None means the
    secret was not found; callers decide whether to fall back or fail.
    """

    def get(self, name: str) -> Optional[str]:
        """Return the secret value for `name`, or None if not set."""
        ...


class EnvBackend:
    """Default backend — reads from process env and loaded .env file.

    The .env is auto-loaded by wfdos_common.config.settings on import, so
    callers do not need to call load_dotenv() themselves.
    """

    def get(self, name: str) -> Optional[str]:
        return os.getenv(name)


def _load_backend_class(name: str) -> type:
    """Lazy-import an opt-in backend. Raises ImportError with a clear
    message if the corresponding extras group isn't installed.
    """
    if name == "keyvault":
        try:
            from wfdos_common.config.backends.keyvault import KeyVaultBackend

            return KeyVaultBackend
        except ImportError as e:  # pragma: no cover — optional dep
            raise ImportError(
                "KeyVault backend requires: pip install 'wfdos-common[keyvault]'"
            ) from e
    if name == "onepassword":
        try:
            from wfdos_common.config.backends.onepassword import OnePasswordBackend

            return OnePasswordBackend
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "1Password backend requires: pip install 'wfdos-common[onepassword]'"
            ) from e
    if name == "doppler":
        try:
            from wfdos_common.config.backends.doppler import DopplerBackend

            return DopplerBackend
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "Doppler backend requires: pip install 'wfdos-common[doppler]'"
            ) from e
    if name == "infisical":
        try:
            from wfdos_common.config.backends.infisical import InfisicalBackend

            return InfisicalBackend
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "Infisical backend requires: pip install 'wfdos-common[infisical]'"
            ) from e
    if name == "hashivault":
        try:
            from wfdos_common.config.backends.hashivault import VaultBackend

            return VaultBackend
        except ImportError as e:  # pragma: no cover
            raise ImportError(
                "HashiCorp Vault backend requires: pip install 'wfdos-common[hashivault]'"
            ) from e
    raise ValueError(
        f"Unknown secret backend: {name!r}. "
        "Valid: env (default), keyvault, onepassword, doppler, infisical, hashivault."
    )


def get_secret_backend() -> SecretBackend:
    """Return the active SecretBackend instance.

    Backend selected by WFDOS_SECRET_BACKEND env var. Defaults to EnvBackend.
    """
    name = os.getenv("WFDOS_SECRET_BACKEND", "env").strip().lower()
    if name == "env":
        return EnvBackend()
    cls = _load_backend_class(name)
    return cls()
