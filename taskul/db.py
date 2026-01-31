"""DB connection, schema init, and ID generation."""
import os
import sqlite3
from pathlib import Path

from .date_utils import parse_date

DEFAULT_DB_PATH = os.environ.get("TASKUL_DB", str(Path.home() / ".taskul" / "taskul.db"))

_SCHEMA_SQL_PATH = Path(__file__).resolve().parent.parent / "schema" / "init.sql"
_MIGRATIONS_DIR = Path(__file__).resolve().parent.parent / "schema" / "migrations"


def get_connection(db_path: str | None = None) -> sqlite3.Connection:
    path = db_path or DEFAULT_DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    # check_same_thread=False: FastAPI runs endpoints in a threadpool, so the connection
    # created in the dependency may be used from a different thread.
    conn = sqlite3.connect(path, check_same_thread=False)
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
        return
    # Migration: milestones and task.milestone_id, parent_task_id
    cur = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='milestones'"
    )
    if cur.fetchone() is None and _MIGRATIONS_DIR.joinpath("001_milestone_subtask.sql").exists():
        migration_sql = _MIGRATIONS_DIR.joinpath("001_milestone_subtask.sql").read_text(encoding="utf-8")
        conn.executescript(migration_sql)
        conn.commit()
    # Migration: task.depth (hierarchy level from root)
    cur = conn.execute("PRAGMA table_info(tasks)")
    columns = [row[1] for row in cur.fetchall()]
    has_depth = "depth" in columns
    if not has_depth and _MIGRATIONS_DIR.joinpath("002_task_depth.sql").exists():
        migration_sql = _MIGRATIONS_DIR.joinpath("002_task_depth.sql").read_text(encoding="utf-8")
        conn.executescript(migration_sql)
        conn.commit()
    # Migration: remove rank column (order by dates instead)
    cur = conn.execute("PRAGMA table_info(tasks)")
    columns = [row[1] for row in cur.fetchall()]
    has_rank = "rank" in columns
    if has_rank and _MIGRATIONS_DIR.joinpath("003_remove_rank.sql").exists():
        migration_sql = _MIGRATIONS_DIR.joinpath("003_remove_rank.sql").read_text(encoding="utf-8")
        conn.executescript(migration_sql)
        conn.commit()


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
    if prefix == "M":
        width = 4
    return f"{prefix}-{next_val:0{width}d}"


def get_projects(conn: sqlite3.Connection) -> list[dict]:
    """List all projects (id, name)."""
    cur = conn.execute("SELECT id, name FROM projects ORDER BY id")
    return [{"id": row["id"], "name": row["name"]} for row in cur.fetchall()]


def get_project(conn: sqlite3.Connection, project_id: str) -> dict | None:
    """Get a single project by id. Returns None if not found."""
    cur = conn.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,))
    row = cur.fetchone()
    if row is None:
        return None
    return {"id": row["id"], "name": row["name"]}


def row_to_milestone(row) -> dict | None:
    """Convert a milestones table row to a milestone dict."""
    if row is None:
        return None
    return {
        "id": row["id"],
        "project_id": row["project_id"],
        "title": row["title"],
        "start_date": row["start_date"],
        "due_date": row["due_date"],
    }


def get_milestones(conn: sqlite3.Connection, project_id: str) -> list[dict] | None:
    """List milestones of a project (by start_date). Returns None if project not found."""
    cur = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if cur.fetchone() is None:
        return None
    cur = conn.execute(
        "SELECT * FROM milestones WHERE project_id = ? ORDER BY start_date, id",
        (project_id,),
    )
    return [row_to_milestone(r) for r in cur.fetchall()]


def get_milestone(conn: sqlite3.Connection, milestone_id: str) -> dict | None:
    """Get a single milestone by id. Returns None if not found."""
    cur = conn.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,))
    return row_to_milestone(cur.fetchone())


