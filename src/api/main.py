import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from neo4j.exceptions import DriverError, Neo4jError

from src.api.routes import (
    certificates,
    health,
    models,
    pipeline,
    regulations,
)
from src.api.spa import mount_frontend
from src.lib.model_bundle import BundleStorageError

logger = logging.getLogger(__name__)

IS_PRODUCTION = os.environ.get("ENVIRONMENT") == "production"

# The API schema is not public in production.
app = FastAPI(
    title="Rego API",
    version="0.1.0",
    docs_url=None if IS_PRODUCTION else "/docs",
    redoc_url=None if IS_PRODUCTION else "/redoc",
    openapi_url=None if IS_PRODUCTION else "/openapi.json",
)

GRAPH_UNAVAILABLE = (
    "The knowledge graph is temporarily unavailable. Please try again shortly."
)


@app.exception_handler(DriverError)
@app.exception_handler(Neo4jError)
async def graph_unavailable(request: Request, exc: Exception) -> JSONResponse:
    """A Neo4j outage is a 503 with a plain message, not a 500 and not the
    driver's error text, which can name internal hosts."""
    logger.error("Neo4j unavailable error=%s", type(exc).__name__)
    return JSONResponse(status_code=503, content={"detail": GRAPH_UNAVAILABLE})


STORAGE_UNAVAILABLE = (
    "Model file storage is temporarily unavailable. Please try again shortly."
)


@app.exception_handler(BundleStorageError)
async def storage_unavailable(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Model file storage unavailable")
    return JSONResponse(status_code=503, content={"detail": STORAGE_UNAVAILABLE})


# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID & Timing Middleware
@app.middleware("http")
async def add_process_time_header(request: Request, call_next: Any) -> Any:
    start_time = time.time()
    request_id = str(uuid.uuid4())
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    response.headers["X-Request-ID"] = request_id
    return response

# Everything the app does lives under /api. /health also stays at the root for
# the platform health check (Railway).
API_PREFIX = "/api"
for router in (
    health.router,
    regulations.router,
    certificates.router,
    pipeline.router,
    models.router,
):
    app.include_router(router, prefix=API_PREFIX)
app.include_router(health.router)

# The built React app, when there is one (the production image has it).
mount_frontend(app, Path(os.environ.get("FRONTEND_DIST", "frontend/dist")))
