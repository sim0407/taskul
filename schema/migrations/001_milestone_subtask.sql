-- Migration: add milestones and task.milestone_id, task.parent_task_id (for existing DBs)
CREATE TABLE IF NOT EXISTS milestones (
  id TEXT PRIMARY KEY,
  project_id TEXT NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
  title TEXT NOT NULL,
  start_date TEXT NOT NULL,
  due_date TEXT NOT NULL,
  CHECK (start_date <= due_date)
);
CREATE INDEX IF NOT EXISTS idx_milestones_project ON milestones(project_id);

-- SQLite ALTER TABLE ADD COLUMN may not support REFERENCES on older versions
ALTER TABLE tasks ADD COLUMN milestone_id TEXT;
ALTER TABLE tasks ADD COLUMN parent_task_id TEXT;

INSERT OR IGNORE INTO id_sequences (prefix, next_value) VALUES ('M', 1);
