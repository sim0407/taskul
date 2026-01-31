-- Migration: add task.depth (0 = root, 1 = direct child, ...)
ALTER TABLE tasks ADD COLUMN depth INTEGER DEFAULT 0;
UPDATE tasks SET depth = 0 WHERE parent_task_id IS NULL;
-- Backfill: set depth = parent.depth + 1 (multiple passes for deep trees)
UPDATE tasks SET depth = (SELECT depth + 1 FROM tasks t2 WHERE t2.id = tasks.parent_task_id) WHERE parent_task_id IS NOT NULL;
UPDATE tasks SET depth = (SELECT depth + 1 FROM tasks t2 WHERE t2.id = tasks.parent_task_id) WHERE parent_task_id IS NOT NULL;
UPDATE tasks SET depth = (SELECT depth + 1 FROM tasks t2 WHERE t2.id = tasks.parent_task_id) WHERE parent_task_id IS NOT NULL;
UPDATE tasks SET depth = (SELECT depth + 1 FROM tasks t2 WHERE t2.id = tasks.parent_task_id) WHERE parent_task_id IS NOT NULL;
UPDATE tasks SET depth = (SELECT depth + 1 FROM tasks t2 WHERE t2.id = tasks.parent_task_id) WHERE parent_task_id IS NOT NULL;
