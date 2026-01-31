"""Tasks API routes."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_db
from ...db import get_task

router = APIRouter()


@router.get("/{task_id}")
def get_task_by_id(
    task_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get a single task."""
    task = get_task(conn, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return task


@router.post("")
def create_task(
    body: dict,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Create a task. Body: { \"project_id\": \"P-0001\", \"title\": \"Title\", \"status\": \"Backlog\" (optional) }."""
    project_id = body.get("project_id")
    title = body.get("title")
    if not project_id or not title:
        raise HTTPException(status_code=400, detail="project_id and title are required")
    status = body.get("status", "Backlog")
    from ...commands.create_task import create_task_impl
    try:
        return create_task_impl(conn, project_id, title, status)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{task_id}")
def update_task(
    task_id: str,
    body: dict,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Update a task. Body: optional title, description, status, start_date, due_date, estimate_hours."""
    from ...commands.update_task import update_task_impl
    try:
        return update_task_impl(
            conn,
            task_id,
            title=body.get("title"),
            description=body.get("description"),
            status=body.get("status"),
            start_date=body.get("start_date"),
            due_date=body.get("due_date"),
            estimate_hours=body.get("estimate_hours"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/move")
def move_task(
    task_id: str,
    body: dict,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Move a task to a status lane. Body: { \"status\": \"Todo\", \"position\": \"top\" | \"bottom\" | \"after:T-xxxxxx\" (optional, default bottom) }."""
    status = body.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="status is required")
    position = body.get("position", "bottom")
    from ...commands.move_task import move_task_impl
    try:
        return move_task_impl(conn, task_id, status, position)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/mark-done")
def mark_task_done(
    task_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Mark a task as Done."""
    from ...commands.mark_done import mark_done_impl
    try:
        return mark_done_impl(conn, task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
