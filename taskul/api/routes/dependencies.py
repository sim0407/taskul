"""Dependencies API routes (task dependency graph)."""
import sqlite3

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_db

router = APIRouter()


@router.post("")
def add_dependency(
    body: dict,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Add a dependency: from_task_id blocks to_task_id. Body: { \"from_task_id\": \"T-000001\", \"to_task_id\": \"T-000002\" }. Rejects if cycle."""
    from_task_id = body.get("from_task_id")
    to_task_id = body.get("to_task_id")
    if not from_task_id or not to_task_id:
        raise HTTPException(status_code=400, detail="from_task_id and to_task_id are required")
    from ...commands.add_dependency import add_dependency_impl
    try:
        return add_dependency_impl(conn, from_task_id, to_task_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("")
def remove_dependency(
    from_task_id: str,
    to_task_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Remove a dependency. Query params: from_task_id, to_task_id."""
    from ...commands.remove_dependency import remove_dependency_impl
    result = remove_dependency_impl(conn, from_task_id, to_task_id)
    if result is None:
        raise HTTPException(status_code=404, detail="dependency not found")
    return result
