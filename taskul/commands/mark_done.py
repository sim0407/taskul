"""mark_done(task_id) - MVP command. Shortcut for update_task(..., status=Done)."""
import json
import click
from ..db import get_connection, ensure_schema, get_task, row_to_task


def mark_done_impl(conn, task_id: str) -> dict:
    task = get_task(conn, task_id)
    if task is None:
        raise ValueError(f"task not found: {task_id}")
    # New rank at bottom of Done lane
    cur = conn.execute(
        "SELECT COALESCE(MAX(rank), -1) + 1 FROM tasks WHERE project_id = ? AND status = ?",
        (task["project_id"], "Done"),
    )
    new_rank = cur.fetchone()[0]
    # First move task to Done to avoid UNIQUE violation in old lane
    conn.execute(
        "UPDATE tasks SET status = ?, rank = ? WHERE id = ?",
        ("Done", new_rank, task_id),
    )
    # Then decrement ranks of tasks that were after this one in the old lane
    conn.execute(
        "UPDATE tasks SET rank = rank - 1 WHERE project_id = ? AND status = ? AND rank > ?",
        (task["project_id"], task["status"], task["rank"]),
    )
    conn.execute(
        "INSERT INTO events (actor, type, payload) VALUES (?, ?, ?)",
        ("human", "TASK_UPDATED", json.dumps({"task_id": task_id, "status": "Done"})),
    )
    conn.commit()
    cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    return row_to_task(cur.fetchone())


@click.command("mark-done")
@click.argument("task_id")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def mark_done(task_id: str, json_output: bool | None, db_path: str | None):
    """Mark a task as Done."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        task = mark_done_impl(conn, task_id)
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is False:
        click.echo(f"Marked task {task['id']} as Done")
    else:
        click.echo(json.dumps(task, ensure_ascii=False))
