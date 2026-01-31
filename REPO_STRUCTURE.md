# taskul - リポジトリ構成

## ディレクトリ構成

```
taskul/
├── SPEC.md                 # 仕様
├── REPO_STRUCTURE.md       # 本ドキュメント
├── README.md
├── requirements.txt        # Python 依存
├── schema/
│   └── init.sql            # SQLite DDL（初回セットアップ用）
├── taskul/
│   ├── __init__.py
│   ├── __main__.py
│   ├── db.py               # DB 接続・初期化・ヘルパ
│   ├── cli.py              # CLI エントリポイント（Click）
│   ├── cycle_check.py      # 依存サイクル検出
│   ├── events.py           # イベント記録（record_event）
│   ├── api/                # HTTP API（FastAPI）
│   │   ├── app.py
│   │   ├── deps.py
│   │   └── routes/
│   │       ├── projects.py
│   │       ├── tasks.py
│   │       ├── dependencies.py
│   │       └── events.py
│   ├── web/                # Web UI 静的ファイル
│   │   ├── index.html
│   │   ├── style.css
│   │   └── app.js
│   └── commands/           # CLI コマンド（1 コマンド 1 モジュール）
│       ├── create_project.py
│       ├── create_task.py
│       ├── get_task.py
│       ├── get_board.py
│       ├── get_gantt.py
│       ├── list_blockers.py
│       ├── get_events.py
│       ├── update_task.py
│       ├── move_task.py
│       ├── mark_done.py
│       ├── add_dependency.py
│       ├── remove_dependency.py
│       └── serve.py        # API サーバ起動
└── tests/
    └── ...
```

## 方針

- **言語**: Python 3（CLI・API・JSON 出力に適している）
- **CLI**: Click（サブコマンド・引数・JSON 出力が扱いやすい）
- **DB**: SQLite（単一ユーザー・ローカル前提）
- **スキーマ**: `schema/init.sql` をアプリ起動時または専用コマンドで適用
- **コマンド**: `taskul/commands/` に 1 コマンド 1 モジュールで配置し、`cli.py` で登録
- **API**: FastAPI（`taskul/api/`）。`taskul serve` で起動。Swagger UI は `/docs`
- **Web UI**: `taskul/web/` の静的ファイルを API の `/app/` で配信

## 実行方法（開発時）

セットアップ・コマンド一覧・API の使い方は [README.md](README.md) を参照。開発時の最小手順のみ記載する。

```bash
python -m venv .venv && .venv/bin/activate
pip install -r requirements.txt
python -m taskul serve   # または uvicorn taskul.api.app:app --reload
# → http://127.0.0.1:8000/app/ で Web UI、/docs で API ドキュメント
```

DB はデフォルトで `~/.taskul/taskul.db`。別パスは環境変数 `TASKUL_DB` または `--db` で指定。

## Git 管理方針（GitHub 公開時）

### 管理する（コミットする）ファイル

| 種類 | 例 |
|------|-----|
| 仕様・ドキュメント | `SPEC.md`, `REPO_STRUCTURE.md`, `README.md` |
| 依存定義 | `requirements.txt` |
| スキーマ | `schema/init.sql` |
| ソースコード | `taskul/**/*.py`（`__pycache__` 以外） |
| Web UI | `taskul/web/*.html`, `*.css`, `*.js` |
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

DB はデフォルトで `~/.taskul/taskul.db` に作成されるためリポジトリには含めません。開発時にリポジトリ内で `taskul.db` を作成した場合も、`.gitignore` で除外します。
