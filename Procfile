# Procfile for honcho-based local dev orchestration.
#
# Usage:
#   # One-time install of every dep needed to run the stack:
#   python -m pip install -r requirements-dev.txt
#   python -m pip install -e packages/wfdos-common
#   python -m pip install -e agents/grant-compliance
#   cd portal/student && npm install && cd ../..
#
#   # Start the whole stack:
#   honcho start
#
#   # Or just specific services:
#   honcho start portal consulting-api
#
# Invocation notes:
# - FastAPI services use `uvicorn <module>:app` (module-path). Do NOT use
#   `python agents/portal/*.py` — that prepends agents/portal to sys.path,
#   which shadows Python's stdlib `email` package (agents/portal/email.py
#   has the same name). Module-path invocation from repo root avoids this.
# - aiohttp services (grant / market-intel / scoping bots) use `python -m ...`
#   for the same reason.
# - Services requiring external credentials (Graph API, BotFramework, Apollo)
#   will fail to start without them — comment out the relevant lines or run
#   selectively via `honcho start <name> <name>`.

# Next.js portal (port 3000). Proxies /api/* to Python services below.
# Pass --port explicitly because honcho auto-assigns PORT per
# process-type (base 5000 + 100×index). Without the --port flag,
# Next.js reads honcho's PORT and crashes on reserved ports like 6000
# ("reserved for x11") when portal is later in the start list. Using
# -- --port (not `PORT=3000 npm`) so the Windows cmd.exe shell parses
# correctly.
portal: cd portal/student && npm run dev -- --port 3000

# FastAPI services (Python — via uvicorn module path)
reporting-api: uvicorn agents.reporting.api:app --host 0.0.0.0 --port 8000
student-api: uvicorn agents.portal.student_api:app --host 0.0.0.0 --port 8001
showcase-api: uvicorn agents.portal.showcase_api:app --host 0.0.0.0 --port 8002
consulting-api: uvicorn agents.portal.consulting_api:app --host 0.0.0.0 --port 8003
college-api: uvicorn agents.portal.college_api:app --host 0.0.0.0 --port 8004
wji-api: uvicorn agents.portal.wji_api:app --host 0.0.0.0 --port 8007
marketing-api: uvicorn agents.marketing.api:app --host 0.0.0.0 --port 8008
assistant-api: GRANT_COMPLIANCE_API_BASE=http://127.0.0.1:8014 uvicorn agents.assistant.api:app --host 0.0.0.0 --port 8009
apollo-api: uvicorn agents.apollo.api:app --host 0.0.0.0 --port 8010
recruiting-api: uvicorn agents.job_board.api:app --host 0.0.0.0 --port 8012
cockpit-api: GRANT_COMPLIANCE_ENGINE_URL=http://127.0.0.1:8014 uvicorn agents.finance.cockpit_api:app --host 0.0.0.0 --port 8013
laborpulse-api: uvicorn agents.laborpulse.api:app --host 0.0.0.0 --port 8015

# grant-compliance is its own installable package (src/ layout, separate
# pyproject.toml). Requires `pip install -e agents/grant-compliance` first
# — the module path below resolves via that install, not via repo root.
# Port 8014 chosen to avoid 8013 (cockpit-api) and 8000 (reporting-api,
# where next.config.mjs historically pointed grant-compliance). Whenever
# this port changes, also update next.config.mjs's /api/grant-compliance/*
# rewrite destination.
grant-compliance-api: uvicorn grant_compliance.main:app --host 0.0.0.0 --port 8014

# aiohttp services (Teams bots + scoping webhook).
# These use `cd <dir> && python <file>.py` because their own imports
# assume the service-local dir is sys.path[0] (`from bot.grant_bot ...`,
# etc.). The `agents/market-intelligence/` directory has a hyphen so it
# cannot be a Python module path. #27 will standardize this with proper
# per-service packaging.
grant-bot: cd agents/grant && python api.py
market-bot: cd agents/market-intelligence && python app.py
scoping-webhook: cd agents/scoping && python api.py
