"""move_task(task_id, status) - タスクのステータスを変更する。"""
import json
import click
from ..db import get_connection, ensure_schema, get_task, row_to_task
from ..events import record_event

STATUSES = ("Backlog", "Todo", "Doing", "Review", "Done")


def move_task_impl(
    conn,
    task_id: str,
    status: str,
) -> dict:
    """Move a task to a new status lane."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    task = get_task(conn, task_id)
    if task is None:
        raise ValueError(f"task not found: {task_id}")

    if task["status"] == status:
        return task  # No change needed

    conn.execute(
        "UPDATE tasks SET status = ? WHERE id = ?",
        (status, task_id),
    )
    record_event(conn, "human", "TASK_MOVED", {"task_id": task_id, "status": status})
    conn.commit()

    cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    return row_to_task(cur.fetchone())


@click.command("move-task")
@click.argument("task_id")
@click.argument("status", type=click.Choice(STATUSES))
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def move_task(task_id: str, status: str, json_output: bool | None, db_path: str | None):
    """Move a task to a status lane."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        task = move_task_impl(conn, task_id, status)
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is False:
        click.echo(f"Moved task {task['id']} to {task['status']}")
    else:
        click.echo(json.dumps(task, ensure_ascii=False))
