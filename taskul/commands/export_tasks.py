"""export-tasks - プロジェクトのタスクをCSV/XMLにエクスポートするコマンド。"""
import csv
import json
import xml.etree.ElementTree as ET
from io import StringIO
from pathlib import Path

import click

from ..db import get_connection, ensure_schema, get_project, get_board, get_milestones

STATUSES = ("Backlog", "Todo", "Doing", "Review", "Done")


def export_tasks_impl(conn, project_id: str, format: str = "csv") -> str:
    """プロジェクトのタスクをエクスポートする。"""
    project = get_project(conn, project_id)
    if project is None:
        raise ValueError(f"project not found: {project_id}")

    board = get_board(conn, project_id)
    if board is None:
        raise ValueError(f"project not found: {project_id}")

    # Flatten all tasks from lanes
    tasks = []
    for status in STATUSES:
        tasks.extend(board["lanes"].get(status, []))

    if format == "csv":
        return _export_csv(tasks)
    elif format == "xml":
        return _export_xml(project, tasks, get_milestones(conn, project_id) or [])
    else:
        raise ValueError(f"Unsupported format: {format}. Use 'csv' or 'xml'.")


def _export_csv(tasks: list[dict]) -> str:
    """タスクをCSV形式でエクスポートする。"""
    output = StringIO()
    fieldnames = [
        "id", "title", "description", "status",
        "start_date", "due_date", "estimate_hours",
        "milestone_id", "parent_task_id", "depth"
    ]
    writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
    writer.writeheader()
    for task in tasks:
        writer.writerow(task)
    return output.getvalue()


def _export_xml(project: dict, tasks: list[dict], milestones: list[dict]) -> str:
    """プロジェクトをXML形式でエクスポートする。"""
    root = ET.Element("project")
    root.set("id", project["id"])
    root.set("name", project["name"])

    # Milestones section
    milestones_elem = ET.SubElement(root, "milestones")
    for m in milestones:
        ms_elem = ET.SubElement(milestones_elem, "milestone")
        ms_elem.set("id", m["id"])
        ET.SubElement(ms_elem, "title").text = m["title"]
        ET.SubElement(ms_elem, "start_date").text = m["start_date"] or ""
        ET.SubElement(ms_elem, "due_date").text = m["due_date"] or ""

    # Tasks section
    tasks_elem = ET.SubElement(root, "tasks")
    for task in tasks:
        task_elem = ET.SubElement(tasks_elem, "task")
        task_elem.set("id", task["id"])
        ET.SubElement(task_elem, "title").text = task["title"]
        ET.SubElement(task_elem, "description").text = task.get("description") or ""
        ET.SubElement(task_elem, "status").text = task["status"]
        ET.SubElement(task_elem, "start_date").text = task.get("start_date") or ""
        ET.SubElement(task_elem, "due_date").text = task.get("due_date") or ""
        ET.SubElement(task_elem, "estimate_hours").text = str(task.get("estimate_hours") or "")
        ET.SubElement(task_elem, "milestone_id").text = task.get("milestone_id") or ""
        ET.SubElement(task_elem, "parent_task_id").text = task.get("parent_task_id") or ""
        ET.SubElement(task_elem, "depth").text = str(task.get("depth", 0))

    # Pretty print
    ET.indent(root, space="  ")
    return ET.tostring(root, encoding="unicode", xml_declaration=True)


@click.command("export-tasks")
@click.argument("project_id")
@click.option("--format", "fmt", type=click.Choice(["csv", "xml"]), default="csv", help="Export format")
@click.option("--output", "-o", "output_path", type=click.Path(), default=None, help="Output file path")
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None, help="SQLite DB path")
def export_tasks(project_id: str, fmt: str, output_path: str | None, db_path: str | None):
    """プロジェクトのタスクをCSV/XMLファイルにエクスポートする。

    --output を指定しない場合は標準出力に出力する。
    """
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        content = export_tasks_impl(conn, project_id, fmt)
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if output_path:
        Path(output_path).write_text(content, encoding="utf-8")
        click.echo(f"Exported to {output_path}")
    else:
        click.echo(content)
