"""update_milestone(milestone_id, fields...) - extension."""
import json
import click
from ..db import get_connection, ensure_schema, update_milestone as db_update_milestone
from ..events import record_event


def update_milestone_impl(
    conn,
    milestone_id: str,
    *,
    title: str | None = None,
    start_date: str | None = None,
    due_date: str | None = None,
) -> dict:
    m = db_update_milestone(conn, milestone_id, title=title, start_date=start_date, due_date=due_date)
    record_event(conn, "human", "MILESTONE_UPDATED", {"milestone_id": milestone_id})
    conn.commit()
    return m


@click.command("update-milestone")
@click.argument("milestone_id")
@click.option("--title", default=None, help="New title")
@click.option("--start-date", default=None, help="Start date YYYY-MM-DD")
@click.option("--due-date", default=None, help="Due date YYYY-MM-DD")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def update_milestone(
    milestone_id: str,
    title: str | None,
    start_date: str | None,
    due_date: str | None,
    json_output: bool | None,
    db_path: str | None,
):
    """Update a milestone. Only provided options are updated. start_date <= due_date."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        m = update_milestone_impl(conn, milestone_id, title=title, start_date=start_date, due_date=due_date)
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is False:
        click.echo(f"Updated milestone {m['id']}: {m['title']} ({m['start_date']} .. {m['due_date']})")
    else:
        click.echo(json.dumps(m, ensure_ascii=False))
