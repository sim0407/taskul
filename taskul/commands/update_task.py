"""update_task(task_id, fields...) - MVP command."""
import json
import click
from ..db import get_connection, ensure_schema, get_task, row_to_task

STATUSES = ("Backlog", "Todo", "Doing", "Review", "Done")


def update_task_impl(
    conn,
    task_id: str,
    *,
    title: str | None = None,
    description: str | None = None,
    status: str | None = None,
    start_date: str | None = None,
    due_date: str | None = None,
    estimate_hours: float | None = None,
) -> dict:
    task = get_task(conn, task_id)
    if task is None:
        raise ValueError(f"task not found: {task_id}")

    updates = []
    params = []
    if title is not None:
        updates.append("title = ?")
        params.append(title)
    if description is not None:
        updates.append("description = ?")
        params.append(description)
    if start_date is not None:
        updates.append("start_date = ?")
        params.append(start_date)
    if due_date is not None:
        updates.append("due_date = ?")
        params.append(due_date)
    if estimate_hours is not None:
        updates.append("estimate_hours = ?")
        params.append(estimate_hours)

    if status is not None:
        if status not in STATUSES:
            raise ValueError(f"status must be one of {STATUSES}")
        updates.append("status = ?")
        params.append(status)
        # Move to new lane: assign new rank at bottom of new status
        cur = conn.execute(
            "SELECT COALESCE(MAX(rank), -1) + 1 AS next_rank FROM tasks WHERE project_id = ? AND status = ?",
            (task["project_id"], status),
        )
        new_rank = cur.fetchone()[0]
        updates.append("rank = ?")
        params.append(new_rank)

    if not updates:
        return task

    params.append(task_id)
    conn.execute(
        "UPDATE tasks SET " + ", ".join(updates) + " WHERE id = ?",
        params,
    )
    # After moving task to new lane, remove gap in old lane (only when status changed)
    if status is not None:
        conn.execute(
            "UPDATE tasks SET rank = rank - 1 WHERE project_id = ? AND status = ? AND rank > ?",
            (task["project_id"], task["status"], task["rank"]),
        )
    payload = json.dumps({"task_id": task_id})
    conn.execute(
        "INSERT INTO events (actor, type, payload) VALUES (?, ?, ?)",
        ("human", "TASK_UPDATED", payload),
    )
    conn.commit()

    cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    return row_to_task(cur.fetchone())


@click.command("update-task")
@click.argument("task_id")
@click.option("--title", default=None, help="New title")
@click.option("--description", default=None, help="New description")
@click.option("--status", default=None, type=click.Choice(STATUSES), help="New status")
@click.option("--start-date", default=None, help="Start date YYYY-MM-DD")
@click.option("--due-date", default=None, help="Due date YYYY-MM-DD")
@click.option("--estimate-hours", default=None, type=float, help="Estimate hours")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def update_task(
    task_id: str,
    title: str | None,
    description: str | None,
    status: str | None,
    start_date: str | None,
    due_date: str | None,
    estimate_hours: float | None,
    json_output: bool | None,
    db_path: str | None,
):
    """Update a task's fields. Only provided options are updated."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        task = update_task_impl(
            conn,
            task_id,
            title=title,
            description=description,
            status=status,
            start_date=start_date,
            due_date=due_date,
            estimate_hours=estimate_hours,
        )
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is False:
        click.echo(f"Updated task {task['id']}: {task['title']} ({task['status']})")
    else:
        click.echo(json.dumps(task, ensure_ascii=False))
