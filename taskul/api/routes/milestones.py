"""Milestones API routes."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_db
from ...db import get_milestone

router = APIRouter()


@router.get("/{milestone_id}")
def get_milestone_by_id(
    milestone_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get a single milestone."""
    m = get_milestone(conn, milestone_id)
    if m is None:
        raise HTTPException(status_code=404, detail="milestone not found")
    return m


@router.patch("/{milestone_id}")
def update_milestone(
    milestone_id: str,
    body: dict,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Update a milestone. Body: optional title, start_date, due_date (start_date <= due_date)."""
    from ...commands.update_milestone import update_milestone_impl
    try:
        return update_milestone_impl(
            conn,
            milestone_id,
            title=body.get("title"),
            start_date=body.get("start_date"),
            due_date=body.get("due_date"),
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
