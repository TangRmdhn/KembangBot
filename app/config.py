"""Centralized configuration for Kembang AI backend.

All configuration values are loaded from environment variables or .env file.
This is the first module that every other module imports.

Usage:
    from app.config import settings

    if settings.is_production:
        # production-specific logic
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    All fields can be set via environment variables with the same name.
    For local development, create a .env file in the project root.

    Example .env:
        APP_ENV=development
        APP_SECRET_KEY=your-secret-key-here
        DATABASE_URL=postgresql+asyncpg://...
        OPENAI_API_KEY=sk-...
    """

    # --- App ---
    APP_ENV: str = "development"  # "development" | "staging" | "production"
    APP_DEBUG: bool = True
    APP_SECRET_KEY: str
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:3001"

    # --- Database ---
    DATABASE_URL: str = "postgresql+asyncpg://kembang:kembang@localhost:5432/kembang"
    DATABASE_URL_SYNC: str = "postgresql+psycopg://kembang:kembang@localhost:5432/kembang"
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20

    # --- Redis ---
    REDIS_URL: str = "redis://localhost:6379/0"

    # --- WAHA ---
    WAHA_BASE_URL: str
    WAHA_API_KEY: str = ""
    WAHA_WEBHOOK_SECRET: str

    # --- OpenAI ---
    OPENAI_API_KEY: str

    # --- MinIO / S3 ---
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "kembang-media"
    MINIO_USE_SSL: bool = False

    # --- Rate Limiting ---
    RATE_LIMIT_PER_MINUTE: int = 30
    RATE_LIMIT_PER_HOUR: int = 200

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.APP_ENV == "development"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance.

    Returns:
        Singleton Settings instance.
    """
    return Settings()


# Global settings instance
settings = get_settings()
