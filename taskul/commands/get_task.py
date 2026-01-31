"""get_task(task_id) - MVP query."""
import json
import click
from ..db import get_connection, ensure_schema, get_task as db_get_task


@click.command("get-task")
@click.argument("task_id")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def get_task(task_id: str, json_output: bool | None, db_path: str | None):
    """Get a single task by id."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    task = db_get_task(conn, task_id)
    conn.close()
    if task is None:
        click.echo(f"Task not found: {task_id}", err=True)
        raise SystemExit(1)
    if json_output is False:
        click.echo(f"{task['id']}: {task['title']} [{task['status']}] (project {task['project_id']})")
    else:
        click.echo(json.dumps(task, ensure_ascii=False))
