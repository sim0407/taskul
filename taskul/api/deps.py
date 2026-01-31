"""FastAPI dependencies (DB connection)."""
import sqlite3
from collections.abc import Generator

from ..db import get_connection, ensure_schema


def get_db() -> Generator[sqlite3.Connection, None, None]:
    """Yield a DB connection per request. Ensures schema. Closes on exit."""
    conn = get_connection()
    ensure_schema(conn)
    try:
        yield conn
    finally:
        conn.close()
