"""get_events - List events (audit log)."""
import json
import click
from ..db import get_connection, ensure_schema, get_events as db_get_events


@click.command("get-events")
@click.option("--project-id", "project_id", default=None, help="Filter by project (payload.project_id or task in project)")
@click.option("--type", "event_type", default=None, help="Filter by event type (e.g. TASK_CREATED)")
@click.option("--limit", default=50, type=int, show_default=True, help="Max number of events (newest first)")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def get_events(
    project_id: str | None,
    event_type: str | None,
    limit: int,
    json_output: bool | None,
    db_path: str | None,
):
    """List events (audit log). Newest first. Optional filters: --project-id, --type."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    events = db_get_events(conn, limit=limit, event_type=event_type, project_id=project_id)
    conn.close()
    if json_output is False:
        for e in events:
            click.echo(f"  {e['ts']} [{e['actor']}] {e['type']} {e.get('payload', {})}")
    else:
        click.echo(json.dumps(events, ensure_ascii=False))
