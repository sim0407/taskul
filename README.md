# taskul

シングルユーザー向けローカルタスク管理ツール（MVP）。Kanban + Gantt を想定し、**エージェント連携を前提**とした CLI と JSON 出力を提供します。

## 特徴

- **CLI 駆動**: すべての操作をコマンドラインから実行可能
- **HTTP API**: FastAPI で REST API を提供（`taskul serve` で起動、`/docs` で Swagger UI）
- **JSON 出力**: `--json-output` で機械可読な出力（エージェント・スクリプト連携向け）
- **SQLite**: 単一ユーザー・ローカル前提で DB は `~/.taskul/taskul.db`（変更可）

## 技術スタック

| 項目 | 採用 |
|------|------|
| 言語 | Python 3 |
| CLI | Click（サブコマンド・オプション） |
| API | FastAPI + uvicorn |
| DB | SQLite |
| スキーマ | `schema/init.sql`（初回利用時に自動適用） |

## ディレクトリ構成

```
taskul/
├── SPEC.md              # 仕様（MVP エンティティ・クエリ・コマンド）
├── REPO_STRUCTURE.md    # リポジトリ構成・方針
├── README.md            # 本ドキュメント
├── requirements.txt     # Python 依存（Click, FastAPI, uvicorn）
├── schema/
│   └── init.sql         # SQLite DDL
└── taskul/
    ├── __init__.py
    ├── __main__.py      # python3 -m taskul のエントリ
    ├── api/             # HTTP API（FastAPI）
    │   ├── app.py
    │   ├── deps.py
    │   └── routes/
    │       ├── projects.py
    │       ├── tasks.py
    │       └── dependencies.py
    ├── cli.py           # CLI エントリポイント
    ├── db.py            # DB 接続・スキーマ適用・ID 採番
    ├── cycle_check.py   # 依存サイクル検出
    └── commands/
        ├── create_project.py, create_task.py, serve.py, ...
        └── get_board.py, get_gantt.py, get_task.py, list_blockers.py, ...
```

## セットアップ

```bash
# 仮想環境
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 依存インストール
pip install -r requirements.txt
```

## 使い方

DB は初回コマンド実行時に自動作成され、`schema/init.sql` が適用されます。デフォルトのパスは `~/.taskul/taskul.db` です。別パスにする場合は環境変数 `TASKUL_DB` またはオプション `--db` を指定してください。

### プロジェクトを作成

```bash
python3 -m taskul create-project "My Project"
# → Created project P-0001: My Project

python3 -m taskul create-project "My Project" --json-output
# → {"id":"P-0001","name":"My Project"}
```

### タスクを作成

```bash
python3 -m taskul create-task P-0001 "最初のタスク"
# ステータスはデフォルトで Backlog

python3 -m taskul create-task P-0001 "着手するタスク" --status Todo
python3 -m taskul create-task P-0001 "作業中" --status Doing --json-output
# → 作成したタスクの JSON（id, project_id, title, status, rank など）
```

利用可能なステータス: `Backlog`, `Todo`, `Doing`, `Review`, `Done`

### 読み取り（Phase 1）

```bash
# ボード取得（ステータス別レーン＋タスク順）
python3 -m taskul get-board P-0001
# JSON: python3 -m taskul get-board P-0001 --json-output

# Gantt 用データ（期間指定可）
python3 -m taskul get-gantt P-0001
# 期間指定: python3 -m taskul get-gantt P-0001 --from YYYY-MM-DD --to YYYY-MM-DD
# JSON: 上記の末尾に --json-output

# 単一タスク取得
python3 -m taskul get-task T-000001
# JSON: python3 -m taskul get-task T-000001 --json-output

# ブロックされているタスク一覧
python3 -m taskul list-blockers P-0001
# JSON: python3 -m taskul list-blockers P-0001 --json-output
```

### 更新・移動・依存（Phase 1）

```bash
# タスク更新（指定した項目のみ更新）
python3 -m taskul update-task T-000001 --title "新タイトル" --status Todo
# JSON: 末尾に --json-output

# タスク移動（top / bottom / after:T-xxxxxx）
python3 -m taskul move-task T-000001 Todo --position top

# 依存追加（サイクルになる場合は拒否）
python3 -m taskul add-dependency T-000001 T-000002

# 依存削除
python3 -m taskul remove-dependency T-000001 T-000002

# 完了にする
python3 -m taskul mark-done T-000001
```

### HTTP API（Phase 1）

```bash
# API サーバ起動（デフォルト http://127.0.0.1:8000）
python3 -m taskul serve
# オプション: --host 0.0.0.0 --port 8080 --db /path/to/taskul.db

# 別の方法
uvicorn taskul.api.app:app --host 127.0.0.1 --port 8000
```

起動後、**http://127.0.0.1:8000/docs** で Swagger UI を開けます。

| エンドポイント | 説明 |
|----------------|------|
| `GET /projects` | プロジェクト一覧 |
| `POST /projects` | プロジェクト作成（body: `{"name": "..."}`） |
| `GET /projects/{id}` | プロジェクト取得 |
| `GET /projects/{id}/board` | ボード取得 |
| `GET /projects/{id}/gantt` | Gantt データ（query: from_date, to_date） |
| `GET /projects/{id}/blockers` | ブロッカー一覧 |
| `GET /tasks/{id}` | タスク取得 |
| `POST /tasks` | タスク作成（body: `{"project_id","title","status"?}`） |
| `PATCH /tasks/{id}` | タスク更新（body: 任意フィールド） |
| `POST /tasks/{id}/move` | タスク移動（body: `{"status","position"?}`） |
| `POST /tasks/{id}/mark-done` | タスクを Done に |
| `POST /dependencies` | 依存追加（body: `{"from_task_id","to_task_id"}`） |
| `DELETE /dependencies?from_task_id=...&to_task_id=...` | 依存削除 |

## 環境変数・オプション

| 項目 | 説明 |
|------|------|
| `TASKUL_DB` | SQLite DB ファイルのパス（未指定時は `~/.taskul/taskul.db`） |
| `--db` | 上記と同じ（コマンドごとに指定可能） |
| `--json-output` | 出力を JSON にする（全コマンドで利用可能） |

## ドキュメント

- [SPEC.md](SPEC.md) … エンティティ（Project / Task / Dependency / Event）、MVP クエリ・コマンド、制約
- [REPO_STRUCTURE.md](REPO_STRUCTURE.md) … ディレクトリ方針、Git 管理、今後の拡張案

## 今後の拡張（4 段階）

1. **操作の充実（CLI/API）** — CLI と HTTP API は完了。
2. **状態の可視化（board / gantt / blockers）** — データ取得（get-board, get-gantt, list-blockers）は完了。表示は Phase 4 の UI で。
3. **ルールと整合性（依存・制約・履歴）** — 依存のサイクル検出・制約は完了。履歴の共通化（events.py）・履歴参照は未着手。
4. **UI（Web / TUI）** — 未着手。

詳細は [REPO_STRUCTURE.md](REPO_STRUCTURE.md) の「今後の拡張」を参照。

## ライセンス

MIT License。詳細は [LICENSE](LICENSE) を参照してください。
