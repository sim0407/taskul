// Type definitions for taskul web UI

export type TaskStatus = 'Backlog' | 'Todo' | 'Doing' | 'Review' | 'Done';

export interface Project {
  id: string;
  name: string;
}

export interface Milestone {
  id: string;
  project_id: string;
  title: string;
  start_date: string;
  due_date: string;
}

export interface Task {
  id: string;
  project_id: string;
  title: string;
  description: string | null;
  status: TaskStatus;
  start_date: string | null;
  due_date: string | null;
  estimate_hours: number | null;
  milestone_id: string | null;
  parent_task_id: string | null;
  depth: number;
  created_at: string;
}

export interface Board {
  project_id: string;
  lanes: Record<TaskStatus, Task[]>;
}

export interface ProgressSummary {
  milestone: Milestone | null;
  total_estimate_hours: number;
  completed_estimate_hours: number;
  progress_percent: number;
  task_count: number;
  completed_task_count: number;
}

export interface Blocker {
  id: string;
  project_id: string;
  title: string;
  status: TaskStatus;
  blocked_by: string[];
}

export interface Event {
  event_id: number;
  ts: string;
  actor: string;
  type: string;
  payload: Record<string, unknown>;
}

export interface DeleteCheck {
  task_count?: number;
  milestone_count?: number;
  child_count?: number;
  descendant_count?: number;
}
