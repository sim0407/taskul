# taskul - SPEC (MVP)

## Goal
Single-user local task management tool with Kanban + Gantt.
Agent-friendly: all operations are possible via CLI and HTTP API, with JSON outputs.

## Core Entities
### Project
- id: string (e.g. "P-0001")
- name: string

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

## Non-Goals (for now)
- Multi-user, auth, cloud sync
- Complex gantt editing UI