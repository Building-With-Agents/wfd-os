"""Create all database tables. Dev use only — production uses Alembic."""

from __future__ import annotations

from grant_compliance.db.session import init_db

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
