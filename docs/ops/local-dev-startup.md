# Local dev startup — wfd-os stack + LaborPulse walk-through

Quickest path from a fresh clone to browsing the LaborPulse page with
mock data rendering. Captured during the 2026-04-20/21 live smoke.

**Target audience:** anyone — Windows + Git Bash is the primary env
(Gary's setup). macOS / Linux notes called out where relevant.

---

## Prerequisites

| Tool | Version | Why |
|---|---|---|
| Python | **3.11** or **3.14** | Runtime for FastAPI services + wfdos-common. CI runs 3.11. |
| Node.js | 22.x | Next.js 16 portal. `nvm use 22.11.0` if you juggle versions. |
| Docker Desktop | any recent | Hosts the JIE `postgres-server` + `langfuse-server`. Not strictly required for the LaborPulse mock-mode demo. |
| Git | any recent | |
| GPG + Kleopatra (Windows) | any recent | Every commit must be signed — `git commit -S`. |

Optional but useful:

- `gh` CLI logged in to `Building-With-Agents`
- `honcho` (pip-installed below, not required on PATH globally)
- nginx — only needed for the §10 `nginx -t` smoke, not for running the app

---

## One-time setup

```bash
# 1. Clone.
git clone git@github.com:Building-With-Agents/wfd-os.git
cd wfd-os

# 2. Install the monorepo + wfdos-common in editable mode.
#    The [dev] extra pulls numpy, anthropic, pandas, aiohttp, botbuilder-core,
#    etc. — everything every service needs.
python -m pip install -e packages/wfdos-common
python -m pip install -e '.[dev]'
python -m pip install python-multipart   # FastAPI Form() / UploadFile

# 3. Install the Next.js portal deps.
cd portal/student
npm install
cd ../..

# 4. Copy the .env.example and fill in the blanks.
cp .env.example .env
# Edit .env — at minimum set PG_*, GRAPH_*, AZURE_OPENAI_*, and:
#   WFDOS_AUTH_STAFF_ALLOWLIST=<your-email>
#   WFDOS_AUTH_WORKFORCE_DEVELOPMENT_ALLOWLIST=<your-email>
#   WFDOS_AUTH_SECRET_KEY=<python -c 'import secrets; print(secrets.token_urlsafe(48))'>
#   WFDOS_AUTH_COOKIE_SECURE=false   # required for http://localhost
```

### Windows: Python Scripts folder on PATH

`honcho` and `uvicorn` install as `.exe` shims in Python's `Scripts`
dir, which is usually **not** on PATH. Add this to your shell rc:

```bash
# Git Bash / WSL style
export PATH="/c/Users/<you>/AppData/Local/Python/pythoncore-3.14-64/Scripts:$PATH"
```

Or invoke everything via `python -m honcho` / `python -m uvicorn`.

---

## Port conflicts — check before starting

wfd-os wants:

| Port | Service |
|---|---|
| 3000 | Next.js portal |
| 8000 | reporting-api |
| 8001 | student-api |
| 8002 | showcase-api |
| 8003 | consulting-api (auth lives here) |
| 8004 | college-api |
| 8007 | wji-api |
| 8008 | marketing-api |
| 8009 | assistant-api |
| 8010 | apollo-api |
| 8012 | recruiting-api (job_board) |
| 8013 | cockpit-api (finance) |
| 8014 | grant-compliance-api |
| 8015 | laborpulse-api |

**Known conflict**: JIE's `langfuse-server` Docker container binds
`:3000` by default. If you run JIE locally:

```bash
# In the JIE repo's .env:
LANGFUSE_PORT=3001
# Then restart just the Langfuse container:
cd ../job-intelligence-engine
docker compose up -d langfuse
# Langfuse moves to http://localhost:3001; wfd-os portal takes :3000.
```

Full reconciliation plan:
`docs/database/jie-wfdos-schema-reconciliation.md`.

Quick probe:

```bash
# What's listening where
netstat -ano -p tcp | grep LISTENING | grep -E ":(3000|3001|5432|8000|8003|8012|8013|8014|8015) "
```

---

## Start the stack

```bash
# PATH fix if honcho isn't installed globally (Windows):
export PATH="/c/Users/<you>/AppData/Local/Python/pythoncore-3.14-64/Scripts:$PATH"

# The full stack — 13 FastAPI services + Next.js portal on :3000.
honcho start reporting-api student-api showcase-api consulting-api \
              college-api wji-api marketing-api assistant-api \
              apollo-api recruiting-api cockpit-api \
              grant-compliance-api laborpulse-api portal
```

Wait ~15–25s for Next.js to compile on first boot. Subsequent runs
are much faster (Next.js caches in `portal/student/.next`).

### Smoke the boot

```bash
python scripts/smoke/bootstrap/healthchecks.py
# Expect: 10/10 OK, then "OK: every /api/health responded (n=10)"
```

If any service is red, tail the honcho log for that process name
(honcho multiplexes stdout) and check `agents/<svc>/api.py`'s import
chain for missing deps.

---

## LaborPulse walk-through

### Path A — click a real magic link (closest to production)

```bash
# Fire the login
python scripts/smoke/auth/login.py <your-allowlisted-email>
# Expect: "OK: /auth/login accepted <email>"
```

Check your inbox for **"Your Waifinder sign-in link"** (sender is
currently `ritu@computingforall.org` until the `no-reply@thewaifinder.com`
mailbox is provisioned — see the spawned-task chip from 2026-04-20).

Click the link within 15 minutes. The URL is
`http://localhost:3000/auth/verify?token=<urlencoded-token>` — Next.js
proxies `/auth/*` to consulting-api on :8003, which verifies and
drops the `wfdos_session` cookie.

Then navigate to `http://localhost:3000/laborpulse`.

### Path B — synthesize a cookie directly (fastest for demo / CI)

Skips the email round-trip. Useful when Graph is down or you're in
the middle of debugging.

```bash
python -c "
import pathlib
env = pathlib.Path('.env').read_text()
key = next(l.split('=',1)[1].strip() for l in env.splitlines() if l.startswith('WFDOS_AUTH_SECRET_KEY='))
from wfdos_common.auth.tokens import issue_magic_link
import urllib.parse
tok = issue_magic_link('<your-allowlisted-email>', secret_key=key)
print(f'http://localhost:3000/auth/verify?token={urllib.parse.quote(tok, safe=\"\")}')
"
```

Paste the printed URL into your browser. Same effect as clicking the
real email link.

### On the /laborpulse page

1. You'll see the "LaborPulse" heading with a Q&A input.
2. Type any workforce-dev question — the placeholder is
   "Which sectors gained the most postings in Doña Ana in Q1?".
3. Click **Ask**. The input clears, the "Ask" button dims, and the
   page enters the 8–12s mock-synthesis wait (no visible loader
   today — the shimmering border is the only cue).
4. After ~10s, the answer renders:
   - `[MOCK]` prefix on the answer text
   - `confidence: mock` badge next to ANSWER
   - 3 evidence cards (`lightcast_postings_2026Q1`,
     `bls_oes_nm_doña_ana`, `cfa_skills_registry`)
   - 3 follow-up chips (clicking them re-fires a query)
   - 👍 / 👎 thumbs buttons (write to `qa_feedback` — **currently
     errors** until schema reconciliation lands; see Part 4 of
     `docs/laborpulse-backend-handoff.md`).

### Flipping to real JIE data

Once the JIE team delivers `POST /analytics/query` (see
`docs/laborpulse-backend-handoff.md` Part 2):

```bash
# In wfd-os .env:
JIE_BASE_URL=https://jie-dev.thewaifinder.com
JIE_API_KEY=<shared-secret>

# Restart laborpulse-api so it picks up the env:
# (taskkill the :8012 pid on Windows, then honcho respawns it
#  — or easier, Ctrl-C honcho and re-run)
```

`/api/health` on :8012 will report `jie_configured=true`. The answer
won't have `[MOCK]`; `confidence` will be `low` / `medium` / `high`;
wall-clock will depend on JIE synthesis (typically 15–45s).

---

## Stopping the stack

- Foreground honcho: `Ctrl-C` once, wait for graceful shutdown.
- Orphaned uvicorn processes after `Ctrl-C` (common on Windows):

```bash
for port in 8000 8001 8002 8003 8004 8007 8008 8009 8010 8012 3000; do
  pid=$(netstat -ano -p tcp 2>/dev/null | grep ":$port " | grep LISTENING | awk '{print $NF}' | head -1)
  [ -n "$pid" ] && taskkill //F //PID "$pid" > /dev/null 2>&1 && echo "killed $port/$pid"
done
```

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `'uvicorn' is not recognized` on Windows | Python Scripts dir not on PATH | `export PATH=".../Python/.../Scripts:$PATH"` or use `python -m uvicorn` |
| `Bad port: "6000" is reserved for x11` | honcho auto-assigns `PORT=6000` to portal when it's the 11th process | The committed Procfile passes `--port 3000` — if you see this, you're running a stale Procfile |
| `/auth/verify` returns 404 in browser | Next.js `/auth/*` rewrite missing OR portal compiled before the config change | Restart portal (`honcho start portal`); verify `portal/student/next.config.mjs` has the `/auth/:path*` rule |
| Cookie set but not sent to services | `WFDOS_AUTH_COOKIE_SECURE=true` + http://localhost | Set `WFDOS_AUTH_COOKIE_SECURE=false` in `.env`, restart services |
| Magic-link email URL has `token=%7B` only | Pre-`35b51ef` token-encoding bug | Pull latest `development`; the fix is committed |
| Portal on 3001 / 3002 / 6000 | `:3000` occupied by another process (usually Langfuse) | Free :3000 (see "Port conflicts" above) |
| LaborPulse "error: Something went wrong" instantly | Portal `/api/laborpulse/*` rewrite missing (pre-`9f2ff2f`) | Pull latest `development` |
| LaborPulse 401 on `/api/laborpulse/query` | No session cookie | Use Path A or B above |
| 312/312 tests locally but CI red | Env differences (USER / PATH) | Pull the latest `.github/workflows/ci.yml` from `development` (post-#69) |

---

## Related docs

- `docs/refactor/phase-5-exit-report.md` — full smoke checklist + current pass/defer state
- `docs/laborpulse.md` — LaborPulse architecture + role model + qa_feedback schema
- `docs/laborpulse-backend-handoff.md` — JIE team contract + chat-widget evolution + entitlement plan
- `docs/database/jie-wfdos-schema-reconciliation.md` — shared-Postgres plan + port-3000 fix + flatten `dbo.*` → `public.*` recommendation
- `Procfile` — the authoritative service list + startup commands
