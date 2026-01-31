"""create_project(name) - minimal helper so create_task can be tested."""
import json
import click
from ..db import get_connection, ensure_schema, next_id


def create_project_impl(conn, name: str) -> dict:
    project_id = next_id(conn, "P")
    conn.execute("INSERT INTO projects (id, name) VALUES (?, ?)", (project_id, name))
    conn.commit()
    cur = conn.execute("SELECT id, name FROM projects WHERE id = ?", (project_id,))
    row = cur.fetchone()
    return {"id": row["id"], "name": row["name"]}


@click.command("create-project")
@click.argument("name")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def create_project(name: str, json_output: bool | None, db_path: str | None):
    """Create a new project (helper for testing create-task)."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    project = create_project_impl(conn, name)
    conn.close()
    if json_output is False:
        click.echo(f"Created project {project['id']}: {project['name']}")
    else:
        click.echo(json.dumps(project, ensure_ascii=False))

