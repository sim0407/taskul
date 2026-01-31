"""get_milestones(project_id) - list milestones of a project."""
import json
import click
from ..db import get_connection, ensure_schema, get_milestones


@click.command("get-milestones")
@click.argument("project_id")
@click.option("--json-output", "json_output", is_flag=True, default=None, help="Output as JSON")
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None, help="SQLite DB path")
def get_milestones_cmd(project_id: str, json_output: bool | None, db_path: str | None):
    """List milestones of a project (by start_date)."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        ms = get_milestones(conn, project_id)
    finally:
        conn.close()
    if ms is None:
        click.echo("Project not found.", err=True)
        raise SystemExit(1)
    if json_output is False:
        for m in ms:
            click.echo(f"{m['id']}  {m['title']}  {m['start_date']} .. {m['due_date']}")
    else:
        click.echo(json.dumps(ms, ensure_ascii=False))
