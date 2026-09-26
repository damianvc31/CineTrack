import os
from pathlib import Path
import re
from typing import Any
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from enum import Enum


class VarietyLevel(str, Enum):
    VERY_LOW = "VERY_LOW"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    VERY_HIGH = "VERY_HIGH"


class Settings(BaseSettings):
    PROJECT_NAME: str = "CineTrack API"
    VERSION: str = "1.7.4"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] | str = ["http://localhost:5173", "http://127.0.0.1:5173"]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> list[str]:
        if isinstance(v, str):
            v_str = v.strip()
            if not v_str:
                return []
            if v_str.startswith("[") and v_str.endswith("]"):
                import json
                try:
                    parsed = json.loads(v_str)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    pass
            return [item.strip() for item in v_str.split(",") if item.strip()]
        elif isinstance(v, (list, tuple)):
            return [str(item).strip() for item in v if str(item).strip()]
        return v

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://usuario:password@localhost:5432/cinetrack"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgres://"):
                v = v.replace("postgres://", "postgresql+asyncpg://", 1)
            elif v.startswith("postgresql://"):
                v = v.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif v.startswith("sqlite"):
                if not v.startswith("sqlite+aiosqlite://"):
                    v = v.replace("sqlite://", "sqlite+aiosqlite://", 1)
                prefix = "sqlite+aiosqlite:///"
                if v.startswith(prefix) and not v.startswith("sqlite+aiosqlite:////") and ":memory:" not in v:
                    rel_path = v[len(prefix):]
                    root_dir = Path(__file__).resolve().parents[3]
                    abs_db_path = (root_dir / rel_path).resolve().as_posix()
                    return f"sqlite+aiosqlite:///{abs_db_path}"

            # Normalizar sslmode=require para asyncpg
            if "sslmode=require" in v:
                v = v.replace("sslmode=require", "ssl=require")

            # Remover parámetros no soportados por asyncpg (ej. channel_binding de Neon)
            v = re.sub(r"[?&]channel_binding=[^&]+", "", v)
            if "?" not in v and "&" in v:
                v = v.replace("&", "?", 1)
        return v

    # Auth
    AUTH_SECRET_KEY: str = "temporary-dev-secret-key-change-in-production"

    # External APIs
    TMDB_API_KEY: str = ""
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    TMDB_LANGUAGE: str = "en-US"
    TMDB_INGEST_MOVIES_TARGET: int = 1000
    TMDB_INGEST_SERIES_TARGET: int = 1000
    TMDB_MIN_VOTE_COUNT: int = 100
    TMDB_CAST_LIMIT: int = 15
    TMDB_CREW_WRITERS_LIMIT: int = 3
    TMDB_RELEASES_DAYS_WINDOW: int = 15
    TMDB_CHANGES_DAYS_WINDOW: int = 7
    TMDB_DAILY_SYNC_POP_THRESHOLD: float = 10.0
    TMDB_INGEST_PRIORITY: str = "popular_first"  # "popular_first" o "toprated_first"
    TMDB_REVIEWS_PER_TITLE_LIMIT: int = 20
    TMDB_ALLOW_UNRELEASED: bool = False

    @property
    def TMDB_DAILY_SYNC_DAYS_WINDOW(self) -> int:
        return self.TMDB_RELEASES_DAYS_WINDOW

    @property
    def TMDB_CHANGES_HOURS_WINDOW(self) -> int:
        return self.TMDB_CHANGES_DAYS_WINDOW * 24

    # TMDB Expand Configuration (Criterio 1: Expansión por géneros vía /discover)
    TMDB_EXPAND_MIN_VOTE_COUNT: int = 300
    TMDB_EXPAND_MIN_VOTE_AVERAGE: float = 7.0
    TMDB_EXPAND_TITLES_PER_GENRE: int = 50
    TMDB_EXPAND_UPCOMING_TARGET: int = 10
    TMDB_EXPAND_UPCOMING_DAYS: int = 365

    # Ingesta de Fotos de Actores
    TMDB_ACTOR_PHOTOS_LIMIT: int = 500

    # Admin Key para endpoints administrativos y automatizaciones
    ADMIN_API_KEY: str = "cinetrack-dev-admin-secret-key"

    # AI Recommender (Híbrido con Cascada Multi-Nivel: Gemini / Groq + Fallback Heurístico)
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-3.6-flash"
    GEMINI_FALLBACK_MODELS: str = "gemini-3.8-flash,gemini-3.5-flash-lite,gemini-flash-lite-latest"
    GEMINI_EMBEDDING_MODEL: str = "gemini-embedding-001"
    EMBEDDING_DIMENSION: int = 768
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"
    GROQ_FALLBACK_MODELS: str = "openai/gpt-oss-20b,qwen/qwen3.8-27b"
    AI_REASONING_MODELS: str = "openai/gpt-oss-120b,openai/gpt-oss-20b,qwen/qwen3.8-27b"
    AI_RECOMMENDER_PRIMARY: str = "gemini"  # "gemini" o "groq"
    RECOMMENDATION_CANDIDATES_LIMIT: int = 20
    AI_RECOMMENDER_DEFAULT_VARIETY: VarietyLevel = VarietyLevel.MEDIUM
    AI_RECOMMENDER_MIN_VOTES_VECTOR: int = 25
    AI_RECOMMENDER_MIN_VOTES_THEMATIC: int = 80
    AI_RECOMMENDER_MIN_VOTES_FALLBACK: int = 150
    AI_RECOMMENDER_NEW_RELEASE_DAYS: int = 30

    @property
    def reasoning_models_set(self) -> set[str]:
        return {m.strip() for m in self.AI_REASONING_MODELS.split(",") if m.strip()}

    # Home Sections & Pools Configuration
    HOME_SECTION_SAMPLE_SIZE: int = 10
    HOME_NEW_RELEASES_DAYS: int = 30
    HOME_TRENDING_DAYS: int = 90
    HOME_TRENDING_MIN_POPULARITY_PERCENTILE: float = 0.80
    HOME_CLASSICS_MIN_YEARS: int = 20
    HOME_CLASSICS_MIN_RATING: float = 7.5
    HOME_CLASSICS_MIN_VOTES: int = 500
    HOME_CLASSICS_POOL_SIZE: int = 100
    HOME_TOP_RATED_MIN_VOTES: int = 500
    HOME_TOP_RATED_POOL_SIZE: int = 100
    HOME_GENRE_POOL_SIZE: int = 100
    HOME_GENRE_MIN_TITLES_FOR_CAROUSEL: int = 10

    # Cache Configuration (Memoria en backend)
    CACHE_HOME_TTL_SECONDS: int = 3600      # 1 hora para los pools de Home
    CACHE_CATALOG_TTL_SECONDS: int = 300     # 5 minutos para conteos y queries frecuentes

    @model_validator(mode="before")
    @classmethod
    def handle_legacy_env_aliases(cls, data: Any) -> Any:
        if isinstance(data, dict):
            if "TMDB_RELEASES_DAYS_WINDOW" not in data and "TMDB_DAILY_SYNC_DAYS_WINDOW" in data:
                data["TMDB_RELEASES_DAYS_WINDOW"] = data["TMDB_DAILY_SYNC_DAYS_WINDOW"]
            if "TMDB_CHANGES_DAYS_WINDOW" not in data and "TMDB_CHANGES_HOURS_WINDOW" in data:
                try:
                    data["TMDB_CHANGES_DAYS_WINDOW"] = max(1, int(data["TMDB_CHANGES_HOURS_WINDOW"]) // 24)
                except Exception:
                    pass
        return data

    @model_validator(mode="after")
    def validate_production_security(self) -> "Settings":
        if self.ENVIRONMENT == "production":
            import logging
            cfg_logger = logging.getLogger("config")
            if self.AUTH_SECRET_KEY == "temporary-dev-secret-key-change-in-production":
                cfg_logger.warning("ALERTA DE SEGURIDAD: AUTH_SECRET_KEY usa la clave insegura por defecto en entorno de producción.")
            if self.ADMIN_API_KEY == "cinetrack-dev-admin-secret-key":
                cfg_logger.warning("ALERTA DE SEGURIDAD: ADMIN_API_KEY usa la clave insegura por defecto en entorno de producción.")
        return self

    model_config = SettingsConfigDict(
        env_file=(os.getenv("ENV_FILE") or os.getenv("CINETRACK_ENV_FILE"),) if (os.getenv("ENV_FILE") or os.getenv("CINETRACK_ENV_FILE")) else (".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
