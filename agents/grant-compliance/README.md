# Grant Compliance System

A grant-accounting and federal-compliance assistant that sits **on top of QuickBooks**.
It proposes grant tagging for transactions, drafts time & effort certifications,
runs 2 CFR 200 compliance checks, and generates funder-report drafts — always
with a human in the loop and a full audit trail.

> **If you're an AI assistant working on this codebase, read `CLAUDE.md` first.**

## Quickstart

```bash
# 1. Install
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# 2. Configure
cp .env.example .env
# Edit .env — at minimum set ANTHROPIC_API_KEY if you want real LLM calls.
# Leave LLM_PROVIDER=mock for offline development.

# 3. Initialize the database with seed data
python scripts/init_db.py
python scripts/seed_dev_data.py

# 4. Run the API
uvicorn grant_compliance.main:app --reload

# 5. Open the docs
open http://localhost:8000/docs
```

## What it does

| Agent | Job | Status |
|---|---|---|
| Transaction Classifier | Proposes grant/class tagging for new QB transactions | Skeleton |
| Time & Effort | Drafts monthly certifications for federal grant employees | Skeleton |
| Compliance Monitor | Flags unallowable costs, period violations, budget overruns | Rule engine ready |
| Reporting | Generates SF-425 and foundation report drafts | Skeleton |

## What it deliberately does NOT do

- Post journal entries back to QuickBooks (read-only for now)
- Auto-approve allocations or send reports to funders
- Make allowability determinations via LLM (those are coded rules)

## Architecture

```
QuickBooks Online ──► sync ──► local DB ──► agents ──► human review ──► reports
                                              │
                                              └──► audit_log (append-only)
```

See `CLAUDE.md` for principles and `docs/architecture.md` (TBD) for diagrams.

## Project layout

```
src/grant_compliance/   Application code
tests/                   Pytest suite
scripts/                 One-off scripts (init_db, seed)
alembic/                 DB migrations
```

## Before Step 1

Step 1 of the QB ingestion migration begins the first real OAuth flow against
an Intuit sandbox. Before it runs, the following four human prerequisites
must be true. None of them can be verified from code — confirm each yourself
before triggering Step 1.

### 1. Redirect URI is registered at developer.intuit.com

The Intuit developer app created for this scaffold must have
`http://localhost:8000/qb/callback` registered **character-for-character** as
an authorized redirect URI. If it doesn't match, the OAuth callback fails.

How to confirm:
- Log in at https://developer.intuit.com/app/developer/myapps
- Open the app → Keys & credentials → Sandbox → Redirect URIs
- Verify `http://localhost:8000/qb/callback` appears in the list

### 2. A sandbox company exists

An Intuit sandbox company must have been created so there's something to
authorize the OAuth flow against. A fresh developer account starts with no
sandbox companies.

How to confirm:
- https://developer.intuit.com/app/developer/sandbox
- Verify at least one sandbox company is listed
- Note its Realm ID (Company ID) — you do NOT set this in `.env`; it's
  captured from the OAuth callback by `quickbooks/oauth.py`

### 3. Authorize the OAuth flow as a Master Admin / Company Admin user

**Important correction from an earlier draft of this doc:** a low-privilege
"read-only" QB user CANNOT authorize the OAuth flow. QuickBooks Online
restricts third-party app authorization to Master Admin or Company Admin
users. Additionally, the token's capabilities come from the app's
requested scope (`com.intuit.quickbooks.accounting`, which is read+write —
Intuit offers no read-only variant), NOT from the authorizing user's role.
So the OAuth flow must be completed as an admin user, and the resulting
token is full read+write on the Intuit side regardless of who authorized.

**Where read-only enforcement actually comes from:**
- Primary: `_ReadOnlyHttpxClient` in `quickbooks/client.py` — raises
  `NotImplementedError` for any non-GET request. See CLAUDE.md
  "Enforced constraints" for the three-layer defense model.
- Post-hoc: Intuit's own audit log, which records the app + user + time
  + endpoint for every API call. Useful for forensics, not prevention.

How to complete this step:
- Sign in to the sandbox company as an admin user
- Run the OAuth flow (see step 4 below for the env chain); approve the
  app's access to the sandbox company
- The Intuit callback returns a token our server persists in
  `grant_compliance.qb_oauth_tokens`

### 4. The scaffold can load QB credentials from the env chain

`src/grant_compliance/config.py` reads from wfd-os's root `.env` first,
then this scaffold's `.env`. Confirm that `QB_CLIENT_ID` and
`QB_CLIENT_SECRET` are actually loadable by the scaffold's config
machinery:

```bash
cd agents/grant-compliance
./.venv/Scripts/python.exe -c "from grant_compliance.config import get_settings; s = get_settings(); print('client_id set:', bool(s.qb_client_id), '| secret set:', bool(s.qb_client_secret), '| env:', s.qb_environment)"
```

Expected output:
```
client_id set: True | secret set: True | env: sandbox
```

If either value is `False`, the `.env` chain isn't picking up wfd-os's root
`.env`, or the values aren't present there.

---

Once all four prerequisites are true, Step 1 can begin. Do not start Step 1
before all four are confirmed — a failure during OAuth is much harder to
debug than a failure here.

## Regulatory references

- 2 CFR 200 — Uniform Guidance: https://www.ecfr.gov/current/title-2/subtitle-A/chapter-II/part-200
- SF-425 (Federal Financial Report): https://www.grants.gov/forms/sf-424-family
