"""
Application Configuration

Reads all config from environment variables.
Uses Pydantic Settings so every field is typed and validated at startup.
A misconfigured environment (missing JWT_SECRET, bad DB URL, etc.)
fails fast with a clear error before serving any requests.
"""

from functools import lru_cache
from typing import List

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_env: str = "development"
    log_level: str = "INFO"
    service_name: str = "user-service"

    # PostgreSQL
    database_url: str  # Required — no default
    # Sync URL for Alembic migrations (asyncpg doesn't support Alembic directly)
    database_url_sync: str = ""

    # Connection pool settings
    db_pool_size: int = 10
    db_max_overflow: int = 20
    db_pool_timeout: int = 30

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    jwt_secret: str  # Required — no default
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7

    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]

    # Rate limits (requests per minute)
    rate_limit_login: int = 10
    rate_limit_register: int = 5
    rate_limit_general: int = 100

    @field_validator("jwt_secret")
    @classmethod
    def jwt_secret_must_be_long_enough(cls, value: str) -> str:
        if len(value) < 32:
            raise ValueError("JWT_SECRET must be at least 32 characters long")
        return value

    @field_validator("database_url")
    @classmethod
    def database_url_must_use_asyncpg(cls, value: str) -> str:
        if "postgresql" not in value:
            raise ValueError("DATABASE_URL must be a PostgreSQL connection string")
        return value

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


# Cache the settings object — reads env vars only once
@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
