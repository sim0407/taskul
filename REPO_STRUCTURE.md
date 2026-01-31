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

- `taskul/api/` … FastAPI 等で HTTP API
- `taskul/events.py` … イベント記録の共通処理
- `taskul/cycle_check.py` … 依存関係のサイクル検出
