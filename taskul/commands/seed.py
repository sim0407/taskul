"""seed - サンプルプロジェクトとその中身を一括作成するコマンド。"""
import json
from datetime import date, timedelta

import click

from ..db import get_connection, ensure_schema
from .create_project import create_project_impl
from .create_milestone import create_milestone_impl
from .create_task import create_task_impl
from .add_dependency import add_dependency_impl


def _date_str(d: date) -> str:
    return d.isoformat()


def seed_impl(conn, name: str = "サンプルプロジェクト") -> dict:
    """サンプルプロジェクトとマイルストーン・タスク・依存を一括で作成する。conn は呼び出し元で確保・コミット済み。"""
    today = date.today()
    project = create_project_impl(conn, name)
    project_id = project["id"]

    m1 = create_milestone_impl(
        conn, project_id, "Phase 1", _date_str(today), _date_str(today + timedelta(days=14))
    )
    m2 = create_milestone_impl(
        conn, project_id, "Phase 2",
        _date_str(today + timedelta(days=15)), _date_str(today + timedelta(days=45)),
    )
    m3 = create_milestone_impl(
        conn, project_id, "Release",
        _date_str(today + timedelta(days=46)), _date_str(today + timedelta(days=60)),
    )

    t1 = create_task_impl(conn, project_id, "要件定義", "Backlog", milestone_id=m1["id"])
    t2 = create_task_impl(conn, project_id, "設計", "Todo", milestone_id=m1["id"])
    t3 = create_task_impl(conn, project_id, "実装", "Doing", milestone_id=m2["id"])
    t4 = create_task_impl(conn, project_id, "結合テスト", "Backlog", milestone_id=m2["id"])
    t5 = create_task_impl(conn, project_id, "リリース準備", "Backlog", milestone_id=m3["id"])

    t1a = create_task_impl(conn, project_id, "ヒアリング", "Backlog", milestone_id=m1["id"], parent_task_id=t1["id"])
    t1b = create_task_impl(conn, project_id, "要件書作成", "Backlog", milestone_id=m1["id"], parent_task_id=t1["id"])
    t2a = create_task_impl(conn, project_id, "アーキテクチャ設計", "Backlog", milestone_id=m1["id"], parent_task_id=t2["id"])
    t2b = create_task_impl(conn, project_id, "詳細設計", "Backlog", milestone_id=m1["id"], parent_task_id=t2["id"])
    t3a = create_task_impl(conn, project_id, "単体テスト", "Backlog", milestone_id=m2["id"], parent_task_id=t3["id"])
    t3b = create_task_impl(conn, project_id, "コードレビュー", "Backlog", milestone_id=m2["id"], parent_task_id=t3["id"])
    t4a = create_task_impl(conn, project_id, "テスト実行・バグ修正", "Backlog", milestone_id=m2["id"], parent_task_id=t4["id"])
    t5a = create_task_impl(conn, project_id, "デプロイ", "Backlog", milestone_id=m3["id"], parent_task_id=t5["id"])

    all_tasks = [t1, t1a, t1b, t2, t2a, t2b, t3, t3a, t3b, t4, t4a, t5, t5a]

    add_dependency_impl(conn, t1["id"], t2["id"])
    add_dependency_impl(conn, t2["id"], t3["id"])
    add_dependency_impl(conn, t3["id"], t3a["id"])
    add_dependency_impl(conn, t3["id"], t4["id"])
    add_dependency_impl(conn, t4["id"], t5["id"])

    return {
        "project": project,
        "milestones": [m1, m2, m3],
        "tasks": all_tasks,
        "dependencies": [
            {"from_task_id": t1["id"], "to_task_id": t2["id"]},
            {"from_task_id": t2["id"], "to_task_id": t3["id"]},
            {"from_task_id": t3["id"], "to_task_id": t3a["id"]},
            {"from_task_id": t3["id"], "to_task_id": t4["id"]},
            {"from_task_id": t4["id"], "to_task_id": t5["id"]},
        ],
    }


@click.command("seed")
@click.option("--name", default="サンプルプロジェクト", help="プロジェクト名")
@click.option("--json-output", "json_output", is_flag=True, default=None, help="Output as JSON")
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None, help="SQLite DB path")
def seed(name: str, json_output: bool | None, db_path: str | None):
    """サンプルプロジェクトとマイルストーン・タスク・依存を一括で作成する。"""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        summary = seed_impl(conn, name)
        project_id = summary["project"]["id"]
        m1, m2, m3 = summary["milestones"]
    except ValueError as e:
        click.echo(str(e), err=True)
        raise SystemExit(1)
    finally:
        conn.close()

    if json_output is True:
        click.echo(json.dumps(summary, ensure_ascii=False))
    else:
        click.echo(f"Created project {project_id}: {name}")
        click.echo(f"  Milestones: {m1['id']}, {m2['id']}, {m3['id']}")
        click.echo(f"  Tasks: 親5 + 子8 = 13 tasks")
        click.echo("  Dependencies: 要件定義→設計→実装→(単体テスト/結合テスト)→リリース準備")
