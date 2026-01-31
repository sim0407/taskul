"""import-tasks - CSV/Excel/XMLからタスクを一括インポートするコマンド。"""
import csv
import json
import xml.etree.ElementTree as ET
from pathlib import Path

import click

from ..db import get_connection, ensure_schema
from .create_task import create_task_impl, _UNSET

STATUSES = ("Backlog", "Todo", "Doing", "Review", "Done")


def _normalize_status(status: str | None) -> str:
    """ステータス文字列を正規化。None や空文字は Backlog に。"""
    if not status or not status.strip():
        return "Backlog"
    s = status.strip()
    # 大文字小文字を無視してマッチ
    for valid in STATUSES:
        if s.lower() == valid.lower():
            return valid
    return s  # 無効な場合はそのまま返し、create_task_impl でエラーにする


def _parse_csv(file_path: Path) -> list[dict]:
    """CSVファイルをパースしてタスクのリストを返す。"""
    tasks = []
    with open(file_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            task = {
                "title": row.get("title", "").strip(),
                "status": _normalize_status(row.get("status")),
                "description": row.get("description", "").strip() or None,
                "start_date": row.get("start_date", "").strip() or None,
                "due_date": row.get("due_date", "").strip() or None,
                "milestone_id": row.get("milestone_id", "").strip() or None,
                "parent_task_id": row.get("parent_task_id", "").strip() or None,
            }
            if task["title"]:
                tasks.append(task)
    return tasks


def _parse_excel(file_path: Path) -> list[dict]:
    """Excelファイルをパースしてタスクのリストを返す。"""
    try:
        import openpyxl
    except ImportError:
        raise ValueError("Excel読み込みには openpyxl が必要です: pip install openpyxl")

    wb = openpyxl.load_workbook(file_path, read_only=True, data_only=True)
    ws = wb.active
    tasks = []

    rows = list(ws.iter_rows(values_only=True))
    if not rows:
        return tasks

    # ヘッダー行を取得
    header = [str(c).strip().lower() if c else "" for c in rows[0]]
    col_map = {name: idx for idx, name in enumerate(header) if name}

    def get_val(row, col_name):
        idx = col_map.get(col_name)
        if idx is None or idx >= len(row):
            return None
        val = row[idx]
        if val is None:
            return None
        return str(val).strip()

    for row in rows[1:]:
        title = get_val(row, "title")
        if not title:
            continue
        task = {
            "title": title,
            "status": _normalize_status(get_val(row, "status")),
            "description": get_val(row, "description") or None,
            "start_date": get_val(row, "start_date") or None,
            "due_date": get_val(row, "due_date") or None,
            "milestone_id": get_val(row, "milestone_id") or None,
            "parent_task_id": get_val(row, "parent_task_id") or None,
        }
        tasks.append(task)

    wb.close()
    return tasks


def _parse_xml(file_path: Path) -> list[dict]:
    """XMLファイルをパースしてタスクのリストを返す。"""
    tree = ET.parse(file_path)
    root = tree.getroot()
    tasks = []

    for task_elem in root.findall(".//task"):
        title = task_elem.findtext("title", "").strip()
        if not title:
            continue
        task = {
            "title": title,
            "status": _normalize_status(task_elem.findtext("status")),
            "description": (task_elem.findtext("description") or "").strip() or None,
            "start_date": (task_elem.findtext("start_date") or "").strip() or None,
            "due_date": (task_elem.findtext("due_date") or "").strip() or None,
            "milestone_id": (task_elem.findtext("milestone_id") or "").strip() or None,
            "parent_task_id": (task_elem.findtext("parent_task_id") or "").strip() or None,
        }
        tasks.append(task)

    return tasks


def import_tasks_impl(conn, project_id: str, file_path: str) -> dict:
    """ファイルからタスクをインポートする。"""
    path = Path(file_path)
    if not path.exists():
        raise ValueError(f"ファイルが見つかりません: {file_path}")

    ext = path.suffix.lower()
    if ext == ".csv":
        tasks_data = _parse_csv(path)
    elif ext in (".xlsx", ".xls"):
        tasks_data = _parse_excel(path)
    elif ext == ".xml":
        tasks_data = _parse_xml(path)
    else:
        raise ValueError(f"未対応のファイル形式です: {ext} (対応: .csv, .xlsx, .xml)")

    if not tasks_data:
        raise ValueError("インポートするタスクがありません")

    created = []
    errors = []

    for i, task_data in enumerate(tasks_data, start=1):
        try:
            task = create_task_impl(
                conn,
                project_id,
                task_data["title"],
                status=task_data["status"],
                milestone_id=task_data["milestone_id"] if task_data["milestone_id"] else _UNSET,
                parent_task_id=task_data["parent_task_id"],
                start_date=task_data["start_date"] if task_data["start_date"] else _UNSET,
                due_date=task_data["due_date"] if task_data["due_date"] else _UNSET,
            )
            created.append(task)
        except ValueError as e:
            errors.append({"row": i, "title": task_data["title"], "error": str(e)})

    return {
        "project_id": project_id,
        "file": str(path),
        "imported": len(created),
        "errors": len(errors),
        "tasks": created,
        "error_details": errors,
    }


@click.command("import-tasks")
@click.argument("project_id")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--json-output", "json_output", is_flag=True, default=None, help="Output as JSON")
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None, help="SQLite DB path")
def import_tasks(project_id: str, file_path: str, json_output: bool | None, db_path: str | None):
    """CSV/Excel/XMLファイルからタスクを一括インポートする。

    対応フォーマット: .csv, .xlsx, .xml

    必須カラム: title

    オプションカラム: status, description, start_date, due_date, milestone_id, parent_task_id
    """
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        result = import_tasks_impl(conn, project_id, file_path)
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is True:
        click.echo(json.dumps(result, ensure_ascii=False))
    else:
        click.echo(f"Imported {result['imported']} tasks into {project_id}")
        if result["errors"]:
            click.echo(f"  Errors: {result['errors']}")
            for err in result["error_details"]:
                click.echo(f"    Row {err['row']}: {err['title']} - {err['error']}")
