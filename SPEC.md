# taskul - SPEC (MVP)

## Goal
Single-user local task management tool with Kanban + Gantt.
Agent-friendly: all operations are possible via CLI and HTTP API, with JSON outputs.

## Core Entities
### Project
- id: string (e.g. "P-0001")
- name: string

### Milestone
- id: string (e.g. "M-0001") immutable
- project_id: string
- title: string
- start_date: YYYY-MM-DD
- due_date: YYYY-MM-DD（幅を持った期日。start_date ≦ due_date）

### Task
- id: string (e.g. "T-000001") immutable
- project_id: string
- title: string
- description: string (optional)
- status: Backlog | Todo | Doing | Review | Done
- rank: integer (ordering inside a status lane; smaller = higher priority)
- start_date: YYYY-MM-DD (optional)
- due_date: YYYY-MM-DD (optional)
- estimate_hours: number (optional)
- milestone_id: string (optional) — タスクはマイルストーンを**1つまで**持てる
- parent_task_id: string (optional) — 親タスク。1つまで持てる（サブタスクはこの関係で表現）
- depth: integer — root（親を持たない）から数えた段数。root=0、その子=1、孫=2 …

### Dependency
- from_task_id blocks to_task_id
- rule: no cycles allowed

### Event (append-only)
- event_id, ts
- actor: "human" | "agent"
- type: TASK_CREATED / TASK_UPDATED / TASK_MOVED / DEP_CREATED / ...
- payload: json

## MVP Queries (read)
- get_board(project_id) -> lanes: status -> ordered tasks
- get_gantt(project_id, from, to) -> tasks with schedule fields
- get_task(task_id)
- list_blockers(project_id)

## MVP Commands (write)
- create_project(name)
- create_task(project_id, title, status=Backlog)
- update_task(task_id, fields...)
- move_task(task_id, status, rank_position=top|bottom|after:<task_id>)
- add_dependency(from_task_id, to_task_id)
- remove_dependency(...)
- mark_done(task_id)

## Constraints
- Task IDs are immutable.
- rank is unique within (project_id, status).
- Adding dependency must reject cycles.
- Moving tasks must keep rank consistency.
- **Milestone**: 同一プロジェクト内で start_date ≦ due_date。Milestone ID は不変。
- **Task と Milestone**: タスクは 0 または 1 個のマイルストーンを参照する。
- **サブタスク（parent_task_id）**: タスクは 0 または 1 個の親タスクを持つ。親子で循環してはならない（親チェーンは DAG／ツリー）。親タスクは同一 project_id とする。

**注**: マイルストーン・サブタスクのクエリ（一覧取得・ボード／ガントでの扱い）とコマンド（作成・更新・紐付け）は、実装時に別途定義する。

## Non-Goals (for now)
- Multi-user, auth, cloud sync
- Complex gantt editing UI

## Roadmap (development order)
1. 操作の充実（CLI/API）
2. 状態の可視化（board / gantt / blockers）
3. ルールと整合性（依存・制約・履歴）
4. UI（Web / TUI）

## 今後の方針

更新は次の順で検討する。

1. **データモデル・概念の拡張検討**  
   エンティティの追加・変更、新しい概念の検討。例: マイルストーン、ラベル／タグ、サブタスク、担当者、優先度の明示、カスタムステータス 等。既存の Project / Task / Dependency / Event の範囲で収めるか、スキーマ拡張するかを整理する。

2. **整合性・ルール設計**  
   制約・バリデーションの明確化、履歴・監査の拡張。例: 必須フィールド・日付の前後関係・依存とステータスの整合、イベントの用途拡大（undo 検討）、スキーママイグレーション方針 等。データの一貫性と運用ルールを仕様として固める。

3. **プロジェクト管理としての価値機能**  
   利用者がプロジェクトを進めるうえで役立つ機能。例: 進捗・工数レポート、ブロッカー解消の支援、期限リマインド、マイルストーン達成状況、ダッシュボード 等。1・2 を前提に、提供する価値機能の優先度を決める。

## 今後の検討事項

- **TUI**: ターミナル内でのボード表示・キー操作（Textual / Cursive 等の検討）
- **スキーママイグレーション**: カラム・テーブル追加時に `schema/migrations/` でバージョン管理する方式の検討
- **パッケージ公開**: PyPI 公開時は `pyproject.toml` とコンソールスクリプト `taskul` の整備