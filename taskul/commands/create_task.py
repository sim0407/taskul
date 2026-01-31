"""create_task(project_id, title, status=Backlog) - MVP command."""
import json
import click
from ..db import get_connection, ensure_schema, next_id, row_to_task, get_milestone, get_task
from ..events import record_event
STATUSES = ("Backlog", "Todo", "Doing", "Review", "Done")


def create_task_impl(
    conn,
    project_id: str,
    title: str,
    status: str = "Backlog",
    milestone_id: str | None = None,
    parent_task_id: str | None = None,
) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    cur = conn.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
    if cur.fetchone() is None:
        raise ValueError(f"project not found: {project_id}")

    if milestone_id:
        m = get_milestone(conn, milestone_id)
        if m is None:
            raise ValueError(f"milestone not found: {milestone_id}")
        if m["project_id"] != project_id:
            raise ValueError("milestone must belong to the same project")

    if parent_task_id:
        parent = get_task(conn, parent_task_id)
        if parent is None:
            raise ValueError(f"parent task not found: {parent_task_id}")
        if parent["project_id"] != project_id:
            raise ValueError("parent task must belong to the same project")

    cur = conn.execute(
        "SELECT COALESCE(MAX(rank), -1) + 1 AS next_rank FROM tasks WHERE project_id = ? AND status = ?",
        (project_id, status),
    )
    rank = cur.fetchone()[0]

    task_id = next_id(conn, "T")
    conn.execute(
        """
        INSERT INTO tasks (id, project_id, title, description, status, rank, start_date, due_date, estimate_hours, milestone_id, parent_task_id)
        VALUES (?, ?, ?, NULL, ?, ?, NULL, NULL, NULL, ?, ?)
        """,
        (task_id, project_id, title, status, rank, milestone_id, parent_task_id),
    )
    record_event(conn, "human", "TASK_CREATED", {"task_id": task_id, "project_id": project_id, "title": title, "status": status})
    conn.commit()

    cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    return row_to_task(cur.fetchone())


@click.command("create-task")
@click.argument("project_id")
@click.argument("title")
@click.option("--status", default="Backlog", show_default=True, help="Task status")
@click.option("--milestone-id", "milestone_id", default=None, help="Milestone id (optional)")
@click.option("--parent-task-id", "parent_task_id", default=None, help="Parent task id for subtask (optional)")
@click.option("--json-output", "json_output", is_flag=True, default=None, help="Output as JSON")
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None, help="SQLite DB path")
def create_task(project_id: str, title: str, status: str, milestone_id: str | None, parent_task_id: str | None, json_output: bool | None, db_path: str | None):
    """Create a new task in a project. status defaults to Backlog."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        task = create_task_impl(conn, project_id, title, status, milestone_id=milestone_id, parent_task_id=parent_task_id)
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is False:
        click.echo(f"Created task {task['id']}: {task['title']} ({task['status']})")
    else:
        click.echo(json.dumps(task, ensure_ascii=False))
