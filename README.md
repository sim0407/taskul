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

### 読み取り（Phase 1）

```bash
# ボード取得（ステータス別レーン＋タスク順）
python -m taskul get-board P-0001 [--json-output]

# Gantt 用データ（期間指定可）
python -m taskul get-gantt P-0001 [--from YYYY-MM-DD] [--to YYYY-MM-DD] [--json-output]

# 単一タスク取得
python -m taskul get-task T-000001 [--json-output]

# ブロックされているタスク一覧
python -m taskul list-blockers P-0001 [--json-output]
```

### 更新・移動・依存（Phase 1）

```bash
# タスク更新（指定した項目のみ更新）
python -m taskul update-task T-000001 --title "新タイトル" --status Todo [--json-output]

# タスク移動（top / bottom / after:T-xxxxxx）
python -m taskul move-task T-000001 Todo --position top [--json-output]

# 依存追加（サイクルになる場合は拒否）
python -m taskul add-dependency T-000001 T-000002 [--json-output]

# 依存削除
python -m taskul remove-dependency T-000001 T-000002 [--json-output]

# 完了にする
python -m taskul mark-done T-000001 [--json-output]
```

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

1. **操作の充実（CLI/API）** — CLI は完了。HTTP API は未着手。
2. **状態の可視化（board / gantt / blockers）** — データ取得（get-board, get-gantt, list-blockers）は完了。表示は Phase 4 の UI で。
3. **ルールと整合性（依存・制約・履歴）** — 依存のサイクル検出・制約は完了。履歴の共通化（events.py）・履歴参照は未着手。
4. **UI（Web / TUI）** — 未着手。

詳細は [REPO_STRUCTURE.md](REPO_STRUCTURE.md) の「今後の拡張」を参照。

## ライセンス

MIT License。詳細は [LICENSE](LICENSE) を参照してください。
