"""
Configuration management using pydantic-settings.

This module provides centralized configuration for the victim chatbot application.
Settings are loaded from environment variables with sensible defaults.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AWS Configuration
    aws_region: str = "us-east-1"

    # Code Interpreter Configuration
    code_interpreter_id: str | None = None
    code_interpreter_arn: str | None = None

    # Application Configuration
    app_title: str = "AI Data Analyst"
    app_version: str = "1.0.0"
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Settings are cached to avoid re-reading environment on every call.
    """
    return Settings()
