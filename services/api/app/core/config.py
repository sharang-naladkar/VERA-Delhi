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

    # Providers Configuration (Phase 02: Ollama / Qwen3 and Mock support)
    LLM_PROVIDER: str = "ollama"
    LLM_MODEL: str = "qwen3:8b"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_TIMEOUT_SECONDS: float = 60.0
    LLM_TEMPERATURE: float = 0.1

    OCR_PROVIDER: str = "unavailable"
    STT_PROVIDER: str = "unavailable"
    DEEPFAKE_PROVIDER: str = "unavailable"
    FACE_DETECTOR_PROVIDER: str = "opencv"
    MESONET_WEIGHTS_PATH: str | None = None
    VIDEO_MAX_FRAMES: int = 10
    VIDEO_SAMPLE_INTERVAL_SECONDS: float = 1.0
    MAX_MEDIA_FILE_SIZE_BYTES: int = 52428800  # 50 MB
    URL_CLASSIFIER_PROVIDER: str = "unavailable"
    APK_CLASSIFIER_PROVIDER: str = "unavailable"
    EMBEDDING_PROVIDER: str = "unavailable"


@lru_cache
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
