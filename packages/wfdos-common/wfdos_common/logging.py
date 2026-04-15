"""wfdos_common.logging — structlog configuration + request-context middleware.

STATUS: STUB — implementation lands in Building-With-Agents/wfd-os#23.

Target scope (from #23):
- configure(service_name: str) — single startup call.
- ContextVars: tenant_id, user_id, request_id, service_name.
- RequestContextMiddleware for FastAPI; @request_context decorator for aiohttp.
- JSON output in prod, pretty output when LOG_FORMAT=console.

Replaces 51 files using print() and 13 bare `except:` handlers with
structured log calls at appropriate levels.
"""
