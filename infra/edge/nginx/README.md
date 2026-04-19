# `infra/edge/nginx/` — multi-tenant edge proxy (#30)

The config that replaces the single-tenant `infra/nginx/wfd-os.conf`
once #30 lands on the production VM.

## What changed vs. the old config

| | `infra/nginx/wfd-os.conf` (pre-#30) | `infra/edge/nginx/wfdos-platform.conf` (this dir) |
|---|---|---|
| Hostnames | `platform.thewaifinder.com` only | Multi-tenant (flagship + Borderplex; extensible via `map`) |
| Tenant routing | Service reads `Host` header directly | Nginx `map` → `X-Tenant-Id` → upstream reads via `TenantResolutionMiddleware` (#16) |
| API surface | Single port (3001 Next.js) | 10 upstreams (portal + 9 FastAPI services) |
| Rate limiting | None | `limit_req_zone` per zone (default / login / api) |
| Security headers | Partial | HSTS, X-Content-Type-Options, X-Frame-Options, Referrer-Policy |

## Why a new filename

A new file path (`infra/edge/nginx/wfdos-platform.conf` and
`sites-available/wfdos-platform` on the VM) keeps the old single-tenant
config alive for fast rollback. The deployment runbook inside the conf
file walks through the upgrade.

## Dependencies

- #16 white-label: `TenantResolutionMiddleware` reads `X-Tenant-Id`
  from the proxy.
- #22 multi-tenant DB engine: tenant_id attached to every request
  state, engine factory picks the right per-tenant pool.
- #24 auth: `/auth/login` has a stricter rate-limit zone
  (`platform_login`) to slow brute-force attempts.

## Testing locally

The conf uses absolute certbot paths that only exist on the VM. To
validate the syntax on any Linux box with nginx installed:

```bash
sudo nginx -t -c infra/edge/nginx/wfdos-platform.conf
```

This fails on the `ssl_certificate` line unless the TLS cert paths
exist — expected. The CI check uses a mocked TLS cert (see
`packages/wfdos-common/tests/test_nginx_config.py`) to validate
everything except the cert paths.
