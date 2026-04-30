"""wfdos-common: shared primitives for wfd-os services.

Per the 2026-04-14 product-architecture review, this package is the shared
library that wfd-os services import to avoid duplicating config, DB access,
LLM adapter, auth, logging, Microsoft Graph client, and email code across
independently-deployable services.

See packages/wfdos-common/README.md for module-by-module status.
"""

__version__ = "0.0.1"
