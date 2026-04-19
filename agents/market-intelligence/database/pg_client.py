"""
PostgreSQL client for Market Intelligence Agent.
Password is never stored — prompted at runtime or passed via PG_PASSWORD env var.
Gary's rule: don't put the password in .env or pass it to an LLM.
"""
import getpass
import psycopg2

# wfdos_common.config auto-loads the repo .env via python-dotenv find_dotenv.
from wfdos_common.config import settings

_conn = None


def get_connection():
    """
    Returns a live PostgreSQL connection.
    Password is read from PG_PASSWORD env var (via settings) if set,
    otherwise prompts the user at the terminal.

    TODO(#22): this per-service connection management goes away when
    wfdos_common.db.engine.get_engine() lands — market-intelligence will
    use the shared pooled engine like every other service.
    """
    global _conn
    if _conn and not _conn.closed:
        return _conn

    # Settings fall back to .env / env vars via EnvBackend by default.
    password = settings.pg.password
    if not password:
        password = getpass.getpass(
            f"PostgreSQL password for {settings.pg.user}@{settings.pg.host}: "
        )

    _conn = psycopg2.connect(
        host=settings.pg.host,
        database=settings.pg.database,
        user=settings.pg.user,
        password=password,
        port=settings.pg.port,
        sslmode="require",
    )
    print(f"Connected to PostgreSQL: {settings.pg.database}@{settings.pg.host}")
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
