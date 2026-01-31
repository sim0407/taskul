"""FastAPI application."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from .routes import projects, tasks, dependencies, events

app = FastAPI(
    title="taskul",
    description="Single-user local task management (Kanban + Gantt). Agent-friendly CLI & API.",
    version="0.1.0",
)

app.include_router(projects.router, prefix="/projects", tags=["projects"])
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
