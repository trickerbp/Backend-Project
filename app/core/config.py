
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

def _optional_float_env(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise RuntimeError(f"Environment variable {name} must be a number") from exc


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
    openai_extraction_model: str
    openai_extraction_max_input_chars: int
    openai_extraction_max_output_tokens: int
    openai_extraction_min_missing_fields: int
    openai_extraction_timeout_seconds: float
    use_embedding_matching: bool
    openai_embedding_model: str
    openai_embedding_dimensions: int
    openai_embedding_timeout_seconds: float
    openai_embedding_max_input_chars: int
    openai_embedding_skip_if_local_at_least: float
    openai_embedding_skip_if_local_below: float
    openai_embedding_expand_low_confidence: bool
    use_azure_document_intelligence: bool
    azure_document_intelligence_endpoint: str
    azure_document_intelligence_key: str
    ocr_min_text_chars: int

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
        openai_extraction_model=_optional_env(
            "OPENAI_EXTRACTION_MODEL",
            "gpt-5.4-mini",
        ),
        openai_extraction_max_input_chars=_optional_int_env(
            "OPENAI_EXTRACTION_MAX_INPUT_CHARS",
            3500,
        ),
        openai_extraction_max_output_tokens=_optional_int_env(
            "OPENAI_EXTRACTION_MAX_OUTPUT_TOKENS",
            800,
        ),
        openai_extraction_min_missing_fields=_optional_int_env(
            "OPENAI_EXTRACTION_MIN_MISSING_FIELDS",
            2,
        ),
        openai_extraction_timeout_seconds=_optional_float_env(
            "OPENAI_EXTRACTION_TIMEOUT_SECONDS",
            12.0,
        ),
        use_embedding_matching=_optional_bool_env("USE_EMBEDDING_MATCHING", False),
        openai_embedding_model=_optional_env(
            "OPENAI_EMBEDDING_MODEL",
            "text-embedding-3-small",
        ),
        openai_embedding_dimensions=_optional_int_env(
            "OPENAI_EMBEDDING_DIMENSIONS",
            0,
        ),
        openai_embedding_timeout_seconds=_optional_float_env(
            "OPENAI_EMBEDDING_TIMEOUT_SECONDS",
            8.0,
        ),
        openai_embedding_max_input_chars=_optional_int_env(
            "OPENAI_EMBEDDING_MAX_INPUT_CHARS",
            900,
        ),
        openai_embedding_skip_if_local_at_least=_optional_float_env(
            "OPENAI_EMBEDDING_SKIP_IF_LOCAL_AT_LEAST",
            0.72,
        ),
        openai_embedding_skip_if_local_below=_optional_float_env(
            "OPENAI_EMBEDDING_SKIP_IF_LOCAL_BELOW",
            0.12,
        ),
        openai_embedding_expand_low_confidence=_optional_bool_env(
            "OPENAI_EMBEDDING_EXPAND_LOW_CONFIDENCE",
            False,
        ),
        use_azure_document_intelligence=_optional_bool_env(
            "USE_AZURE_DOCUMENT_INTELLIGENCE",
            False,
        ),
        azure_document_intelligence_endpoint=_optional_env(
            "AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT",
            "",
        ),
        azure_document_intelligence_key=_optional_env(
            "AZURE_DOCUMENT_INTELLIGENCE_KEY",
            "",
        ),
        ocr_min_text_chars=_optional_int_env("OCR_MIN_TEXT_CHARS", 300),
    )
