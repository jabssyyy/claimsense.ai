"""
ClaimSense.ai - Application Configuration

Loads settings from environment variables and .env file.
Uses pydantic-settings for type validation and automatic .env loading.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # Google Gemini API
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"

    # PostgreSQL Database
    DATABASE_URL: str = "postgresql://claimsense:password@localhost:5432/claimsense"

    # Application
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    UPLOAD_DIR: str = "./uploads"
    DEBUG: bool = False

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000


@lru_cache
def get_settings() -> Settings:
    """
    Get application settings (cached).

    Settings are loaded once from .env file and environment variables.
    Environment variables take precedence over .env file values.
    """
    return Settings()
