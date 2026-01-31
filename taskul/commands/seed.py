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


@click.command("seed")
@click.option("--name", default="サンプルプロジェクト", help="プロジェクト名")
@click.option("--json-output", "json_output", is_flag=True, default=None, help="Output as JSON")
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None, help="SQLite DB path")
def seed(name: str, json_output: bool | None, db_path: str | None):
    """サンプルプロジェクトとマイルストーン・タスク・依存を一括で作成する。"""
    conn = get_connection(db_path)
    ensure_schema(conn)
    try:
        today = date.today()
        # プロジェクト
        project = create_project_impl(conn, name)
        project_id = project["id"]

        # マイルストーン（Phase 1, Phase 2, Release）
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

        # タスク（ステータス・マイルストーン・サブタスクをばらす）
        t1 = create_task_impl(conn, project_id, "要件定義", "Backlog", milestone_id=m1["id"])
        t2 = create_task_impl(conn, project_id, "設計", "Todo", milestone_id=m1["id"])
        t3 = create_task_impl(conn, project_id, "実装", "Doing", milestone_id=m2["id"])
        t4 = create_task_impl(conn, project_id, "単体テスト", "Backlog", milestone_id=m2["id"], parent_task_id=t3["id"])
        t5 = create_task_impl(conn, project_id, "結合テスト", "Backlog", milestone_id=m2["id"])
        t6 = create_task_impl(conn, project_id, "リリース準備", "Backlog", milestone_id=m3["id"])

        # 依存（要件定義→設計→実装、実装→単体テスト）
        add_dependency_impl(conn, t1["id"], t2["id"])
        add_dependency_impl(conn, t2["id"], t3["id"])
        add_dependency_impl(conn, t3["id"], t4["id"])

        summary = {
            "project": project,
            "milestones": [m1, m2, m3],
            "tasks": [t1, t2, t3, t4, t5, t6],
            "dependencies": [
                {"from_task_id": t1["id"], "to_task_id": t2["id"]},
                {"from_task_id": t2["id"], "to_task_id": t3["id"]},
                {"from_task_id": t3["id"], "to_task_id": t4["id"]},
            ],
        }
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
        click.echo(f"  Tasks: {t1['id']} .. {t6['id']} (6 tasks, 1 subtask)")
        click.echo("  Dependencies: 要件定義→設計→実装→単体テスト")
