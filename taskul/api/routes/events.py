"""Events API routes (audit log)."""
import sqlite3

from fastapi import APIRouter, Depends

from ..deps import get_db
from ...db import get_events

router = APIRouter()


@router.get("")
def list_events(
    project_id: str | None = None,
    event_type: str | None = None,
    limit: int = 100,
    conn: sqlite3.Connection = Depends(get_db),
):
    """List events (audit log). Newest first. Optional query: project_id, event_type, limit."""
    return get_events(conn, limit=limit, event_type=event_type, project_id=project_id)
