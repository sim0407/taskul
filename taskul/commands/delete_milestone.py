"""delete_milestone(milestone_id) - マイルストーンを削除する。"""
import json
import click
from ..db import get_connection, ensure_schema, get_milestone
from ..events import record_event


def delete_milestone_impl(conn, milestone_id: str) -> dict:
    """Delete a milestone. Returns the deleted milestone info."""
    milestone = get_milestone(conn, milestone_id)
    if milestone is None:
        raise ValueError(f"milestone not found: {milestone_id}")

    conn.execute("DELETE FROM milestones WHERE id = ?", (milestone_id,))
    record_event(conn, "human", "MILESTONE_DELETED", {"milestone_id": milestone_id, "title": milestone["title"]})
    conn.commit()

    return milestone


@click.command("delete-milestone")
@click.argument("milestone_id")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def delete_milestone(milestone_id: str, json_output: bool | None, db_path: str | None):
    """Delete a milestone."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        milestone = delete_milestone_impl(conn, milestone_id)
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is False:
        click.echo(f"Deleted milestone {milestone['id']}: {milestone['title']}")
    else:
        click.echo(json.dumps(milestone, ensure_ascii=False))
