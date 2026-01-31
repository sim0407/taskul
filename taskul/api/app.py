"""FastAPI application."""
from pathlib import Path

from fastapi import FastAPI, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from .deps import get_db
from .routes import projects, tasks, dependencies, events, milestones

app = FastAPI(
    title="taskul",
    description="Single-user local task management (Kanban + Gantt). Agent-friendly CLI & API.",
    version="0.1.0",
)


@app.post("/seed")
def create_seed_project(
    body: dict | None = None,
    conn=Depends(get_db),
):
    """Create a sample project with milestones, tasks (including subtasks), and dependencies. Body: optional { \"name\": \"サンプルプロジェクト\" }."""
    from ...commands.seed import seed_impl
    name = (body or {}).get("name") or "サンプルプロジェクト"
    try:
        return seed_impl(conn, name)
    except ValueError as e:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail=str(e))


app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(milestones.router, prefix="/milestones", tags=["milestones"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(dependencies.router, prefix="/dependencies", tags=["dependencies"])
app.include_router(events.router, prefix="/events", tags=["events"])


@app.get("/")
def root():
    return {"service": "taskul", "docs": "/docs", "web_ui": "/app/"}


@app.get("/app")
def app_redirect():
    """Redirect /app to /app/ so that index.html is served."""
    return RedirectResponse(url="/app/")


# Web UI (static): /app/ → taskul/web/ (mount after /app redirect so redirect is matched first)
_web_dir = Path(__file__).resolve().parent.parent / "web"
if _web_dir.exists():
    app.mount("/app", StaticFiles(directory=str(_web_dir), html=True), name="web")
