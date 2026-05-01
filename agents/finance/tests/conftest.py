"""Pytest config for agents/finance.

The finance services don't currently bind to a live database for the
units exercised here (label rendering, verdict construction, FastAPI
auth wiring). Anything that does need DB access goes through
wfdos_common.testing fixtures, which the project-root pyproject points
pytest at via the wfdos-common testing plugin.
"""
from __future__ import annotations
