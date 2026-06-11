from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Server
    SECRET_KEY: str = "change-me-in-production"
    DEBUG: bool = False
    ALLOWED_ORIGINS: List[str] = ["http://localhost:3000"]
    API_PREFIX: str = "/api/v1"
    APP_NAME: str = "Man Matters Creative OS"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/man_matters_cos"

    # Redis / Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/1"

    # Supabase
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "man-matters-creatives"

    # Google AI
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-pro"
    EMBEDDING_MODEL: str = "text-embedding-004"
    EMBEDDING_DIMENSION: int = 768

    # Meta Marketing API
    META_APP_ID: str = ""
    META_APP_SECRET: str = ""
    META_ACCESS_TOKEN: str = ""
    META_AD_ACCOUNT_ID: str = ""
    META_API_VERSION: str = "v21.0"

    # Sync
    META_SYNC_LOOKBACK_DAYS: int = 30
    META_SYNC_INTERVAL_HOURS: int = 6

    # Features
    ENABLE_AUTO_ANALYSIS: bool = True
    ENABLE_COMPETITOR_SYNC: bool = True
    ENABLE_FATIGUE_ALERTS: bool = True
    MIN_SPEND_FOR_ANALYSIS: float = 500.0

    # Fatigue thresholds
    FATIGUE_HEALTHY_MAX: float = 30.0
    FATIGUE_WATCH_MAX: float = 60.0
    FATIGUE_FATIGUING_MAX: float = 80.0

    # Winner / Loser classification
    WINNER_ROAS_PERCENTILE: float = 0.75  # top 25% = winners
    LOSER_ROAS_PERCENTILE: float = 0.25   # bottom 25% = losers
    MIN_SPEND_FOR_CLASSIFICATION: float = 2000.0

    # Sentry
    SENTRY_DSN: str = ""

    # JWT
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days


settings = Settings()
