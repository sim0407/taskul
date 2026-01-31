"""create_task(project_id, title, status=Backlog) - MVP command."""
import json
import click
from ..db import get_connection, ensure_schema, next_id, row_to_task, get_milestone, get_task, recalc_parent_status
from ..events import record_event
STATUSES = ("Backlog", "Todo", "Doing", "Review", "Done")

# Sentinel value for unspecified optional arguments
_UNSET = object()


def create_task_impl(
    conn,
    project_id: str,
    title: str,
    status: str | None = _UNSET,
    milestone_id: str | None = _UNSET,
    parent_task_id: str | None = None,
    start_date: str | None = _UNSET,
    due_date: str | None = _UNSET,
) -> dict:
    cur = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if cur.fetchone() is None:
        raise ValueError(f"project not found: {project_id}")

    # If parent_task_id is specified, inherit defaults from parent
    depth = 0
    parent = None
    if parent_task_id:
        parent = get_task(conn, parent_task_id)
        if parent is None:
            raise ValueError(f"parent task not found: {parent_task_id}")
        if parent["project_id"] != project_id:
            raise ValueError("parent task must belong to the same project")
        depth = parent.get("depth", 0) + 1

    # Resolve values: use explicit value, or inherit from parent, or use default
    if status is _UNSET:
        status = parent["status"] if parent else "Backlog"
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")

    if milestone_id is _UNSET:
        milestone_id = parent["milestone_id"] if parent else None

    if start_date is _UNSET:
        start_date = parent["start_date"] if parent else None

    if due_date is _UNSET:
        due_date = parent["due_date"] if parent else None

    # Validate milestone if specified
    if milestone_id:
        m = get_milestone(conn, milestone_id)
        if m is None:
            raise ValueError(f"milestone not found: {milestone_id}")
        if m["project_id"] != project_id:
            raise ValueError("milestone must belong to the same project")

    task_id = next_id(conn, "T")
    conn.execute(
        """
        INSERT INTO tasks (id, project_id, title, description, status, start_date, due_date, estimate_hours, milestone_id, parent_task_id, depth)
        VALUES (?, ?, ?, NULL, ?, ?, ?, NULL, ?, ?, ?)
        """,
        (task_id, project_id, title, status, start_date, due_date, milestone_id, parent_task_id, depth),
    )
    record_event(conn, "human", "TASK_CREATED", {"task_id": task_id, "project_id": project_id, "title": title, "status": status})

    # Recalculate parent status if this is a subtask
    if parent_task_id:
        recalc_parent_status(conn, parent_task_id)

    conn.commit()

    cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    return row_to_task(cur.fetchone())


@click.command("create-task")
@click.argument("project_id")
@click.argument("title")
@click.option("--status", default=None, help="Task status (default: Backlog, or inherit from parent)")
@click.option("--milestone-id", "milestone_id", default=None, help="Milestone id (optional, inherit from parent if not specified)")
@click.option("--parent-task-id", "parent_task_id", default=None, help="Parent task id for subtask (optional)")
@click.option("--start-date", "start_date", default=None, help="Start date YYYY-MM-DD (optional, inherit from parent if not specified)")
@click.option("--due-date", "due_date", default=None, help="Due date YYYY-MM-DD (optional, inherit from parent if not specified)")
@click.option("--json-output", "json_output", is_flag=True, default=None, help="Output as JSON")
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None, help="SQLite DB path")
def create_task(project_id: str, title: str, status: str | None, milestone_id: str | None, parent_task_id: str | None, start_date: str | None, due_date: str | None, json_output: bool | None, db_path: str | None):
    """Create a new task in a project. status defaults to Backlog (or inherits from parent if subtask)."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        task = create_task_impl(
            conn,
            project_id,
            title,
            status=status if status is not None else _UNSET,
            milestone_id=milestone_id if milestone_id is not None else _UNSET,
            parent_task_id=parent_task_id,
            start_date=start_date if start_date is not None else _UNSET,
            due_date=due_date if due_date is not None else _UNSET,
        )
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is False:
        click.echo(f"Created task {task['id']}: {task['title']} ({task['status']})")
    else:
        click.echo(json.dumps(task, ensure_ascii=False))
