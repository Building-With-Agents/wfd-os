"""wfdos_common.config — centralized Pydantic Settings + pluggable secret backends.

Public surface:
    settings              — lazy-loaded Settings singleton (see settings.py)
    require(*paths)       — fail-fast validator for required keys
    ConfigurationError    — raised on missing required config
    reset_settings()      — test hook to clear the settings cache
    SecretBackend         — protocol for pluggable secret retrieval
    EnvBackend            — default backend, reads from env/dotenv
    get_secret_backend()  — returns the active backend (selected by WFDOS_SECRET_BACKEND)
"""

from wfdos_common.config.pg_config import PG_CONFIG
from wfdos_common.config.secrets import (
    EnvBackend,
    SecretBackend,
    get_secret_backend,
)
from wfdos_common.config.settings import (
    ConfigurationError,
    Settings,
    require,
    reset_settings,
    settings,
)

__all__ = [
    "settings",
    "require",
    "reset_settings",
    "ConfigurationError",
    "Settings",
    "SecretBackend",
    "EnvBackend",
    "get_secret_backend",
    "PG_CONFIG",
]
