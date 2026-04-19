# White-label configuration guide

**Audience:** Gary (onboarding a new client) + the future "consulting
engagement delivery" playbook.

## How requests get mapped to tenants

Every HTTP request to a wfd-os service goes through
`wfdos_common.tenancy.TenantResolutionMiddleware`, which resolves a
`tenant_id` in this priority order:

1. `X-Tenant-Id` header — set by the nginx edge proxy (#30) after it
   inspects the Host header, or by server-to-server callers that know
   the tenant up front.
2. `Host` header — looked up in the in-process brand registry.
3. Fallback: `settings.tenancy.default_tenant_id` (Waifinder flagship).

The resolved `tenant_id` is attached to `request.state.tenant_id` and the
`BrandConfig` for that tenant goes onto `request.state.brand`. Structured
logs (via `wfdos_common.logging`) pick up the tenant_id into every log
record. The DB engine factory from #22 uses it to pick the right
per-tenant DB connection pool.

## The current tenants

Two tenants are registered at import time (see
`wfdos_common.tenancy._DEFAULT_BRANDS`):

| tenant_id              | Host                              | Display name                        |
|------------------------|-----------------------------------|-------------------------------------|
| `waifinder-flagship`   | `platform.thewaifinder.com`       | Waifinder                           |
| `borderplex`           | `talent.borderplexwfs.org`        | Workforce Solutions Borderplex      |

Adding a new client means:

1. Choose a tenant_id (kebab-case, stable, never reused).
2. Choose the client-facing hostname (`talent.<client>.<tld>` is the
   convention).
3. Add a `BrandConfig` entry to `_DEFAULT_BRANDS` OR (preferred once the
   `tenants` DB table lands in Phase 6) insert a row and restart the
   services.
4. Nginx (#30): add a `server` block for the new hostname → `X-Tenant-Id`
   mapping.
5. Email "from" address: set `BrandConfig.email_from_address` to an
   address the Waifinder Graph app can `SendAs`. Request the SendAs
   grant in the Azure admin center if the address is outside the
   Waifinder tenant.
6. DNS: point the hostname at the platform VM / load balancer.
7. Add the client's TLS cert via certbot (`--nginx -d talent.<client>...`).

## BrandConfig schema

```python
@dataclass
class BrandConfig:
    tenant_id: str
    display_name: str
    logo_url: str              # absolute URL — portal loads from here
    primary_color: str         # hex, "#RRGGBB"
    accent_color: str
    email_from_name: str       # "Waifinder", "Workforce Solutions Borderplex"
    email_from_address: str    # must be a Graph-send-as-authorized address
    portal_hostname: str       # canonical hostname; used for CORS + link generation
    support_email: str         # shown in footer / "contact" links
    extras: dict[str, str]     # free-form per-tenant settings
```

## Portal + email consumption

- **Next.js portal** (`portal/student/`) — loads the brand server-side in
  a root layout and injects it into the React tree via context. Logos,
  colors, display name all flow from `request.state.brand`.
- **Email templates** — every outbound email (magic-link, consulting
  intake notifications, etc.) uses the resolved `BrandConfig` for From
  name, From address, and visual branding in the HTML body.
- **Agent invocations** — `request.state.tenant_id` flows into every
  `wfdos_common.agent.process()` call via `metadata={"tenant_id": ...}`,
  so agent responses can reference the tenant by name naturally.

## Unknown hostnames

Any request with a `Host` not in the registry (e.g. a health check from
the load balancer itself, or a typo in DNS) falls through to the
flagship default instead of erroring. This matches the "no breaking
changes" invariant: misconfigured DNS shouldn't nuke traffic, and the
structured log `tenancy.unknown_tenant` surfaces the misfire for ops to
investigate.

## Testing new tenants locally

```python
from wfdos_common.tenancy import BrandConfig, register_brand, reset_brands

# Restore defaults (in tests — autouse fixture handles this).
reset_brands()

# Add a test tenant.
register_brand(
    BrandConfig(
        tenant_id="acme",
        display_name="Acme Workforce",
        logo_url="https://example.com/logo.svg",
        primary_color="#000000",
        accent_color="#ffffff",
        email_from_name="Acme",
        email_from_address="hr@acme.example.com",
        portal_hostname="talent.acme.example.com",
    )
)
```

The TestClient can then send `Host: talent.acme.example.com` and the
middleware resolves to `"acme"`.

## Migration path: env → DB

Today the brand registry is hardcoded in
`wfdos_common/tenancy.py:_DEFAULT_BRANDS`. Two deployments in, it moves
to a `tenants` table in the shared-infra DB:

```sql
CREATE TABLE tenants (
  tenant_id         TEXT PRIMARY KEY,
  display_name      TEXT NOT NULL,
  logo_url          TEXT NOT NULL,
  primary_color     TEXT NOT NULL,
  accent_color      TEXT NOT NULL,
  email_from_name   TEXT NOT NULL,
  email_from_address TEXT NOT NULL,
  portal_hostname   TEXT NOT NULL UNIQUE,
  support_email     TEXT NOT NULL,
  extras            JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```

The `resolve_tenant()` + `get_brand()` APIs don't change; what changes
is the inner loader (startup populates the registry from the DB + a
`LISTEN` channel picks up per-row updates).
