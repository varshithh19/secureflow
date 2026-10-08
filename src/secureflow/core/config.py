"""[VULNERABLE VERSION - v0-insecure]

VUL-01: Hardcoded secret key for JWT and application cryptography.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # VUL-01: Hardcoded cryptographic key in source code
    SECRET_KEY: str = "hardcoded-insecure-secret-123"
    JWT_SECRET_KEY: str = "hardcoded-insecure-secret-123"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_HOURS: int = 8
    DATABASE_URL: str = "sqlite:///./secureflow.db"
    DEBUG: bool = True
    DEMO_MODE: bool = True
    CONTROLLER_SIGNING_KEY: str = "controller-secret-hmac-key-256bit-min-32-chars"
    CONTROLLER_API_URL: str = "http://localhost:8010/api/controller/apply"
    RATE_LIMIT_DEFAULT: str = "100/minute"
    RATE_LIMIT_TELEMETRY: str = "120/minute"
    RATE_LIMIT_AUTH: str = "10/minute"


def get_settings() -> Settings:
    return Settings()
