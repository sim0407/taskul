"""get_board(project_id) - MVP query."""
import json
import click
from ..db import get_connection, ensure_schema, get_board as db_get_board


@click.command("get-board")
@click.argument("project_id")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def get_board(project_id: str, json_output: bool | None, db_path: str | None):
    """Get Kanban board (lanes by status with ordered tasks) for a project."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    board = db_get_board(conn, project_id)
    conn.close()
    if board is None:
        click.echo(f"Project not found: {project_id}", err=True)
        raise SystemExit(1)
    if json_output is False:
        for status, tasks in board["lanes"].items():
            if tasks:
                click.echo(f"  {status}: {', '.join(t['id'] for t in tasks)}")
    else:
        click.echo(json.dumps(board, ensure_ascii=False))
