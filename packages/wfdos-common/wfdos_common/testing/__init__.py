"""wfdos_common.testing — shared pytest fixtures for wfd-os services (#28).

Consumer services opt in by adding to their `conftest.py`::

    pytest_plugins = ["wfdos_common.testing"]

That imports the `plugin` module, which defines every fixture below.
Each fixture is conservative: no external API calls, no real DB writes,
no real LLM invocations. Fast, deterministic, CI-safe.

Available fixtures:

    wfdos_tenant_id      — str, "test-tenant" by default
    wfdos_db_engine      — SQLAlchemy Engine over sqlite in-memory
    wfdos_db_session     — Session; rolls back at teardown
    wfdos_llm_stub       — monkey-patched complete() with a spy
    wfdos_graph_stub     — monkey-patched graph + email calls
    wfdos_auth_client    — FastAPI TestClient with a fake session cookie
    reset_wfdos_logging  — ensures test doesn't leak ContextVar state

Consumer usage::

    def test_something(wfdos_db_session, wfdos_llm_stub):
        wfdos_db_session.execute(text("INSERT INTO ..."))
        response = do_thing_that_calls_llm()
        assert wfdos_llm_stub.last_call["messages"][0]["content"].startswith("...")

Fixtures prefix with `wfdos_` to avoid collisions with service-local
fixtures (which might define a `db_session` already).
"""

# Re-export every fixture from .plugin so `pytest_plugins = ["wfdos_common.testing"]`
# picks them up automatically (pytest discovers fixtures at plugin import time).
from wfdos_common.testing.plugin import *  # noqa: F401, F403
