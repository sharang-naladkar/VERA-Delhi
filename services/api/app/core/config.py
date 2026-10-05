"""Application settings and environment configuration."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # General
    APP_ENV: str = "development"
    APP_NAME: str = "VERA"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True
    PORT: int = 8000
    HOST: str = "0.0.0.0"

    # CORS
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    # Database
    DATABASE_URL: str = "postgresql+psycopg://vera_user:vera_password@postgres:5432/vera_db"

    # Redis Cache & Queues
    REDIS_URL: str = "redis://redis:6379/0"

    # Object Storage (MinIO / S3)
    MINIO_ENDPOINT: str = "http://minio:9000"
    MINIO_ACCESS_KEY: str = "vera_minio_admin"
    MINIO_SECRET_KEY: str = "vera_minio_secret"
    MINIO_BUCKET: str = "vera-artifacts"
    MINIO_SECURE: bool = False

    # Providers Configuration (Phase 01: Interfaces with unavailable fallbacks)
    LLM_PROVIDER: str = "unavailable"
    LLM_MODEL: str = "qwen3:32b"

    OCR_PROVIDER: str = "unavailable"
    STT_PROVIDER: str = "unavailable"
    DEEPFAKE_PROVIDER: str = "unavailable"
    URL_CLASSIFIER_PROVIDER: str = "unavailable"
    APK_CLASSIFIER_PROVIDER: str = "unavailable"
    EMBEDDING_PROVIDER: str = "unavailable"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
