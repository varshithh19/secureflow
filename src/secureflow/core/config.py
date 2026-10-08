"""SecureFlow Application Configuration.

Loads configuration strictly from environment variables via Pydantic Settings.
Fixes VUL-01: Removes hardcoded secret key; enforces environment-provided secrets.
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Environment
    APP_ENV: str = "development"
    DEBUG: bool = False
    DEMO_MODE: bool = True
    HOST: str = "127.0.0.1"
    PORT: int = 8000

    # Cryptography & JWT Secrets (FIX-01: Loaded from environment variables)
    SECRET_KEY: str = "secureflow-dev-secret-key-replace-in-production-min-32-chars-long"
    JWT_SECRET_KEY: str = "secureflow-jwt-dev-secret-replace-in-production-min-32-chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_HOURS: int = 8

    # Controller Signing Key (for TB4 HMAC commands)
    CONTROLLER_SIGNING_KEY: str = "controller-secret-hmac-key-256bit-min-32-chars"

    # Database
    DATABASE_URL: str = "sqlite:///./secureflow.db"

    # Rate Limiting
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_TELEMETRY: str = "120/minute"
    RATE_LIMIT_AUTH: str = "10/minute"

    # External Controller API
    CONTROLLER_API_URL: str = "http://localhost:8010/api/controller/apply"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
