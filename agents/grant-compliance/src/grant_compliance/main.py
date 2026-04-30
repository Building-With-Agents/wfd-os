"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from grant_compliance.api.routes import (
    allocations,
    compliance,
    compliance_requirements,
    grants,
    qb_oauth,
    reports,
    time_effort,
    transactions,
)
from grant_compliance.config import get_settings
from grant_compliance.db.session import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()
    if settings.app_env == "development":
        # Auto-create tables in dev. In production, use Alembic migrations.
        init_db()
    yield


app = FastAPI(
    title="Grant Compliance System",
    description=(
        "Grant accounting and federal compliance assistant on top of QuickBooks. "
        "Agents propose; humans dispose. See CLAUDE.md for principles."
    ),
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(grants.router)
app.include_router(transactions.router)
app.include_router(allocations.router)
app.include_router(compliance.router)
app.include_router(compliance_requirements.router)
app.include_router(time_effort.router)
app.include_router(reports.router)
app.include_router(qb_oauth.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
