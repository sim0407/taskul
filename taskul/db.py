"""DB connection, schema init, and ID generation."""
import os
import sqlite3
from pathlib import Path

DEFAULT_DB_PATH = os.environ.get("TASKUL_DB", str(Path.home() / ".taskul" / "taskul.db"))

_SCHEMA_SQL_PATH = Path(__file__).resolve().parent.parent / "schema" / "init.sql"


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    sql = _SCHEMA_SQL_PATH.read_text(encoding="utf-8")
    conn.executescript(sql)
    conn.commit()


def ensure_schema(conn: sqlite3.Connection) -> None:
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='projects'"
    )
    if cur.fetchone() is None:
        init_schema(conn)


def next_id(conn: sqlite3.Connection, prefix: str) -> str:
    """Generate next id like T-000001 or P-0001. Caller must commit."""
    cur = conn.execute(
        "SELECT next_value FROM id_sequences WHERE prefix = ?", (prefix,)
    )
    row = cur.fetchone()
    if not row:
        conn.execute(
            "INSERT INTO id_sequences (prefix, next_value) VALUES (?, 1)", (prefix,)
        )
        next_val = 1
    else:
        next_val = row[0]
    conn.execute(
        "UPDATE id_sequences SET next_value = next_value + 1 WHERE prefix = ?",
        (prefix,),
    )
    width = 6 if prefix == "T" else 4
    return f"{prefix}-{next_val:0{width}d}"
