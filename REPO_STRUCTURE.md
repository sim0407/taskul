# taskul - MVP リポジトリ構成案

## ディレクトリ構成

```
taskul/
├── SPEC.md                 # 仕様（既存）
├── REPO_STRUCTURE.md       # 本ドキュメント
├── requirements.txt        # Python 依存
├── schema/
│   └── init.sql            # SQLite DDL（初回セットアップ用）
├── taskul/
│   ├── __init__.py
│   ├── db.py               # DB接続・初期化・ヘルパ
│   ├── cli.py              # CLI エントリポイント（Click）
│   └── commands/
│       ├── __init__.py
│       ├── create_task.py  # create_task コマンド
│       ├── create_project.py
│       └── ...             # 他コマンドは MVP で順次追加
└── tests/
    └── ...
```

## 方針

- **言語**: Python 3（CLI・API・JSON 出力に適している）
- **CLI**: Click（サブコマンド・引数・JSON 出力が扱いやすい）
- **DB**: SQLite（単一ユーザー・ローカル前提）
- **スキーマ**: `schema/init.sql` をアプリ起動時または専用コマンドで適用
- **コマンド**: `taskul/commands/` に1コマンド1モジュールで配置し、`cli.py` で登録

## 実行方法（想定）

```bash
# 仮想環境
python -m venv .venv
.venv\Scripts\activate # or .venv/bin/activate

# 依存
pip install -r requirements.txt

# CLI（エントリポイントは taskul.cli）
python -m taskul create-task <project_id> <title> [--status Backlog]
# または
taskul create-task P-0001 "最初のタスク"

# 試し方（create_task はプロジェクトが必要）
python -m taskul create-project "My Project" --json-output   # → {"id":"P-0001","name":"My Project"}
python -m taskul create-task P-0001 "最初のタスク" --json-output  # → 作成したタスクの JSON
# DB はデフォルトで ~/.taskul/taskul.db。別パスは TASKUL_DB または --db で指定。
```

## Git 管理方針（GitHub 公開時）

### 管理する（コミットする）ファイル

| 種類 | 例 |
|------|-----|
| 仕様・ドキュメント | `SPEC.md`, `REPO_STRUCTURE.md`, `README.md` |
| 依存定義 | `requirements.txt` |
| スキーマ | `schema/init.sql` |
| ソースコード | `taskul/**/*.py`（`__pycache__` 以外） |
| テスト | `tests/**/*.py` およびテスト用設定 |
| 設定（共有したいもの） | `pyproject.toml`, `setup.cfg` など |

### 無視する（.gitignore）ファイル・ディレクトリ

| 種類 | 例 |
|------|-----|
| 仮想環境 | `.venv/`, `venv/`, `env/` |
| Python バイトコード | `__pycache__/`, `*.pyc`, `*.pyo` |
| ビルド成果物 | `dist/`, `build/`, `*.egg-info/` |
| **DB・ユーザーデータ** | `*.db`, `*.sqlite`, `.taskul/` |
| シークレット | `.env`, `*.pem` |
| テストキャッシュ | `.pytest_cache/`, `.coverage`, `htmlcov/` |
| IDE | `.idea/`, `.vscode/`（任意） |
| OS | `.DS_Store`, `Thumbs.db` |

DB はデフォルトで `~/.taskul/taskul.db` に作成されるためリポジトリには含まれません。開発時にリポジトリ内で `taskul.db` を作成した場合も、`.gitignore` で除外されます。

## 今後の拡張

拡張は次の 4 段階の順序で進める想定です。

| 段階 | テーマ | 進捗 |
|------|--------|------|
| **1** | 操作の充実（CLI/API） | CLI・API 完了 |
| **2** | 状態の可視化（board / gantt / blockers） | データ取得完了 / 表示は Phase 4 で |
| **3** | ルールと整合性（依存・制約・履歴） | 依存・制約・履歴（共通化・参照）完了 |
| **4** | UI（Web / TUI） | Web UI 完了（表示・ブロッカー） / TUI 未着手 |

---

### 1. 操作の充実（CLI / API）

**目的**: タスク・プロジェクト・依存を操作する手段を揃える。まず CLI、続けて HTTP API。

#### 1.1 CLI（✅ 完了）

