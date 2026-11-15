"""Environment-backed settings. Secrets stay in the environment, never in code."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BACKEND_DIR / ".env"


class Settings(BaseSettings):
    """Runtime configuration loaded from the environment and an optional .env file."""

    app_name: str = "Tuition Center MIS"
    app_env: str = "development"
    secret_key: str = Field(min_length=16)
    database_url: str
    access_token_minutes: int = 15
    refresh_token_days: int = 7
    password_reset_minutes: int = 30
    cors_origins: str = "http://localhost:5173"
    frontend_url: str = "http://localhost:5173"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    login_rate_limit: int = 10
    login_rate_window_seconds: int = 60
    max_failed_logins: int = 5
    lockout_minutes: int = 15
    start_scheduler: bool = True
    trust_proxy: bool = False
    seed_admin_email: str = "admin@tuition.example"
    seed_admin_password: str = "Admin@12345"
    seed_admin_name: str = "System Administrator"
    upload_dir: str = ""
    max_upload_bytes: int = 5_242_880

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE) if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @field_validator("cookie_samesite")
    @classmethod
    def _samesite(cls, value: str) -> str:
        allowed = {"lax", "strict", "none"}
        lowered = value.lower()
        if lowered not in allowed:
            raise ValueError("COOKIE_SAMESITE must be lax, strict, or none")
        return lowered

    @field_validator("app_env")
    @classmethod
    def _env(cls, value: str) -> str:
        return value.lower()

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"

    @property
    def upload_path(self) -> Path:
        """Directory for student documents. Relative paths stay inside the backend tree."""
        raw = self.upload_dir.strip()
        path = Path(raw) if raw else BACKEND_DIR / "var" / "uploads"
        return path if path.is_absolute() else BACKEND_DIR / path


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings object."""
    settings = Settings()  # type: ignore[call-arg]
    if settings.is_production and len(settings.secret_key) < 32:
        raise RuntimeError("SECRET_KEY must be at least 32 characters in production")
    if settings.is_production and settings.seed_admin_password == "Admin@12345":
        raise RuntimeError("Replace SEED_ADMIN_PASSWORD before running in production")
    return settings
