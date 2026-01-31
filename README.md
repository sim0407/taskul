# taskul

シングルユーザー向けローカルタスク管理ツール（MVP）。Kanban + Gantt を想定し、**エージェント連携を前提**とした CLI と JSON 出力を提供します。

## 特徴

- **CLI 駆動**: すべての操作をコマンドラインから実行可能
- **JSON 出力**: `--json-output` で機械可読な出力（エージェント・スクリプト連携向け）
- **SQLite**: 単一ユーザー・ローカル前提で DB は `~/.taskul/taskul.db`（変更可）

## 技術スタック

| 項目 | 採用 |
|------|------|
| 言語 | Python 3 |
| CLI | Click（サブコマンド・オプション） |
| DB | SQLite |
| スキーマ | `schema/init.sql`（初回利用時に自動適用） |

## ディレクトリ構成

```
taskul/
├── SPEC.md              # 仕様（MVP エンティティ・クエリ・コマンド）
├── REPO_STRUCTURE.md    # リポジトリ構成・方針
├── README.md            # 本ドキュメント
├── requirements.txt     # Python 依存（Click）
├── schema/
│   └── init.sql         # SQLite DDL
└── taskul/
    ├── __init__.py
    ├── __main__.py      # python -m taskul のエントリ
    ├── cli.py           # CLI エントリポイント
    ├── db.py            # DB 接続・スキーマ適用・ID 採番
    └── commands/
        ├── create_project.py
        └── create_task.py
```

## セットアップ

```bash
# 仮想環境
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 依存インストール
pip install -r requirements.txt
```

## 使い方

DB は初回コマンド実行時に自動作成され、`schema/init.sql` が適用されます。デフォルトのパスは `~/.taskul/taskul.db` です。別パスにする場合は環境変数 `TASKUL_DB` またはオプション `--db` を指定してください。

### プロジェクトを作成

```bash
python -m taskul create-project "My Project"
# → Created project P-0001: My Project

python -m taskul create-project "My Project" --json-output
# → {"id":"P-0001","name":"My Project"}
```

### タスクを作成

```bash
python -m taskul create-task P-0001 "最初のタスク"
# ステータスはデフォルトで Backlog

python -m taskul create-task P-0001 "着手するタスク" --status Todo
python -m taskul create-task P-0001 "作業中" --status Doing --json-output
# → 作成したタスクの JSON（id, project_id, title, status, rank など）
```

利用可能なステータス: `Backlog`, `Todo`, `Doing`, `Review`, `Done`

## 環境変数・オプション

| 項目 | 説明 |
|------|------|
| `TASKUL_DB` | SQLite DB ファイルのパス（未指定時は `~/.taskul/taskul.db`） |
| `--db` | 上記と同じ（コマンドごとに指定可能） |
| `--json-output` | 出力を JSON にする（全コマンドで利用可能） |

## ドキュメント

- [SPEC.md](SPEC.md) … エンティティ（Project / Task / Dependency / Event）、MVP クエリ・コマンド、制約
- [REPO_STRUCTURE.md](REPO_STRUCTURE.md) … ディレクトリ方針、Git 管理、今後の拡張案

## 今後の拡張（予定）

- 読み取り: `get_board`, `get_gantt`, `get_task`, `list_blockers`
- 書き込み: `update_task`, `move_task`, `add_dependency`, `remove_dependency`, `mark_done`
- HTTP API（FastAPI 等）、サイクル検出、イベント共通処理など

## ライセンス

MIT License。詳細は [LICENSE](LICENSE) を参照してください。
