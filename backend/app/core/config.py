from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    project_name: str = Field(default="e-sim Backend Service", alias="PROJECT_NAME")
    api_version: str = Field(default="1.0.0", alias="API_VERSION")
    session_secret: str = Field(default="change-me", alias="SESSION_SECRET")
    session_ttl_seconds: int = Field(default=60 * 60 * 24, alias="SESSION_TTL_SECONDS")
    state_ttl_seconds: int = Field(default=300, alias="STATE_TTL_SECONDS")
    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")

    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback", alias="GOOGLE_REDIRECT_URI"
    )
    google_drive_parent_id: str | None = Field(default=None, alias="GOOGLE_DRIVE_PARENT_ID")

    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000"],
        alias="CORS_ALLOW_ORIGINS",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
