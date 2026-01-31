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
| **4** | UI（Web / TUI） | Web UI 表示・操作（作成/更新/移動/完了/依存追加・削除）完了 / TUI 未着手 |

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

#### 4.1 Web UI（✅ 表示・操作のうち作成/更新/移動/完了まで完了）

- **配置**: `taskul/web/`（index.html, style.css, app.js）。FastAPI で `/app/` に StaticFiles マウント。
- **現状**: プロジェクト一覧・**新規作成**（モーダル）→ プロジェクト選択で Kanban ボード → **タスク追加**（モーダル）、カードごとに**完了**・**移動**（ドロップダウン）・**編集**（モーダル）。**依存を追加**（モーダルで from/to 選択）、**ブロッカー一覧**で各依存に**解除**ボタン。API（GET/POST/PATCH/DELETE）を利用。エラーはトースト表示、操作後にボード/一覧を再取得。
- Gantt 表示・ドラッグ操作は対象外。

#### 4.1.2 Web UI 操作拡張（✅ 完了）

**目的**: Web UI からプロジェクト・タスクの追加・変更・依存の操作を行えるようにする（CLI/API と同等の操作を画面で実行可能にする）。

**前提**:
- 既存の HTTP API（POST/PATCH/DELETE）をそのまま利用する。バックエンドの新規エンドポイントは不要。
- 単一ユーザー・ローカル前提のため、認証は不要（同一オリジンで API を叩く）。

**必要な事項（機能ごと）**:

| 操作 | 利用する API | Web UI で必要なこと |
|------|----------------|---------------------|
| プロジェクト作成 | `POST /projects`（body: `name`） | プロジェクト一覧画面に「新規作成」ボタン＋モーダル/フォーム（名前入力）→ 送信後に一覧を再取得して表示 |
| タスク作成 | `POST /tasks`（body: `project_id`, `title`, `status?`） | ボード画面に「タスク追加」ボタン＋フォーム（タイトル、ステータス選択）→ 送信後にボードを再取得 |
| タスク更新 | `PATCH /tasks/{id}`（body: 任意フィールド） | タスクカードに「編集」またはクリックでフォーム（title, description, status, start_date, due_date, estimate_hours）→ 送信後にボードを再取得 |
| タスク移動 | `POST /tasks/{id}/move`（body: `status`, `position?`） | カードにステータス変更 UI（ドロップダウンまたは「→ Todo」等のボタン）、必要なら position（top/bottom/after）の指定 |
| タスク完了 | `POST /tasks/{id}/mark-done` | カードに「完了」ボタン→ 送信後にボードを再取得 |
| 依存追加 | `POST /dependencies`（body: `from_task_id`, `to_task_id`） | ボードまたはタスク詳細で「依存を追加」フォーム（from / to のタスク ID 選択または入力）→ サイクル時は API が 400 を返すのでメッセージ表示 |
| 依存削除 | `DELETE /dependencies?from_task_id=...&to_task_id=...` | ブロッカー一覧またはタスク詳細で依存一覧＋「削除」ボタン |

**共通で必要なこと**:
- **エラー表示**: 上記 API が 4xx を返したとき、レスポンスの `detail` を画面に表示する（例: バリデーションエラー、サイクル拒否、not found）。
- **操作後の更新**: 作成・更新・移動・削除の成功後に、該当するデータ（プロジェクト一覧またはボード）を再取得（GET）して DOM を更新する。
- **入力チェック**: 必須項目（名前、タイトル、project_id など）はクライアント側でもチェックし、API の 400 を減らす（任意）。

**実装方針**:
- 既存の `taskul/web/` の HTML/CSS/JS を拡張する。フレームワークは使わず Vanilla JS のままでも可。必要に応じてフォーム用のモーダルやインライン編集の UI を追加。
- ドラッグ＆ドロップでのレーン間移動は、SPEC の「Complex gantt editing UI」を避けるため、まずはドロップダウンやボタンで「移動先ステータス」を選ぶ方式でよい。将来的に D&D を入れてもよい。

**優先度の目安**: プロジェクト作成 → タスク作成 → タスク完了・移動 → タスク更新（編集） → 依存追加・削除、の順で段階的に追加すると扱いやすい。

**実装済み（4.1.2）**: プロジェクト作成、タスク作成、タスク完了、タスク移動（ドロップダウン）、タスク編集（モーダル）、依存追加（モーダルで from/to タスク選択）、依存削除（ブロッカー一覧で「〇→〇 を解除」ボタン）。エラー表示（トースト）、操作後の再取得。

#### 4.2 TUI（未着手）

- ターミナル内でのボード表示・キー操作など。Textual / Cursive 等の検討。

---

### その他の検討事項

- **スキーママイグレーション**: カラム追加・テーブル追加時に `schema/migrations/` でバージョン管理する方式を検討。
- **パッケージ公開**: PyPI 公開時は `pyproject.toml` とコンソールスクリプト `taskul` の整備を行う。
