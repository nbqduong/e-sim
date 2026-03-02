from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import UTC, datetime

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import auth, documents
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):  # pragma: no cover - FastAPI hook
    settings.ensure_data_dir()
    yield


app = FastAPI(
    title=settings.project_name,
    version=settings.api_version,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins or ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

app.include_router(auth.router, prefix="/auth")
app.include_router(documents.router)


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok", "timestamp": datetime.now(tz=UTC).isoformat()}
