
from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env")


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value.strip()


def _optional_env(name: str, default: str) -> str:
    value = os.getenv(name)
    return default if value is None or value.strip() == "" else value.strip()


def _optional_int_env(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be an integer") from exc


def _optional_bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_name: str
    mongodb_url: str
    mongodb_db_name: str
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    frontend_url: str
    upload_dir: str
    max_upload_size_mb: int
    use_openai_extraction: bool
    openai_api_key: str

    @property
    def cors_origins(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.frontend_url.split(",")
            if origin.strip()
        ]

    @property
    def cors_origin_regex(self) -> str:
        return (
            r"^https?://("
            r"localhost|127\.0\.0\.1|0\.0\.0\.0|"
            r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
            r"192\.168\.\d{1,3}\.\d{1,3}|"
            r"172\.(1[6-9]|2\d|3[0-1])\.\d{1,3}\.\d{1,3}"
            r")(:\d+)?$"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings(
        app_name=_optional_env("APP_NAME", "EduMatch Resource Mapping API"),
        mongodb_url=_required_env("MONGODB_URL"),
        mongodb_db_name=_required_env("MONGODB_DB_NAME"),
        jwt_secret_key=_required_env("JWT_SECRET_KEY"),
        jwt_algorithm=_optional_env("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=_optional_int_env(
            "ACCESS_TOKEN_EXPIRE_MINUTES",
            60,
        ),
        frontend_url=_optional_env("FRONTEND_URL", "http://localhost:5173"),
        upload_dir=_optional_env("UPLOAD_DIR", "uploads"),
        max_upload_size_mb=_optional_int_env("MAX_UPLOAD_SIZE_MB", 20),
        use_openai_extraction=_optional_bool_env("USE_OPENAI_EXTRACTION", False),
        openai_api_key=_optional_env("OPENAI_API_KEY", ""),
    )
