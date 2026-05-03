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
    session_cookie_secure: bool = Field(default=False, alias="SESSION_COOKIE_SECURE")
    state_ttl_seconds: int = Field(default=300, alias="STATE_TTL_SECONDS")
    data_dir: Path = Field(default=Path("./data"), alias="DATA_DIR")
    database_url: str = Field(default="", alias="DATABASE_URL")

    google_client_id: str | None = Field(default=None, alias="GOOGLE_CLIENT_ID")
    google_client_secret: str | None = Field(default=None, alias="GOOGLE_CLIENT_SECRET")
    google_redirect_uri: str = Field(
        default="http://localhost:8000/auth/google/callback", alias="GOOGLE_REDIRECT_URI"
    )
    frontend_dist_dir: str = Field(default="", alias="FRONTEND_DIST_DIR")

    cors_allow_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:5173", "http://localhost:3000", "http://localhost:8000"],
        alias="CORS_ALLOW_ORIGINS",
    )
    redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")
    gcs_bucket_name: str | None = Field(default=None, validation_alias="GCS_BUCKET_NAME")
    gcs_upload_prefix: str = Field(default="e-sim", validation_alias="GCS_UPLOAD_PREFIX")
    gcs_signing_service_account: str | None = Field(
        default=None,
        validation_alias="GCS_SIGNING_SERVICE_ACCOUNT",
    )
    max_upload_size_bytes: int = Field(
        default=10 * 1024 * 1024,
        validation_alias="PROJECT_CONTENT_MAX_UPLOAD_SIZE_BYTES",
    )
    signed_url_expiration_seconds: int = Field(
        default=900,
        validation_alias="SIGNED_URL_EXPIRATION_SECONDS",
    )
    storage_rate_limit_max_requests: int = Field(
        default=30,
        validation_alias="STORAGE_RATE_LIMIT_MAX_REQUESTS",
    )
    storage_rate_limit_window_seconds: int = Field(
        default=60,
        validation_alias="STORAGE_RATE_LIMIT_WINDOW_SECONDS",
    )
    project_create_rate_limit_max_requests: int = Field(
        default=10,
        validation_alias="PROJECT_CREATE_RATE_LIMIT_MAX_REQUESTS",
    )
    project_create_rate_limit_window_seconds: int = Field(
        default=60,
        validation_alias="PROJECT_CREATE_RATE_LIMIT_WINDOW_SECONDS",
    )
    global_rate_limit_enabled: bool = Field(
        default=True,
        validation_alias="GLOBAL_RATE_LIMIT_ENABLED",
    )
    global_rate_limit_max_requests: int = Field(
        default=120,
        validation_alias="GLOBAL_RATE_LIMIT_MAX_REQUESTS",
    )
    global_rate_limit_window_seconds: int = Field(
        default=60,
        validation_alias="GLOBAL_RATE_LIMIT_WINDOW_SECONDS",
    )
    global_rate_limit_fail_open: bool = Field(
        default=True,
        validation_alias="GLOBAL_RATE_LIMIT_FAIL_OPEN",
    )
    billing_free_max_projects: int = Field(
        default=3,
        validation_alias="BILLING_FREE_MAX_PROJECTS",
    )
    billing_pro_max_projects: int = Field(
        default=25,
        validation_alias="BILLING_PRO_MAX_PROJECTS",
    )

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"

    def ensure_data_dir(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
