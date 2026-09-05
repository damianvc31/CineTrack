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
        if isinstance(v, str) and v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    # Auth
    AUTH_SECRET_KEY: str = "temporary-dev-secret-key-change-in-production"

    # External APIs
    TMDB_API_KEY: str = ""
    TMDB_BASE_URL: str = "https://api.themoviedb.org/3"
    TMDB_INGEST_MOVIES_TARGET: int = 1000
    TMDB_INGEST_SERIES_TARGET: int = 1000
    TMDB_MIN_VOTE_COUNT: int = 100
    TMDB_CAST_LIMIT: int = 15
    TMDB_CREW_WRITERS_LIMIT: int = 3
    TMDB_DAILY_SYNC_DAYS_WINDOW: int = 15
    TMDB_DAILY_SYNC_POP_THRESHOLD: float = 10.0
    TMDB_INGEST_PRIORITY: str = "popular_first"  # "popular_first" o "toprated_first"

    AI_PROVIDER_API_KEY: str = ""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
