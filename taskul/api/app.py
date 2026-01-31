"""FastAPI application."""
from fastapi import FastAPI

from .routes import projects, tasks, dependencies

app = FastAPI(
    title="taskul",
    description="Single-user local task management (Kanban + Gantt). Agent-friendly CLI & API.",
    version="0.1.0",
)

app.include_router(projects.router, prefix="/projects", tags=["projects"])
app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])
app.include_router(dependencies.router, prefix="/dependencies", tags=["dependencies"])


@app.get("/")
def root():
    return {"service": "taskul", "docs": "/docs"}
