-- Migration: Remove rank column, order by dates instead
-- SQLite doesn't support DROP COLUMN directly in older versions, so we recreate the table

-- Create new tasks table without rank
CREATE TABLE IF NOT EXISTS tasks_new (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL CHECK (status IN ('Backlog', 'Todo', 'Doing', 'Review', 'Done')),
  start_date TEXT,
  due_date TEXT,
  estimate_hours REAL,
  milestone_id TEXT REFERENCES milestones(id) ON DELETE SET NULL,
  parent_task_id TEXT REFERENCES tasks(id) ON DELETE SET NULL,
  depth INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
);

-- Copy data (excluding rank)
INSERT INTO tasks_new (id, project_id, title, description, status, start_date, due_date, estimate_hours, milestone_id, parent_task_id, depth, created_at)
SELECT id, project_id, title, description, status, start_date, due_date, estimate_hours, milestone_id, parent_task_id, depth, created_at
FROM tasks;

-- Drop old table and rename new one
DROP TABLE tasks;
ALTER TABLE tasks_new RENAME TO tasks;

-- Recreate indexes
CREATE INDEX IF NOT EXISTS idx_tasks_project_status ON tasks(project_id, status);
CREATE INDEX IF NOT EXISTS idx_tasks_dates ON tasks(project_id, start_date, due_date);
