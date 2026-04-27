from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.deps import get_state_cache
from app.api.routes import auth, legal, projects, tickets, users
from app.core.config import settings
from app.core.database import engine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

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
    if get_state_cache.cache_info().currsize:
        await get_state_cache().close()
        get_state_cache.cache_clear()
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
app.include_router(legal.router)
app.include_router(projects.router)
app.include_router(tickets.router)
app.include_router(users.router)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now(tz=timezone.utc).isoformat()}

# Attempt to locate the frontend 'out' directory
if settings.frontend_dist_dir:
    frontend_dist = settings.frontend_dist_dir
else:
    frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "frontend__output"))
    if not os.path.isdir(frontend_dist):
        frontend_dist = "/app/frontend/out"

logger.info(f"Resolved frontend_dist: {frontend_dist}")
logger.info(f"Does frontend_dist exist? {os.path.isdir(frontend_dist)}")

if os.path.isdir(frontend_dist):
    next_dist = os.path.join(frontend_dist, "assets")
    if os.path.isdir(next_dist):
        logger.info(f"Mounting assets from: {next_dist}")
        app.mount("/assets", StaticFiles(directory=next_dist), name="vite-assets")
    else:
        logger.warning(f"Assets directory not found at: {next_dist}")
        
    if os.path.isdir(next_dist):
        logger.info(f"Mounting demoui assets from: {next_dist}")
        app.mount("/demoui/assets", StaticFiles(directory=next_dist), name="vite-assets-demoui")
    
    @app.get("/{full_path:path}")
    async def serve_frontend(full_path: str):
        # Never intercept API or auth routes
        if full_path.startswith(("api/", "auth/", "health")):
            return {"error": "Not found"}

        # Normalize the path by removing trailing slash for consistent matching
        full_path = full_path.rstrip("/")

        # Strip the Vite base path prefix if it is present
        virtual_path = full_path
        if full_path.startswith("demoui"):
            virtual_path = full_path[len("demoui"):].lstrip("/")
        
        file_path = os.path.join(frontend_dist, virtual_path)
        logger.info(f"Requested static path: '{full_path}' -> Expected file path: {file_path}")
        
        # 1. Check if the exact file exists (like an image or .js file)
        if virtual_path and os.path.isfile(file_path):
            logger.info(f"Serving exact file: {file_path}")
            return FileResponse(file_path)
        
        # 2. Check if the path corresponds directly to a Next.js HTML output
        if virtual_path:
            html_path = f"{file_path}.html"
            if os.path.isfile(html_path):
                logger.info(f"Serving HTML file: {html_path}")
                return FileResponse(html_path)
                
        # 3. Check if the path targets a directory containing an index.html
        if os.path.isdir(file_path):
            index_path = os.path.join(file_path, "index.html")
            if os.path.isfile(index_path):
                logger.info(f"Serving directory index: {index_path}")
                return FileResponse(index_path)
        
        # 4. Fallback to the SPA root index.html if no route matched
        root_index = os.path.join(frontend_dist, "index.html")
        if os.path.isfile(root_index):
            logger.info(f"Fallback to SPA root: {root_index}")
            return FileResponse(root_index)
        
        logger.warning(f"Frontend built file not found for path: {full_path}")
        return {"error": "Frontend build not found"}
else:
    logger.warning(f"Frontend directory {frontend_dist} does not exist. Frontend serving is disabled.")
