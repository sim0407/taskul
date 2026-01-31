-- taskul MVP - SQLite DDL
-- Run once to create schema (e.g. on first use or via init command).

-- Projects
CREATE TABLE IF NOT EXISTS projects (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL
);

-- Milestones (title + date range per project)
CREATE TABLE IF NOT EXISTS milestones (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  start_date TEXT NOT NULL,
  due_date TEXT NOT NULL,
  CHECK (start_date <= due_date)
);

CREATE INDEX IF NOT EXISTS idx_milestones_project ON milestones(project_id);

-- Tasks (status lane + rank unique per project+status; optional milestone, optional parent for subtasks)
CREATE TABLE IF NOT EXISTS tasks (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL CHECK (status IN ('Backlog', 'Todo', 'Doing', 'Review', 'Done')),
  rank INTEGER NOT NULL,
  start_date TEXT,
  due_date TEXT,
  estimate_hours REAL,
  milestone_id TEXT REFERENCES milestones(id) ON DELETE SET NULL,
  parent_task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  UNIQUE(project_id, status, rank)
);

CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_dates ON tasks(project_id, start_date, due_date);

-- Dependencies (from_task_id blocks to_task_id; cycles forbidden at application level)
CREATE TABLE IF NOT EXISTS dependencies (
  from_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  to_task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
  PRIMARY KEY (from_task_id, to_task_id),
  CHECK (from_task_id != to_task_id)
);

CREATE INDEX IF NOT EXISTS idx_deps_to ON dependencies(to_task_id);

-- Append-only events (audit / agent-friendly)
CREATE TABLE IF NOT EXISTS events (
  event_id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now')),
  actor TEXT NOT NULL CHECK (actor IN ('human', 'agent')),
  type TEXT NOT NULL,
  payload TEXT
);

-- Sequence helpers for ID generation (T-000001, P-0001)
CREATE TABLE IF NOT EXISTS id_sequences (
  prefix TEXT PRIMARY KEY,
  next_value INTEGER NOT NULL DEFAULT 1
);
INSERT OR IGNORE INTO id_sequences (prefix, next_value) VALUES ('T', 1), ('P', 1), ('M', 1);
