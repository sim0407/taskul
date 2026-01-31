"""list_blockers(project_id) - MVP query."""
import json
import click
from ..db import get_connection, ensure_schema, list_blockers as db_list_blockers


@click.command("list-blockers")
@click.argument("project_id")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def list_blockers(project_id: str, json_output: bool | None, db_path: str | None):
    """List tasks that are blocked (have unfinished dependencies) in a project."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    result = db_list_blockers(conn, project_id)
    conn.close()
    if result is None:
        click.echo(f"Project not found: {project_id}", err=True)
        raise SystemExit(1)
    if json_output is False:
        for t in result:
            click.echo(f"  {t['id']}: {t['title']} (blocked by {t['blocked_by']})")
    else:
        click.echo(json.dumps(result, ensure_ascii=False))
