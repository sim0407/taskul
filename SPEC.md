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

## 今後の改修方針

以下の項目を今後の改修として整理する。

### データ・ルール

- **親タスクのステータスルール**  
  親タスクのステータスは、子タスクのステータスから導出する。子タスクを **doing → todo → review → backlog → done** の順で確認し、該当する子タスクが一つでもあれば、その時点で親タスクをそのステータスとする（doing が最も優先度が高い）。

- **親タスクの見積時間**  
  親タスクの見積時間は、子タスクの見積時間の合計になるように変更する（算出値として扱う）。

### 入力・型チェック

- **日付の複数形式対応**  
  日付は次の形式を受け付ける: `YYYY-MM-DD`、`YYYY/MM/DD`、`YYYYMMDD`。  
  4 桁の数字のみが入力された場合は **MMDD** と解釈し、最も近い未来の該当する日付として受け取る。

- **タスク追加時の属性入力**  
  タスク追加時（作成時）にも、マイルストーン・due_date・見積時間・説明などの属性入力を受け付ける。

### バグ修正

- **名称変更・説明保存時のエラー**  
  タスクの名称を変更した際、または既存タスクの説明欄に入力して保存ボタンを押した際に「would create cycle in parent chain」が出る不具合を修正する。名称・説明の更新では親子関係を変更していないため、循環チェックの誤判定を解消する。

### フィルタ・表示機能

- **未設定タスクのフィルタ**  
  マイルストーン・due_date・見積時間のいずれか（または全て）が設定されていないタスクだけをフィルタする機能を追加する。

- **子タスクの折り畳み**  
  子タスクの表示を折り畳み／展開できる機能を追加する。

- **子タスクの表示ルール**  
  - 親タスクと同じステータスの子タスク: 親子関係が分かるようにまとめて表示する。  
  - 親タスクと異なるステータスの子タスク: 親のタスク名が分かるように表示する。

- **ID の表示**  
  Web UI のカンバンでは、スペース節約のためタスク ID は表示しない。編集画面など、一つのタスクにフォーカスする場面では ID を表示する。

- **カンバン上のタスク表示**  
  カンバンの各タスクに、締め切りを **MM/DD**、見積時間を **数字+h**（例: `2h`）で表示する。

### 進捗・サマリ

- **締切が最も近いマイルストーンまでの進捗**  
  締切が最も近いマイルストーンに紐づく（またはその範囲までの）タスクについて、合計見積時間と進捗状況を表示する。進捗は「Review」「Done」を完了としたときの終了割合で示す。

### フロントエンド

- **JavaScript → TypeScript**  
  Web UI の `taskul/web/` 配下の JavaScript を TypeScript に移行する。

### インポート・エクスポート

- **プロジェクト単位の XML / CSV**  
  プロジェクト単位での XML・CSV によるデータのエクスポートとインポートを可能にする。

---

## 今後の検討事項

- **TUI**: ターミナル内でのボード表示・キー操作（Textual / Cursive 等の検討）
- **スキーママイグレーション**: カラム・テーブル追加時に `schema/migrations/` でバージョン管理する方式の検討
- **パッケージ公開**: PyPI 公開時は `pyproject.toml` とコンソールスクリプト `taskul` の整備