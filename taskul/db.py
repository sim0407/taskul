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


def row_to_task(row) -> dict:
    """Convert a tasks table row to a task dict (for JSON / API)."""
    if row is None:
        return None
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "title": row["title"],
        "description": row["description"] or None,
        "status": row["status"],
        "rank": row["rank"],
        "start_date": row["start_date"] or None,
        "due_date": row["due_date"] or None,
        "estimate_hours": row["estimate_hours"] if row["estimate_hours"] is not None else None,
        "created_at": row["created_at"],
    }


def get_task(conn: sqlite3.Connection, task_id: str) -> dict | None:
    """Get a single task by id. Returns None if not found."""
    cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cur.fetchone()
    return row_to_task(row)


def get_board(conn: sqlite3.Connection, project_id: str) -> dict | None:
    """
    Get Kanban board: lanes by status with tasks ordered by rank.
    Returns None if project does not exist.
    """
    cur = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if cur.fetchone() is None:
        return None
    statuses = ("Backlog", "Todo", "Doing", "Review", "Done")
    lanes = {}
    for status in statuses:
        cur = conn.execute(
            "SELECT * FROM tasks WHERE project_id = ? AND status = ? ORDER BY rank",
            (project_id, status),
        )
        lanes[status] = [row_to_task(row) for row in cur.fetchall()]
    return {"project_id": project_id, "lanes": lanes}


def get_gantt(
    conn: sqlite3.Connection,
    project_id: str,
    from_date: str | None = None,
    to_date: str | None = None,
) -> list:
    """
    Get tasks with schedule fields for Gantt. Optional date filter (YYYY-MM-DD).
    If from_date/to_date are None, returns all tasks in the project.
    """
    cur = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if cur.fetchone() is None:
        return None
    sql = """
        SELECT * FROM tasks
        WHERE project_id = ?
    """
    params = [project_id]
    if from_date:
        sql += " AND (due_date IS NULL OR due_date >= ?)"
        params.append(from_date)
    if to_date:
        sql += " AND (start_date IS NULL OR start_date <= ?)"
        params.append(to_date)
    sql += " ORDER BY start_date, rank"
    cur = conn.execute(sql, params)
    return [row_to_task(row) for row in cur.fetchall()]


def list_blockers(conn: sqlite3.Connection, project_id: str) -> list:
    """
    List tasks that are blocked (have at least one dependency whose from_task is not Done).
    Returns list of task dicts with optional 'blocked_by' list of task ids.
    """
    cur = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if cur.fetchone() is None:
        return None
    cur = conn.execute(
        """
        SELECT t.id, t.project_id, t.title, t.status, t.rank,
               d.from_task_id
        FROM tasks t
        JOIN dependencies d ON d.to_task_id = t.id
        JOIN tasks f ON f.id = d.from_task_id
        WHERE t.project_id = ? AND f.status != 'Done'
        ORDER BY t.rank
        """,
        (project_id,),
    )
    rows = cur.fetchall()
    # Group by task id, collect blocker ids
    by_id = {}
    for row in rows:
        tid = row["id"]
        if tid not in by_id:
            by_id[tid] = {
                "id": row["id"],
                "project_id": row["project_id"],
                "title": row["title"],
                "status": row["status"],
                "rank": row["rank"],
                "blocked_by": [],
            }
        by_id[tid]["blocked_by"].append(row["from_task_id"])
    return list(by_id.values())


def get_all_dependencies(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Return list of (from_task_id, to_task_id) for cycle detection."""
    cur = conn.execute("SELECT from_task_id, to_task_id FROM dependencies")
    return [(row["from_task_id"], row["to_task_id"]) for row in cur.fetchall()]