def create_milestone(
    conn: sqlite3.Connection,
    project_id: str,
    title: str,
    start_date: str,
    due_date: str,
) -> dict:
    """Create a milestone. Caller must commit. Raises ValueError on validation error."""
    start_date = parse_date(start_date)
    due_date = parse_date(due_date)
    if start_date > due_date:
        raise ValueError("start_date must be <= due_date")
    cur = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if cur.fetchone() is None:
        raise ValueError(f"project not found: {project_id}")
    mid = next_id(conn, "M")
    conn.execute(
        "INSERT INTO milestones (id, project_id, title, start_date, due_date) VALUES (?, ?, ?, ?, ?)",
        (mid, project_id, title, start_date, due_date),
    )
    return {"id": mid, "project_id": project_id, "title": title, "start_date": start_date, "due_date": due_date}


def update_milestone(
    conn: sqlite3.Connection,
    milestone_id: str,
    *,
    title: str | None = None,
    start_date: str | None = None,
    due_date: str | None = None,
) -> dict:
    """Update a milestone. Caller must commit. Returns updated milestone or raises ValueError."""
    m = get_milestone(conn, milestone_id)
    if m is None:
        raise ValueError(f"milestone not found: {milestone_id}")
    updates, params = [], []
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if start_date is not None:
        start_date = parse_date(start_date)
        updates.append("start_date = ?")
        params.append(start_date)
    if due_date is not None:
        due_date = parse_date(due_date)
        updates.append("due_date = ?")
        params.append(due_date)
    if updates:
        start = start_date if start_date is not None else m["start_date"]
        due = due_date if due_date is not None else m["due_date"]
        if start > due:
            raise ValueError("start_date must be <= due_date")
        params.append(milestone_id)
        conn.execute("UPDATE milestones SET " + ", ".join(updates) + " WHERE id = ?", params)
    cur = conn.execute("SELECT * FROM milestones WHERE id = ?", (milestone_id,))
    return row_to_milestone(cur.fetchone())


def set_task_depth_and_cascade(conn: sqlite3.Connection, task_id: str, new_depth: int) -> None:
    """Set task's depth and recursively update all descendants. Caller must commit."""
    conn.execute("UPDATE tasks SET depth = ? WHERE id = ?", (new_depth, task_id))
    cur = conn.execute("SELECT id FROM tasks WHERE parent_task_id = ?", (task_id,))
    for row in cur.fetchall():
        set_task_depth_and_cascade(conn, row["id"], new_depth + 1)


def get_task_parent_chain(conn: sqlite3.Connection, task_id: str) -> list[str]:
    """Return list of ancestor task ids (task_id's parent, grandparent, ...). Empty if no parent."""
    out = []
    cur = conn.execute("SELECT parent_task_id FROM tasks WHERE id = ?", (task_id,))
    row = cur.fetchone()
    if row is None:
        return out
    pid = row["parent_task_id"] if "parent_task_id" in row.keys() else None
    seen = {task_id}
    while pid and pid not in seen:
        seen.add(pid)
        out.append(pid)
        cur = conn.execute("SELECT parent_task_id FROM tasks WHERE id = ?", (pid,))
        row = cur.fetchone()
        pid = row["parent_task_id"] if row and "parent_task_id" in row.keys() else None
    return out


