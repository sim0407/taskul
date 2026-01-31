"""get_gantt(project_id, from, to) - MVP query."""
import json
import click
from ..db import get_connection, ensure_schema, get_gantt as db_get_gantt


@click.command("get-gantt")
@click.argument("project_id")
@click.option("--from", "from_date", default=None, help="From date YYYY-MM-DD")
@click.option("--to", "to_date", default=None, help="To date YYYY-MM-DD")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def get_gantt(
    project_id: str,
    from_date: str | None,
    to_date: str | None,
    json_output: bool | None,
    db_path: str | None,
):
    """Get Gantt data (tasks with schedule fields) for a project, optionally filtered by date range."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    tasks = db_get_gantt(conn, project_id, from_date, to_date)
    conn.close()
    if tasks is None:
        click.echo(f"Project not found: {project_id}", err=True)
        raise SystemExit(1)
    if json_output is False:
        for t in tasks:
            click.echo(f"  {t['id']}: {t['title']} | {t.get('start_date') or '-'} .. {t.get('due_date') or '-'}")
    else:
        click.echo(json.dumps(tasks, ensure_ascii=False))
