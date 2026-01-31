"""move_task(task_id, status, rank_position) - MVP command."""
import json
import click
from ..db import get_connection, ensure_schema, get_task, row_to_task
from ..events import record_event

STATUSES = ("Backlog", "Todo", "Doing", "Review", "Done")


def move_task_impl(
    conn,
    task_id: str,
    status: str,
    position: str,
) -> dict:
    """position: top | bottom | after:T-xxxxxx"""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}")
    task = get_task(conn, task_id)
    if task is None:
        raise ValueError(f"task not found: {task_id}")

    project_id = task["project_id"]
    old_status = task["status"]
    old_rank = task["rank"]

    if position == "top":
        # Insert at rank 0: shift all in same status >= 0 by +1
        conn.execute(
            "UPDATE tasks SET rank = rank + 1 WHERE project_id = ? AND status = ? AND rank >= 0",
            (project_id, status),
        )
        new_rank = 0
    elif position == "bottom":
        cur = conn.execute(
            "SELECT COALESCE(MAX(rank), -1) + 1 FROM tasks WHERE project_id = ? AND status = ?",
            (project_id, status),
        )
        max_rank_plus_one = cur.fetchone()[0]
        # If moving within same lane to bottom, new rank is current max (we're already in list)
        if old_status == status:
            new_rank = max_rank_plus_one - 1
        else:
            new_rank = max_rank_plus_one
    elif position.startswith("after:"):
        after_id = position[6:].strip()
        cur = conn.execute("SELECT rank FROM tasks WHERE id = ? AND project_id = ?", (after_id, project_id))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"task not found or wrong project: {after_id}")
        after_rank = row[0]
        # Insert after after_rank: shift tasks with rank > after_rank by +1
        conn.execute(
            "UPDATE tasks SET rank = rank + 1 WHERE project_id = ? AND status = ? AND rank > ?",
            (project_id, status, after_rank),
        )
        new_rank = after_rank + 1
    else:
        raise ValueError("position must be top, bottom, or after:T-xxxxxx")

    # First move the task to new (status, rank) to avoid UNIQUE violation in old lane
    conn.execute(
        "UPDATE tasks SET status = ?, rank = ? WHERE id = ?",
        (status, new_rank, task_id),
    )
    # Then remove gap in old lane (decrement ranks above old_rank)
    if old_status == status and old_rank != new_rank:
        conn.execute(
            "UPDATE tasks SET rank = rank - 1 WHERE project_id = ? AND status = ? AND rank > ?",
            (project_id, old_status, old_rank),
        )
    elif old_status != status:
        conn.execute(
            "UPDATE tasks SET rank = rank - 1 WHERE project_id = ? AND status = ? AND rank > ?",
            (project_id, old_status, old_rank),
        )
    record_event(conn, "human", "TASK_MOVED", {"task_id": task_id, "status": status, "rank": new_rank})
    conn.commit()

    cur = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
    return row_to_task(cur.fetchone())


@click.command("move-task")
@click.argument("task_id")
@click.argument("status", type=click.Choice(STATUSES))
@click.option("--position", "position", default="bottom", show_default=True,
              help="Placement: top, bottom, or after:T-xxxxxx")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def move_task(task_id: str, status: str, position: str, json_output: bool | None, db_path: str | None):
    """Move a task to a status lane and optional position (top, bottom, or after:T-xxxxxx)."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        task = move_task_impl(conn, task_id, status, position)
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is False:
        click.echo(f"Moved task {task['id']} to {task['status']} (rank {task['rank']})")
    else:
        click.echo(json.dumps(task, ensure_ascii=False))
