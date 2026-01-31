"""add_dependency(from_task_id, to_task_id) - MVP command."""
import json
import click
from ..db import get_connection, ensure_schema, get_task
from ..cycle_check import would_create_cycle


def add_dependency_impl(conn, from_task_id: str, to_task_id: str) -> dict:
    if from_task_id == to_task_id:
        raise ValueError("from_task_id and to_task_id must be different")
    from_task = get_task(conn, from_task_id)
    to_task = get_task(conn, to_task_id)
    if from_task is None:
        raise ValueError(f"task not found: {from_task_id}")
    if to_task is None:
        raise ValueError(f"task not found: {to_task_id}")
    if from_task["project_id"] != to_task["project_id"]:
        raise ValueError("both tasks must belong to the same project")

    if would_create_cycle(conn, from_task_id, to_task_id):
        raise ValueError("adding this dependency would create a cycle")

    cur = conn.execute(
        "SELECT 1 FROM dependencies WHERE from_task_id = ? AND to_task_id = ?",
        (from_task_id, to_task_id),
    )
    if cur.fetchone() is not None:
        raise ValueError(f"dependency already exists: {from_task_id} -> {to_task_id}")

    conn.execute(
        "INSERT INTO dependencies (from_task_id, to_task_id) VALUES (?, ?)",
        (from_task_id, to_task_id),
    )
    payload = json.dumps({"from_task_id": from_task_id, "to_task_id": to_task_id})
    conn.execute(
        "INSERT INTO events (actor, type, payload) VALUES (?, ?, ?)",
        ("human", "DEP_CREATED", payload),
    )
    conn.commit()
    return {"from_task_id": from_task_id, "to_task_id": to_task_id}


@click.command("add-dependency")
@click.argument("from_task_id")
@click.argument("to_task_id")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def add_dependency(
    from_task_id: str,
    to_task_id: str,
    json_output: bool | None,
    db_path: str | None,
):
    """Add a dependency: from_task_id blocks to_task_id. Rejects if it would create a cycle."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        dep = add_dependency_impl(conn, from_task_id, to_task_id)
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is False:
        click.echo(f"Added dependency: {dep['from_task_id']} -> {dep['to_task_id']}")
    else:
        click.echo(json.dumps(dep, ensure_ascii=False))
