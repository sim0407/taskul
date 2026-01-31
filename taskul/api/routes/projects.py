"""Projects API routes."""
import sqlite3
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from ..deps import get_db
from ...db import get_projects, get_project, get_board, get_gantt, list_blockers, get_milestones, get_project_delete_check, get_progress_summary

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


@router.get("/{project_id}/delete-check")
def check_project_delete(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Check what would be deleted if this project is deleted."""
    result = get_project_delete_check(conn, project_id)
    if result is None:
        raise HTTPException(status_code=404, detail="project not found")
    return result


@router.get("/{project_id}/board")
def get_project_board(
    project_id: str,
    missing_milestone: bool = False,
    missing_due_date: bool = False,
    missing_estimate: bool = False,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get Kanban board (lanes by status with ordered tasks).

    Optional filters to show only tasks missing certain fields:
    - missing_milestone: only tasks without milestone
    - missing_due_date: only tasks without due_date
    - missing_estimate: only tasks without estimate_hours
    """
    board = get_board(
        conn,
        project_id,
        missing_milestone=missing_milestone,
        missing_due_date=missing_due_date,
        missing_estimate=missing_estimate,
    )
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


@router.get("/{project_id}/milestones")
def get_project_milestones(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """List milestones of a project (by start_date)."""
    ms = get_milestones(conn, project_id)
    if ms is None:
        raise HTTPException(status_code=404, detail="project not found")
    return ms


@router.get("/{project_id}/progress")
def get_project_progress(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Get progress summary for the nearest upcoming milestone."""
    summary = get_progress_summary(conn, project_id)
    if summary is None:
        raise HTTPException(status_code=404, detail="project not found")
    return summary


@router.post("/{project_id}/milestones")
def create_milestone(
    project_id: str,
    body: dict,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Create a milestone. Body: { \"title\": \"...\", \"start_date\": \"YYYY-MM-DD\", \"due_date\": \"YYYY-MM-DD\" }."""
    title = body.get("title")
    start_date = body.get("start_date")
    due_date = body.get("due_date")
    if not title or not start_date or not due_date:
        raise HTTPException(status_code=400, detail="title, start_date, and due_date are required")
    from ...commands.create_milestone import create_milestone_impl
    try:
        return create_milestone_impl(conn, project_id, title, start_date, due_date)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{project_id}/export")
def export_project_tasks(
    project_id: str,
    format: str = "csv",
    conn: sqlite3.Connection = Depends(get_db),
):
    """Export project tasks to CSV or XML format.

    Query params:
    - format: 'csv' or 'xml' (default: csv)
    """
    from ...commands.export_tasks import export_tasks_impl
    try:
        content = export_tasks_impl(conn, project_id, format)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    media_type = "text/csv" if format == "csv" else "application/xml"
    filename = f"{project_id}_tasks.{format}"

    from fastapi.responses import Response
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{project_id}/import")
def import_tasks(
    project_id: str,
    file: UploadFile = File(...),
    conn: sqlite3.Connection = Depends(get_db),
):
    """Import tasks from CSV/Excel/XML file. Supported: .csv, .xlsx, .xml"""
    from ...commands.import_tasks import import_tasks_impl

    # Check file extension
    filename = file.filename or ""
    ext = Path(filename).suffix.lower()
    if ext not in (".csv", ".xlsx", ".xml"):
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {ext}. Use .csv, .xlsx, or .xml")

    # Save to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=ext) as tmp:
        content = file.file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        result = import_tasks_impl(conn, project_id, tmp_path)
        return result
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        Path(tmp_path).unlink(missing_ok=True)


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


@router.delete("/{project_id}")
def delete_project(
    project_id: str,
    conn: sqlite3.Connection = Depends(get_db),
):
    """Delete a project and all its tasks/milestones."""
    from ...commands.delete_project import delete_project_impl
    try:
        return delete_project_impl(conn, project_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
