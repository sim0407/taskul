"""serve - Start HTTP API server (uvicorn)."""
import click


@click.command("serve")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind host")
@click.option("--port", default=8000, type=int, show_default=True, help="Bind port")
@click.option("--db", "db_path", envvar="TASKUL_DB", default=None, help="SQLite DB path")
def serve(host: str, port: int, db_path: str | None):
    """Start the HTTP API server (FastAPI + uvicorn). Default: http://127.0.0.1:8000. Docs: /docs"""
    if db_path:
        import os
        os.environ["TASKUL_DB"] = db_path
    import uvicorn
    uvicorn.run(
        "taskul.api.app:app",
        host=host,
        port=port,
        reload=False,
    )
