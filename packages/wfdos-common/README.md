# wfdos-common

Shared primitives for wfd-os services. Imported by each service so that config, DB access, LLM adapter, auth, logging, Microsoft Graph client, and email logic are not duplicated across independently-deployable services.

This package exists because the 2026-04-14 product-architecture review (locked by Ritu) rejected consolidating wfd-os into a single FastAPI gateway app (Option A). Each service must stay independently deployable because each is a potentially sellable product (JIE, Talent Showcase, College Pipeline, etc.). Shared code ships as this pip package; services `pip install wfdos-common` and import what they need.

See `Desktop/tmp/wfdos-product-architecture-discussion.md` for the full decision record.

## Install (dev)

From the repo root:

```bash
pip install -e packages/wfdos-common
```

Running services against their existing `.env` continues to work — no behavior change from installing this package.

## Install (prod)

Published to GitHub Packages on tag push `wfdos-common-vX.Y.Z`. (Publishing workflow lands with #27.)

## Module-by-module status

| Module | Status | Owning issue |
|---|---|---|
| `wfdos_common.config` | stub | #18 |
| `wfdos_common.models` | stub | #21 |
| `wfdos_common.db` | stub | #22 |
| `wfdos_common.agent` | stub | #26 |
| `wfdos_common.auth` | stub | #24 |
| `wfdos_common.graph` | migrated (see below) | #17 |
| `wfdos_common.email` | migrated (see below) | #17 |
| `wfdos_common.llm` | stub | #20 |
| `wfdos_common.logging` | stub | #23 |
| `wfdos_common.testing` | stub | #28 |

## Migration pattern (shim + flip)

Modules migrating from `agents/*` follow a two-step deprecation:

1. **Copy** the module into `wfdos_common.*` (new canonical location).
2. **Re-export shim** at the old `agents/*` path — `from wfdos_common.X import *` — so existing importers keep working without change.
3. **Flip importers** (separate commit) to use the new path.
4. **Remove shim** one release later (in a follow-up PR, after all known importers have been flipped).

This satisfies the no-breaking-changes migration invariant: every commit leaves services runnable with the existing `.env`.

## Secret backends

`wfdos_common.config.secrets` defines a pluggable `SecretBackend` protocol. The default is `EnvBackend` (reads from process env / `.env` — what runs today). Opt-in backends:

```bash
pip install "wfdos-common[keyvault]"     # Azure Key Vault
pip install "wfdos-common[onepassword]"  # 1Password Connect
pip install "wfdos-common[doppler]"      # Doppler
pip install "wfdos-common[infisical]"    # Infisical
pip install "wfdos-common[hashivault]"   # HashiCorp Vault
```

Select a backend via `WFDOS_SECRET_BACKEND=<name>`. Default is `env`. Deliberately no Azure Key Vault default — decouples the platform from Azure-specific services and simplifies the CFA → Waifinder subscription migration (see #18).

## Tests

```bash
pytest packages/wfdos-common/tests
```

## License

Proprietary.
