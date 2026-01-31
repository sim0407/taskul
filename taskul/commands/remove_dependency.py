"""remove_dependency(from_task_id, to_task_id) - MVP command."""
import json
import click
from ..db import get_connection, ensure_schema
from ..events import record_event


def remove_dependency_impl(conn, from_task_id: str, to_task_id: str) -> dict | None:
    cur = conn.execute(
        "SELECT 1 FROM dependencies WHERE from_task_id = ? AND to_task_id = ?",
        (from_task_id, to_task_id),
    )
    if cur.fetchone() is None:
        return None
    conn.execute(
        "DELETE FROM dependencies WHERE from_task_id = ? AND to_task_id = ?",
        (from_task_id, to_task_id),
    )
    record_event(conn, "human", "DEP_REMOVED", {"from_task_id": from_task_id, "to_task_id": to_task_id})
    conn.commit()
    return {"from_task_id": from_task_id, "to_task_id": to_task_id}


@click.command("remove-dependency")
@click.argument("from_task_id")
@click.argument("to_task_id")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def remove_dependency(
    from_task_id: str,
    to_task_id: str,
    json_output: bool | None,
    db_path: str | None,
):
    """Remove a dependency between two tasks."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    dep = remove_dependency_impl(conn, from_task_id, to_task_id)
    conn.close()

    if dep is None:
        click.echo(f"Dependency not found: {from_task_id} -> {to_task_id}", err=True)
        raise SystemExit(1)

    if json_output is False:
        click.echo(f"Removed dependency: {dep['from_task_id']} -> {dep['to_task_id']}")
    else:
        click.echo(json.dumps(dep, ensure_ascii=False))
