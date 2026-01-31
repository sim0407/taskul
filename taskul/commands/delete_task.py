"""delete_task(task_id) - タスクを削除する。"""
import json
import click
from ..db import get_connection, ensure_schema, get_task, recalc_parent_status
from ..events import record_event


def delete_task_impl(conn, task_id: str) -> dict:
    """Delete a task and all its descendants. Returns the deleted task info."""
    task = get_task(conn, task_id)
    if task is None:
        raise ValueError(f"task not found: {task_id}")

    # Recursively delete all descendants first
    def delete_descendants(tid: str):
        cur = conn.execute("SELECT id, title FROM tasks WHERE parent_task_id = ?", (tid,))
        children = cur.fetchall()
        for child in children:
            delete_descendants(child["id"])
            conn.execute("DELETE FROM tasks WHERE id = ?", (child["id"],))
            record_event(conn, "human", "TASK_DELETED", {"task_id": child["id"], "title": child["title"], "parent_deleted": task_id})

    # Save parent before deletion
    parent_task_id = task.get("parent_task_id")

    delete_descendants(task_id)
    conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    record_event(conn, "human", "TASK_DELETED", {"task_id": task_id, "title": task["title"]})

    # Recalculate parent status after deletion
    if parent_task_id:
        recalc_parent_status(conn, parent_task_id)

    conn.commit()

    return task


@click.command("delete-task")
@click.argument("task_id")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def delete_task(task_id: str, json_output: bool | None, db_path: str | None):
    """Delete a task."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        task = delete_task_impl(conn, task_id)
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is False:
        click.echo(f"Deleted task {task['id']}: {task['title']}")
    else:
        click.echo(json.dumps(task, ensure_ascii=False))
