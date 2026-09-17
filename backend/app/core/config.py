from pathlib import Path
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "CineTrack API"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    
    # CORS
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://usuario:password@localhost:5432/cinetrack"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def validate_database_url(cls, v: str) -> str:
        if isinstance(v, str):
            if v.startswith("postgresql://"):
                return v.replace("postgresql://", "postgresql+asyncpg://", 1)
            elif v.startswith("sqlite"):
                if not v.startswith("sqlite+aiosqlite://"):
                    v = v.replace("sqlite://", "sqlite+aiosqlite://", 1)
                prefix = "sqlite+aiosqlite:///"
                if v.startswith(prefix) and not v.startswith("sqlite+aiosqlite:////") and ":memory:" not in v:
                    rel_path = v[len(prefix):]
                    root_dir = Path(__file__).resolve().parents[3]
                    abs_db_path = (root_dir / rel_path).resolve().as_posix()
                    return f"sqlite+aiosqlite:///{abs_db_path}"
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
    TMDB_DAILY_SYNC_DAYS_WINDOW: int = 15
    TMDB_CHANGES_HOURS_WINDOW: int = 48
    TMDB_DAILY_SYNC_POP_THRESHOLD: float = 10.0
    TMDB_INGEST_PRIORITY: str = "popular_first"  # "popular_first" o "toprated_first"
    TMDB_REVIEWS_PER_TITLE_LIMIT: int = 20
    TMDB_ALLOW_UNRELEASED: bool = False

    # Admin Key para endpoints administrativos y automatizaciones
    ADMIN_API_KEY: str = "cinetrack-dev-admin-secret-key"

    # AI Recommender (Híbrido: Gemini Primario + Groq Fallback)
    GEMINI_API_KEY: str = ""
    GROQ_API_KEY: str = ""
    AI_RECOMMENDER_PRIMARY: str = "gemini"  # "gemini" o "groq"

    # Home Sections & Pools Configuration
    HOME_SECTION_SAMPLE_SIZE: int = 10
    HOME_NEW_RELEASES_DAYS: int = 30
    HOME_TRENDING_DAYS: int = 90
    HOME_TRENDING_MIN_POPULARITY_PERCENTILE: float = 0.80
    HOME_CLASSICS_MIN_YEARS: int = 20
    HOME_CLASSICS_MIN_RATING: float = 7.5
    HOME_CLASSICS_MIN_VOTES: int = 500
    HOME_CLASSICS_POOL_SIZE: int = 50
    HOME_TOP_RATED_MIN_VOTES: int = 100
    HOME_TOP_RATED_POOL_SIZE: int = 100
    HOME_GENRE_POOL_SIZE: int = 100
    HOME_GENRE_MIN_TITLES_FOR_CAROUSEL: int = 10

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", ".env.local"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
