"""mark_done(task_id) - MVP command. Shortcut for update_task(..., status=Done)."""
import json
import click
from ..db import get_connection, ensure_schema, get_task, row_to_task, recalc_parent_status
from ..events import record_event


def mark_done_impl(conn, task_id: str) -> dict:
    task = get_task(conn, task_id)
    if task is None:
        raise ValueError(f"task not found: {task_id}")

    if task["status"] == "Done":
        return task  # Already done

    # Check if task has children - if so, status is auto-calculated
    cur = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE parent_task_id = ?", (task_id,))
    if cur.fetchone()["cnt"] > 0:
        raise ValueError("子タスクを持つタスクのステータスは自動計算されるため、直接変更できません")

    conn.execute(
        "UPDATE tasks SET status = ? WHERE id = ?",
        ("Done", task_id),
    )
    record_event(conn, "human", "TASK_UPDATED", {"task_id": task_id, "status": "Done"})

    # Recalculate parent status (bottom-up)
    parent_task_id = task.get("parent_task_id")
    if parent_task_id:
        recalc_parent_status(conn, parent_task_id)

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