def row_to_task(row, conn: sqlite3.Connection = None) -> dict:
    """Convert a tasks table row to a task dict (for JSON / API).

    If conn is provided, calculates estimate_hours for parent tasks
    as the sum of children's estimate_hours.
    """
    if row is None:
        return None
    keys = row.keys()
    task_id = row["id"]
    estimate_hours = row["estimate_hours"] if row["estimate_hours"] is not None else None

    # If conn is provided, check if this task has children and calculate sum
    if conn is not None:
        cur = conn.execute(
            "SELECT SUM(estimate_hours) as total FROM tasks WHERE parent_task_id = ?",
            (task_id,)
        )
        sum_row = cur.fetchone()
        if sum_row and sum_row["total"] is not None:
            # Task has children with estimate_hours, use the sum
            estimate_hours = sum_row["total"]

    out = {
        "id": task_id,
        "project_id": row["project_id"],
        "title": row["title"],
        "description": row["description"] or None,
        "status": row["status"],
        "start_date": row["start_date"] or None,
        "due_date": row["due_date"] or None,
        "estimate_hours": estimate_hours,
        "created_at": row["created_at"],
    }
    if "milestone_id" in keys:
        out["milestone_id"] = row["milestone_id"] or None
    if "parent_task_id" in keys:
        out["parent_task_id"] = row["parent_task_id"] or None
    if "depth" in keys:
        out["depth"] = row["depth"] if row["depth"] is not None else 0
    return out


def get_task(conn: sqlite3.Connection, task_id: str) -> dict | None:
    """Get a single task by id. Returns None if not found."""
    cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    row = cur.fetchone()
    return row_to_task(row, conn)


def get_board(
    conn: sqlite3.Connection,
    project_id: str,
    *,
    missing_milestone: bool = False,
    missing_due_date: bool = False,
    missing_estimate: bool = False,
) -> dict | None:
    """
    Get Kanban board: lanes by status with tasks ordered by start_date, due_date, created_at.
    Returns None if project does not exist.

    Filters (if True, only show tasks missing that field):
    - missing_milestone: tasks without milestone_id
    - missing_due_date: tasks without due_date
    - missing_estimate: tasks without estimate_hours
    """
    cur = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if cur.fetchone() is None:
        return None
    statuses = ("Backlog", "Todo", "Doing", "Review", "Done")
    lanes = {}

    # Build filter conditions
    filters = []
    if missing_milestone:
        filters.append("milestone_id IS NULL")
    if missing_due_date:
        filters.append("due_date IS NULL")
    if missing_estimate:
        filters.append("estimate_hours IS NULL")
    filter_clause = " AND " + " AND ".join(filters) if filters else ""

    for status in statuses:
        cur = conn.execute(
            f"""SELECT * FROM tasks WHERE project_id = ? AND status = ?{filter_clause}
               ORDER BY start_date NULLS LAST, due_date NULLS LAST, created_at""",
            (project_id, status),
        )
        lanes[status] = [row_to_task(row, conn) for row in cur.fetchall()]
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
    sql += " ORDER BY start_date, created_at"
    cur = conn.execute(sql, params)
    return [row_to_task(row, conn) for row in cur.fetchall()]


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
        SELECT t.id, t.project_id, t.title, t.status,
               d.from_task_id
        FROM tasks t
        JOIN dependencies d ON d.to_task_id = t.id
        JOIN tasks f ON f.id = d.from_task_id
        WHERE t.project_id = ? AND f.status != 'Done'
        ORDER BY t.start_date NULLS LAST, t.due_date NULLS LAST, t.created_at
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
                "blocked_by": [],
            }
        by_id[tid]["blocked_by"].append(row["from_task_id"])
    return list(by_id.values())


def get_all_dependencies(conn: sqlite3.Connection) -> list[tuple[str, str]]:
    """Return list of (from_task_id, to_task_id) for cycle detection."""
    cur = conn.execute("SELECT from_task_id, to_task_id FROM dependencies")
    return [(row["from_task_id"], row["to_task_id"]) for row in cur.fetchall()]


