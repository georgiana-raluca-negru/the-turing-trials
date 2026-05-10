# backend/app/core/config.py
"""
Centralised settings — reads from environment variables / .env file.
Every value has a safe default so the app still boots without a full .env.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",          # loaded by Docker via environment: block
        env_file_encoding="utf-8",
        extra="ignore",           # ignore unknown env vars
    )

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://admin:admin@localhost:5432/postgres"

    # ── JWT ───────────────────────────────────────────────────────────────────
    # IMPORTANT: set a real random secret in production!
    JWT_SECRET_KEY: str = "CHANGE_ME_super_secret_key_at_least_32_chars"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── OAuth — Google ────────────────────────────────────────────────────────
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8001/api/auth/oauth/google/callback"

    # ── OAuth — GitHub ────────────────────────────────────────────────────────
    GITHUB_CLIENT_ID: str = ""
    GITHUB_CLIENT_SECRET: str = ""
    GITHUB_REDIRECT_URI: str = "http://localhost:8001/api/auth/oauth/github/callback"

    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "The Turing Trials"
    DEBUG: bool = False


# Single shared instance — import this everywhere
settings = Settings()