- **作成**: `create-project`, `create-task`
- **読み取り**: `get-task`, `get-board`, `get-gantt`, `list-blockers`
- **更新・移動**: `update-task`, `move-task`, `mark-done`
- **依存**: `add-dependency`, `remove-dependency`（サイクル時は拒否）
- 全コマンドで `--json-output` 対応。1 コマンド 1 モジュール（`taskul/commands/`）。

#### 1.2 HTTP API（✅ 完了）

- **配置**: `taskul/api/`（FastAPI）。既存の `db.py` と `commands/*_impl` を再利用。
- **エンドポイント**: `GET/POST /projects`, `GET /projects/{id}`, `GET /projects/{id}/board`, `GET /projects/{id}/gantt`, `GET /projects/{id}/blockers`, `GET/POST/PATCH /tasks/{id}`, `POST /tasks/{id}/move`, `POST /tasks/{id}/mark-done`, `POST/DELETE /dependencies`。
- 単一ユーザー・ローカル前提。起動: `taskul serve` または `uvicorn taskul.api.app:app`。Swagger UI: `/docs`。

---

### 2. 状態の可視化（board / gantt / blockers）

**目的**: ボード・ガント・ブロッカーを「見える形」で扱えるようにする。

#### 2.1 データ取得（✅ 完了）

- `get-board` … ステータス別レーン＋タスク順（`lanes: { status -> [task, ...] }`）
- `get-gantt` … 期間指定可能な Gantt 用データ（start_date, due_date, estimate_hours 含む）
- `list-blockers` … ブロックされているタスク一覧（`blocked_by` 付き）

CLI/JSON での出力は実装済み。グラフィカルな表示は **Phase 4（UI）** で行う。

#### 2.2 表示（Phase 4 で実施）

- ボード／ガント／ブロッカー一覧の表示は Web UI または TUI で実装する。

---

### 3. ルールと整合性（依存・制約・履歴）

**目的**: 依存のルール、DB/アプリの制約、操作履歴を明確にし、一貫して守る。

#### 3.1 依存関係（✅ 一部完了）

- **サイクル禁止**: `taskul/cycle_check.py` の `would_create_cycle` で検出し、`add-dependency` で拒否。実装済み。
- 同一プロジェクト内・自タスクへの依存禁止は DB/アプリで維持済み。

#### 3.2 制約（✅ 完了）

- Task ID 不変、`(project_id, status, rank)` の一意性はスキーマとコマンドで維持済み。
- 移動・更新時の rank の付け替えも実装済み。

#### 3.3 履歴（✅ 完了）

- **記録**: `events` テーブルに TASK_CREATED / TASK_UPDATED / TASK_MOVED / DEP_CREATED / DEP_REMOVED を各コマンドから挿入済み。
- **共通化**: `taskul/events.py` に `record_event(conn, actor, type, payload)` を用意し、全コマンド（create_task, update_task, move_task, add/remove_dependency, mark_done）から呼ぶ形にリファクタ済み。
- **参照**: CLI `get-events`（`--project-id`, `--type`, `--limit`）、API `GET /events`（query: project_id, event_type, limit）。監査・undo 検討の土台として利用可能。

---

### 4. UI（Web / TUI）

**目的**: ボード・ガント・ブロッカーなどを画面で見て操作できるようにする。

#### 4.1 Web UI（✅ 完了・表示）

- **配置**: `taskul/web/`（index.html, style.css, app.js）。FastAPI で `/app/` に StaticFiles マウント。
- **内容**: プロジェクト一覧 → プロジェクト選択で Kanban ボード（Backlog / Todo / Doing / Review / Done のレーン＋タスクカード）を表示。ブロッカー一覧ボタンでブロックされているタスクを表示。既存 API（GET /projects, GET /projects/{id}/board, GET /projects/{id}/blockers）を利用。表示のみ（編集は CLI/API）。
- SPEC の Non-Goals「Complex gantt editing UI」のため、Gantt 表示・ドラッグ操作は未実装。

#### 4.2 TUI（未着手）

- ターミナル内でのボード表示・キー操作など。Textual / Cursive 等の検討。

---

### その他の検討事項

- **スキーママイグレーション**: カラム追加・テーブル追加時に `schema/migrations/` でバージョン管理する方式を検討。
- **パッケージ公開**: PyPI 公開時は `pyproject.toml` とコンソールスクリプト `taskul` の整備を行う。
