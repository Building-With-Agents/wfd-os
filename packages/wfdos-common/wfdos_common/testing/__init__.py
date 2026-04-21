"""wfdos_common.testing — pytest plugin with shared fixtures.

STATUS: STUB — implementation lands in Building-With-Agents/wfd-os#28.

Target scope (from #28):
- Pytest plugin exported via pyproject.toml; each service opts in with
  `pytest_plugins = ["wfdos_common.testing"]` in conftest.py.
- Fixtures:
  - db_engine (tenant-aware; uses wfdos_common.db engine factory).
  - db_session (rolled back after each test).
  - llm_stub (stubs wfdos_common.llm.complete — no real API calls).
  - graph_stub (stubs wfdos_common.graph calls).
  - auth_client (FastAPI TestClient with a signed session cookie for each role).
"""
