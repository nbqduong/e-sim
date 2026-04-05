from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import auth, documents, projects
from app.core.config import settings
from app.core.database import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if settings.session_secret == "change-me":
        raise RuntimeError("SESSION_SECRET must be set to a secure value")
    # Verify DB connectivity on startup
    if engine:
        async with engine.connect() as conn:
            await conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        logger.info("Database connection verified")
    yield
    if engine:
        await engine.dispose()


app = FastAPI(
    title=settings.project_name,
    version=settings.api_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(auth.router, prefix="/auth")
app.include_router(projects.router)
app.include_router(documents.router)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now(tz=timezone.utc).isoformat()}

# Attempt to locate the frontend 'out' directory
if settings.frontend_dist_dir:
    frontend_dist = settings.frontend_dist_dir
else:
    frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend_output"))
    if not os.path.isdir(frontend_dist):
        frontend_dist = "/app/frontend/out"

if os.path.isdir(frontend_dist):
    next_dist = os.path.join(frontend_dist, "_next")
    if os.path.isdir(next_dist):
        app.mount("/_next", StaticFiles(directory=next_dist), name="next-static")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Never intercept API or auth routes
        if full_path.startswith(("api/", "auth/", "health")):
            return {"error": "Not found"}

        # Normalize the path by removing trailing slash for consistent matching
        full_path = full_path.rstrip("/")
        
        file_path = os.path.join(frontend_dist, full_path)
        
        # 1. Check if the exact file exists (like an image or .js file)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
        
        # 2. Check if the path corresponds directly to a Next.js HTML output
        if full_path:
            html_path = f"{file_path}.html"
            if os.path.isfile(html_path):
                return FileResponse(html_path)
                
        # 3. Check if the path targets a directory containing an index.html
        if os.path.isdir(file_path):
            index_path = os.path.join(file_path, "index.html")
            if os.path.isfile(index_path):
                return FileResponse(index_path)
        
        # 4. Fallback to the SPA root index.html if no route matched
        root_index = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(root_index):
            return FileResponse(root_index)
        
        return {"error": "Frontend build not found"}
