"""
PostgreSQL client for Market Intelligence Agent.
Password is never stored — prompted at runtime or passed via PG_PASSWORD env var.
Gary's rule: don't put the password in .env or pass it to an LLM.
"""
import os
import getpass
import psycopg2
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "../../../.env"), override=True)

_conn = None


def get_connection():
    """
    Returns a live PostgreSQL connection.
    Password is read from PG_PASSWORD env var if set,
    otherwise prompts the user at the terminal.
    """
    global _conn
    if _conn and not _conn.closed:
        return _conn

    host = os.getenv("PG_HOST")
    database = os.getenv("PG_DATABASE")
    user = os.getenv("PG_USER")
    port = int(os.getenv("PG_PORT", 5432))

    # Get password — env var first, then prompt
    password = os.getenv("PG_PASSWORD")
    if not password:
        password = getpass.getpass(f"PostgreSQL password for {user}@{host}: ")

    _conn = psycopg2.connect(
        host=host,
        database=database,
        user=user,
        password=password,
        port=port,
        sslmode="require",
    )
    print(f"Connected to PostgreSQL: {database}@{host}")
    return _conn


def query_pg(sql: str, params=None) -> list[dict]:
    """Run a read-only SQL query and return results as list of dicts."""
    conn = get_connection()
    with conn.cursor() as cur:
        cur.execute(sql, params or ())
        cols = [desc[0] for desc in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]


def test_connection():
    """Quick connection test — prints table list."""
    rows = query_pg("""
        SELECT table_name, pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size
        FROM information_schema.tables
        WHERE table_schema = 'public'
        ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC
        LIMIT 20
    """)
    print(f"\nConnected! Tables in talent_finder:")
    for r in rows:
        print(f"  {r['table_name']:40s} {r['size']}")


if __name__ == "__main__":
    test_connection()