def recalc_parent_status(conn: sqlite3.Connection, parent_task_id: str) -> None:
    """
    Recalculate parent task's status based on children (bottom-up).
    Rules (priority order: Doing > Todo > Review > Backlog > Done):
    - If any child is Doing → Parent Doing
    - Else if any child is Todo → Parent Todo
    - Else if any child is Review → Parent Review
    - Else if any child is Backlog → Parent Backlog
    - Else (all Done) → Parent Done
    If parent has no children, status is unchanged.
    Recursively updates ancestors.
    """
    if not parent_task_id:
        return

    # Get all direct children
    cur = conn.execute("SELECT status FROM tasks WHERE parent_task_id = ?", (parent_task_id,))
    children = cur.fetchall()

    if not children:
        # No children, don't change parent status
        return

    statuses = set(row["status"] for row in children)

    # Priority order: Doing > Todo > Review > Backlog > Done
    if "Doing" in statuses:
        new_status = "Doing"
    elif "Todo" in statuses:
        new_status = "Todo"
    elif "Review" in statuses:
        new_status = "Review"
    elif "Backlog" in statuses:
        new_status = "Backlog"
    else:
        new_status = "Done"

    # Get current parent status
    cur = conn.execute("SELECT status, parent_task_id FROM tasks WHERE id = ?", (parent_task_id,))
    row = cur.fetchone()
    if row is None:
        return

    old_status = row["status"]
    grandparent_id = row["parent_task_id"]

    # Update if changed
    if old_status != new_status:
        conn.execute("UPDATE tasks SET status = ? WHERE id = ?", (new_status, parent_task_id))
        # Recursively update grandparent
        if grandparent_id:
            recalc_parent_status(conn, grandparent_id)


def get_project_delete_check(conn: sqlite3.Connection, project_id: str) -> dict | None:
    """Check what would be deleted if this project is deleted. Returns None if project not found."""
    cur = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if cur.fetchone() is None:
        return None
    cur = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE project_id = ?", (project_id,))
    task_count = cur.fetchone()["cnt"]
    cur = conn.execute("SELECT COUNT(*) as cnt FROM milestones WHERE project_id = ?", (project_id,))
    milestone_count = cur.fetchone()["cnt"]
    return {"task_count": task_count, "milestone_count": milestone_count}


def get_milestone_delete_check(conn: sqlite3.Connection, milestone_id: str) -> dict | None:
    """Check what would be affected if this milestone is deleted. Returns None if milestone not found."""
    cur = conn.execute("SELECT id FROM milestones WHERE id = ?", (milestone_id,))
    if cur.fetchone() is None:
        return None
    cur = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE milestone_id = ?", (milestone_id,))
    task_count = cur.fetchone()["cnt"]
    return {"task_count": task_count}


def get_task_delete_check(conn: sqlite3.Connection, task_id: str) -> dict | None:
    """Check what would be affected if this task is deleted. Returns None if task not found."""
    cur = conn.execute("SELECT id FROM tasks WHERE id = ?", (task_id,))
    if cur.fetchone() is None:
        return None
    # Count direct children
    cur = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE parent_task_id = ?", (task_id,))
    child_count = cur.fetchone()["cnt"]
    # Count all descendants recursively
    def count_descendants(tid: str) -> int:
        cur = conn.execute("SELECT id FROM tasks WHERE parent_task_id = ?", (tid,))
        children = [row["id"] for row in cur.fetchall()]
        total = len(children)
        for child_id in children:
            total += count_descendants(child_id)
        return total
    descendant_count = count_descendants(task_id)
    return {"child_count": child_count, "descendant_count": descendant_count}


