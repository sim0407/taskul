"""Projects API routes."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_db
from ...db import get_projects, get_project, get_board, get_gantt, list_blockers

router = APIRouter()


@router.get("")
def list_projects(conn: sqlite3.Connection = Depends(get_db)):
    """List all projects."""
    return get_projects(conn)


@router.post("")
def create_project(
    body: dict,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Create a project. Body: { \"name\": \"Project Name\" }."""
    name = body.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")
    from ...commands.create_project import create_project_impl
    return create_project_impl(conn, name)


@router.get("/{project_id}")
def get_project_by_id(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get a single project."""
    project = get_project(conn, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="project not found")
    return project


@router.get("/{project_id}/board")
def get_project_board(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get Kanban board (lanes by status with ordered tasks)."""
    board = get_board(conn, project_id)
    if board is None:
        raise HTTPException(status_code=404, detail="project not found")
    return board


@router.get("/{project_id}/gantt")
def get_project_gantt(
    project_id: str,
    from_date: str | None = None,
    to_date: str | None = None,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get Gantt data (tasks with schedule fields). Optional query: from_date, to_date (YYYY-MM-DD)."""
    tasks_list = get_gantt(conn, project_id, from_date, to_date)
    if tasks_list is None:
        raise HTTPException(status_code=404, detail="project not found")
    return tasks_list


@router.get("/{project_id}/blockers")
def get_project_blockers(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """List tasks that are blocked (have unfinished dependencies)."""
    result = list_blockers(conn, project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="project not found")
    return result
