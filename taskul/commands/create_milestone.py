"""create_milestone(project_id, title, start_date, due_date) - extension."""
import json
import click
from ..db import get_connection, ensure_schema, create_milestone as db_create_milestone
from ..events import record_event


def create_milestone_impl(
    conn,
    project_id: str,
    title: str,
    start_date: str,
    due_date: str,
) -> dict:
    m = db_create_milestone(conn, project_id, title, start_date, due_date)
    record_event(conn, "human", "MILESTONE_CREATED", {"milestone_id": m["id"], "project_id": project_id})
    conn.commit()
    return m


@click.command("create-milestone")
@click.argument("project_id")
@click.argument("title")
@click.argument("start_date", metavar="START_DATE")
@click.argument("due_date", metavar="DUE_DATE")
@click.option("--json-output", "json_output", is_flag=True, default=None, help="Output as JSON")
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None, help="SQLite DB path")
def create_milestone(project_id: str, title: str, start_date: str, due_date: str, json_output: bool | None, db_path: str | None):
    """Create a milestone. START_DATE and DUE_DATE are YYYY-MM-DD (start_date <= due_date)."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        m = create_milestone_impl(conn, project_id, title, start_date, due_date)
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is False:
        click.echo(f"Created milestone {m['id']}: {m['title']} ({m['start_date']} .. {m['due_date']})")
    else:
        click.echo(json.dumps(m, ensure_ascii=False))
