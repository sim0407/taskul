"""Tasks API routes."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_db
from ...db import get_task, get_task_delete_check

router = APIRouter()


@router.post("")
def create_task(
    body: dict,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Create a task. Body: project_id, title; optional: status, milestone_id, parent_task_id, start_date, due_date.

    When parent_task_id is specified, status, milestone_id, start_date, and due_date
    will inherit from the parent task if not explicitly provided.
    """
    project_id = body.get("project_id")
    title = body.get("title")
    if not project_id or not title:
        raise HTTPException(status_code=400, detail="project_id and title are required")
    parent_task_id = body.get("parent_task_id") or None
    from ...commands.create_task import create_task_impl, _UNSET

    # Build kwargs: only pass values that were explicitly provided
    kwargs = {"parent_task_id": parent_task_id}
    if "status" in body and body["status"]:
        kwargs["status"] = body["status"]
    else:
        kwargs["status"] = _UNSET
    if "milestone_id" in body:
        kwargs["milestone_id"] = body["milestone_id"] or None
    else:
        kwargs["milestone_id"] = _UNSET
    if "start_date" in body:
        kwargs["start_date"] = body["start_date"] or None
    else:
        kwargs["start_date"] = _UNSET
    if "due_date" in body:
        kwargs["due_date"] = body["due_date"] or None
    else:
        kwargs["due_date"] = _UNSET

    try:
        return create_task_impl(conn, project_id, title, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.patch("/{task_id}")
def update_task(
    task_id: str,
    body: dict,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Update a task. Body: optional title, description, status, start_date, due_date, estimate_hours, milestone_id, parent_task_id (null to clear)."""
    from ...commands.update_task import update_task_impl, _UNSET
    kwargs = {
        "title": body.get("title"),
        "description": body.get("description"),
        "status": body.get("status"),
        "start_date": body.get("start_date"),
        "due_date": body.get("due_date"),
        "estimate_hours": body.get("estimate_hours"),
    }
    if "milestone_id" in body:
        kwargs["milestone_id"] = body["milestone_id"]
    if "parent_task_id" in body:
        kwargs["parent_task_id"] = body["parent_task_id"]
    try:
        return update_task_impl(conn, task_id, **kwargs)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{task_id}/move")
def move_task(
    task_id: str,
    body: dict,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Move a task to a status lane. Body: { \"status\": \"Todo\" }."""
    status = body.get("status")
    if not status:
        raise HTTPException(status_code=400, detail="status is required")
    from ...commands.move_task import move_task_impl
    try:
        return move_task_impl(conn, task_id, status)
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


@router.get("/{task_id}/delete-check")
def check_task_delete(
    task_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Check what would be affected if this task is deleted."""
    result = get_task_delete_check(conn, task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="task not found")
    return result


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


@router.delete("/{task_id}")
def delete_task(
    task_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Delete a task."""
    from ...commands.delete_task import delete_task_impl
    try:
        return delete_task_impl(conn, task_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
