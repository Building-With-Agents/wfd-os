# nginx config snapshots

Source-of-truth for the production reverse proxy lives on the Azure VM, **not in this repo**.

- **VM:** `WatechProd-v2` (public IP `20.106.201.34`)
- **Live file:** `/etc/nginx/sites-available/wfd-os` (symlinked from `sites-enabled/wfd-os`)
- **Fronts:** Next.js app on `localhost:3001`
- **TLS:** Let's Encrypt via certbot, auto-renewing

## What's in this directory

`wfd-os.conf` — snapshot of the live config. Captured 2026-04-15 after the
`computingforall.thewaifinder.com` → `platform.thewaifinder.com` migration.

This is a **review artifact**, not a deploy artifact. Nothing reads these files
on the VM. Do not edit and expect the VM to pick it up.

## Workflow

When the VM's nginx config changes:

1. Make the change on the VM (test with `sudo nginx -t`, reload with
   `sudo systemctl reload nginx`).
2. Dump the current config and commit it here:
   ```bash
   ssh azwatechadmin@20.106.201.34 'sudo cat /etc/nginx/sites-available/wfd-os' \
     > infra/nginx/wfd-os.conf
   ```
3. Open a PR with the diff so the change is reviewable and the git log
   documents when/why hostnames, certs, or proxy settings changed.

## Recovering from a bad edit on the VM

The sed commands used during the April 2026 migration created `.bak` files next
to the live config on the VM:

- `/etc/nginx/sites-available/wfd-os.bak` — pre-migration state
  (computingforall only)
- `/etc/nginx/sites-available/wfd-os.bak2` — intermediate state
  (both hostnames)

These aren't cleaned up automatically. Roll back with `sudo cp wfd-os.bak
wfd-os && sudo nginx -t && sudo systemctl reload nginx` if needed.
