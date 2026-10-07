"""Serve the built React app from the API, for a single-service deploy.

The API lives under /api (and /health for the platform health check). Anything
else is the frontend: real files from the build, and index.html for every other
path so that a deep link or a page reload on /approval-queue works.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

RESERVED_PREFIXES = ("api", "health")


def is_reserved(path: str) -> bool:
    first = path.strip("/").split("/", 1)[0]
    return first in RESERVED_PREFIXES


def mount_frontend(app: FastAPI, dist: Path) -> bool:
    """Serve `dist` if it holds a build. Returns whether it did."""
    index = dist / "index.html"
    if not index.is_file():
        return False
    root = dist.resolve()
    if (dist / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=dist / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str) -> FileResponse:
        if is_reserved(path):
            # An unknown API route must stay a 404, not turn into the login page.
            raise HTTPException(status_code=404, detail="Not found.")
        candidate = (dist / path).resolve()
        if path and candidate.is_file() and root in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)

    return True
