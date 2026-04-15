"""wfdos_common.auth — magic-link auth + role-based access.

STATUS: STUB — implementation lands in Building-With-Agents/wfd-os#24.

Target scope (from #24):
- Magic-link flow using itsdangerous signed tokens + Microsoft Graph
  sendMail (via wfdos_common.email).
- FastAPI dependency `require_role(*roles)` — services import per-route.
- Tier decorators `@read_only` / `@llm_gated` (#25).
- Rate limits via slowapi: student 100/hr, staff 500/hr.

Auth lives only on platform.thewaifinder.com + client white-label hosts.
The Squarespace marketing apex has no auth surface — see #10 comment.
"""
