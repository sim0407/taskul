"""update_task(task_id, fields...) - MVP command."""
import json
import click
from ..db import get_connection, ensure_schema, get_task, get_milestone, row_to_task, set_task_depth_and_cascade
from ..events import record_event
from ..cycle_check import would_create_parent_cycle

STATUSES = ("Backlog", "Todo", "Doing", "Review", "Done")
_UNSET = object()  # sentinel: omit from update when not provided (e.g. from API)
_CLI_OMIT = "__OMIT__"  # CLI: default for optional --milestone-id/--parent-task-id so we don't update when not passed


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
    milestone_id: str | None = _UNSET,
    parent_task_id: str | None = _UNSET,
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

    if milestone_id is not _UNSET:
        if milestone_id:
            m = get_milestone(conn, milestone_id)
            if m is None:
                raise ValueError(f"milestone not found: {milestone_id}")
            if m["project_id"] != task["project_id"]:
                raise ValueError("milestone must belong to the same project")
        updates.append("milestone_id = ?")
        params.append(milestone_id if milestone_id else None)

    if parent_task_id is not _UNSET:
        new_depth = 0
        if parent_task_id:
            parent = get_task(conn, parent_task_id)
            if parent is None:
                raise ValueError(f"parent task not found: {parent_task_id}")
            if parent["project_id"] != task["project_id"]:
                raise ValueError("parent task must belong to the same project")
            if would_create_parent_cycle(conn, task_id, parent_task_id):
                raise ValueError("would create cycle in parent chain")
            new_depth = parent.get("depth", 0) + 1
        updates.append("parent_task_id = ?")
        params.append(parent_task_id if parent_task_id else None)
        updates.append("depth = ?")
        params.append(new_depth)

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
    # When parent changed, cascade depth to all descendants
    if parent_task_id is not _UNSET:
        cur = conn.execute("SELECT depth FROM tasks WHERE id = ?", (task_id,))
        row = cur.fetchone()
        if row is not None:
            set_task_depth_and_cascade(conn, task_id, row["depth"])
    # After moving task to new lane, remove gap in old lane (only when status changed)
    if status is not None:
        conn.execute(
            "UPDATE tasks SET rank = rank - 1 WHERE project_id = ? AND status = ? AND rank > ?",
            (task["project_id"], task["status"], task["rank"]),
        )
    record_event(conn, "human", "TASK_UPDATED", {"task_id": task_id})
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
@click.option("--milestone-id", default=_CLI_OMIT, help="Milestone id (empty string to clear)")
@click.option("--parent-task-id", default=_CLI_OMIT, help="Parent task id for subtask (empty string to clear)")
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
    milestone_id: str | None,
    parent_task_id: str | None,
    json_output: bool | None,
    db_path: str | None,
):
    """Update a task's fields. Only provided options are updated."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    milestone_id_param = _UNSET if milestone_id == _CLI_OMIT else (None if milestone_id == "" else milestone_id)
    parent_task_id_param = _UNSET if parent_task_id == _CLI_OMIT else (None if parent_task_id == "" else parent_task_id)
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
            milestone_id=milestone_id_param,
            parent_task_id=parent_task_id_param,
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