def get_progress_summary(
    conn: sqlite3.Connection,
    project_id: str,
) -> dict | None:
    """
    Get progress summary for the nearest upcoming milestone.
    Returns:
    - milestone: the nearest milestone with due_date >= today (or None)
    - total_estimate_hours: sum of estimate_hours for tasks linked to that milestone
    - completed_estimate_hours: sum of estimate_hours for Review/Done tasks
    - progress_percent: percentage of completed work (by estimate_hours)
    - task_count: total number of tasks for that milestone
    - completed_task_count: number of Review/Done tasks
    """
    from datetime import date
    cur = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if cur.fetchone() is None:
        return None

    today = date.today().isoformat()

    # Find nearest milestone with due_date >= today
    cur = conn.execute(
        """SELECT * FROM milestones
           WHERE project_id = ? AND due_date >= ?
           ORDER BY due_date ASC LIMIT 1""",
        (project_id, today),
    )
    milestone_row = cur.fetchone()

    if milestone_row is None:
        # No upcoming milestone, show overall project stats
        cur = conn.execute(
            """SELECT
                COUNT(*) as task_count,
                SUM(CASE WHEN status IN ('Review', 'Done') THEN 1 ELSE 0 END) as completed_task_count,
                COALESCE(SUM(estimate_hours), 0) as total_estimate_hours,
                COALESCE(SUM(CASE WHEN status IN ('Review', 'Done') THEN estimate_hours ELSE 0 END), 0) as completed_estimate_hours
               FROM tasks WHERE project_id = ?""",
            (project_id,),
        )
        stats = cur.fetchone()
        total = stats["total_estimate_hours"] or 0
        completed = stats["completed_estimate_hours"] or 0
        progress = round(completed / total * 100, 1) if total > 0 else 0

        return {
            "milestone": None,
            "total_estimate_hours": total,
            "completed_estimate_hours": completed,
            "progress_percent": progress,
            "task_count": stats["task_count"],
            "completed_task_count": stats["completed_task_count"],
        }

    milestone = row_to_milestone(milestone_row)

    # Get task stats for this milestone
    cur = conn.execute(
        """SELECT
            COUNT(*) as task_count,
            SUM(CASE WHEN status IN ('Review', 'Done') THEN 1 ELSE 0 END) as completed_task_count,
            COALESCE(SUM(estimate_hours), 0) as total_estimate_hours,
            COALESCE(SUM(CASE WHEN status IN ('Review', 'Done') THEN estimate_hours ELSE 0 END), 0) as completed_estimate_hours
           FROM tasks WHERE project_id = ? AND milestone_id = ?""",
        (project_id, milestone["id"]),
    )
    stats = cur.fetchone()
    total = stats["total_estimate_hours"] or 0
    completed = stats["completed_estimate_hours"] or 0
    progress = round(completed / total * 100, 1) if total > 0 else 0

    return {
        "milestone": milestone,
        "total_estimate_hours": total,
        "completed_estimate_hours": completed,
        "progress_percent": progress,
        "task_count": stats["task_count"],
        "completed_task_count": stats["completed_task_count"],
    }


def get_events(
    conn: sqlite3.Connection,
    limit: int = 100,
    event_type: str | None = None,
    project_id: str | None = None,
) -> list[dict]:
    """
    List events (newest first). Optional: event_type filter, project_id filter.
    project_id filters by payload.project_id or payload.task_id in that project.
    """
    import json
    sql = "SELECT event_id, ts, actor, type, payload FROM events WHERE 1=1"
    params: list = []
    if event_type:
        sql += " AND type = ?"
        params.append(event_type)
    sql += " ORDER BY event_id DESC LIMIT ?"
    params.append(limit)
    cur = conn.execute(sql, params)
    rows = cur.fetchall()
    out = []
    task_ids_in_project: set[str] | None = None
    if project_id:
        cur2 = conn.execute("SELECT id FROM tasks WHERE project_id = ?", (project_id,))
        task_ids_in_project = {row["id"] for row in cur2.fetchall()}
    for row in rows:
        payload_raw = row["payload"] or ""
        try:
            payload = json.loads(payload_raw) if payload_raw else None
        except (json.JSONDecodeError, TypeError):
            payload = payload_raw
        if project_id and task_ids_in_project is not None:
            if not isinstance(payload, dict):
                continue
            if (payload.get("project_id") != project_id
                and payload.get("task_id") not in task_ids_in_project
                and payload.get("from_task_id") not in task_ids_in_project
                and payload.get("to_task_id") not in task_ids_in_project):
                continue
        out.append({
            "event_id": row["event_id"],
            "ts": row["ts"],
            "actor": row["actor"],
            "type": row["type"],
            "payload": payload,
        })
    return out
