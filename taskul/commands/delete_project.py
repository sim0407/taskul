"""delete_project(project_id) - プロジェクトを削除する（タスク・マイルストーンも削除）。"""
import json
import click
from ..db import get_connection, ensure_schema, get_project
from ..events import record_event


def delete_project_impl(conn, project_id: str) -> dict:
    """Delete a project and all its tasks/milestones. Returns the deleted project info."""
    project = get_project(conn, project_id)
    if project is None:
        raise ValueError(f"project not found: {project_id}")

    # CASCADE will delete tasks and milestones
    conn.execute("DELETE FROM projects WHERE id = ?", (project_id,))
    record_event(conn, "human", "PROJECT_DELETED", {"project_id": project_id, "name": project["name"]})
    conn.commit()

    return project


@click.command("delete-project")
@click.argument("project_id")
@click.option("--json-output", "json_output", is_flag=True, default=None)
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None)
def delete_project(project_id: str, json_output: bool | None, db_path: str | None):
    """Delete a project and all its tasks/milestones."""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        project = delete_project_impl(conn, project_id)
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is False:
        click.echo(f"Deleted project {project['id']}: {project['name']}")
    else:
        click.echo(json.dumps(project, ensure_ascii=False))
