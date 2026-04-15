# Procfile for honcho-based local dev orchestration.
#
# Usage: `honcho start` brings up the whole stack. `honcho start student-api showcase-api`
# runs only the named processes. See docs/dev-setup.md for details.
#
# Notes:
#   - Some services require external credentials (Graph API, BotFramework, Apollo, etc.).
#     Services without valid creds will fail to start — that's expected; comment them out
#     or run selectively.
#   - Port mappings match existing uvicorn.run() / web.run_app() bindings in each service.
#     Changing any of these requires updating portal/student/next.config.mjs in the same commit.

# Next.js portal (port 3000). Proxies /api/* to Python services below.
portal: cd portal/student && npm run dev

# FastAPI services (Python)
reporting-api: python agents/reporting/api.py
student-api: python agents/portal/student_api.py
showcase-api: python agents/portal/showcase_api.py
consulting-api: python agents/portal/consulting_api.py
college-api: python agents/portal/college_api.py
wji-api: python agents/portal/wji_api.py
marketing-api: python agents/marketing/api.py
assistant-api: python agents/assistant/api.py
apollo-api: python agents/apollo/api.py

# aiohttp services (Teams bots + webhook)
grant-bot: python agents/grant/api.py
market-bot: python agents/market-intelligence/app.py
scoping-webhook: python agents/scoping/api.py
