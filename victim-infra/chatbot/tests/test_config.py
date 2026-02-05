"""Tests for configuration module."""

import pytest
import os
from unittest.mock import patch


class TestSettings:
    """Tests for Settings class."""

    def test_default_settings(self):
        """Settings have sensible defaults."""
        with patch.dict(os.environ, {}, clear=True):
            # Clear the cache and reimport
            from app.config import Settings
            settings = Settings()
            assert settings.aws_region == "us-east-1"
            assert settings.app_title == "AI Data Analyst"
            assert settings.app_version == "1.0.0"
            assert settings.log_level == "INFO"

    def test_code_interpreter_id_optional(self):
        """Code interpreter ID can be None."""
        with patch.dict(os.environ, {}, clear=True):
            from app.config import Settings
            settings = Settings()
            assert settings.code_interpreter_id is None

    def test_code_interpreter_arn_optional(self):
        """Code interpreter ARN can be None."""
        with patch.dict(os.environ, {}, clear=True):
            from app.config import Settings
            settings = Settings()
            assert settings.code_interpreter_arn is None

    def test_settings_from_env(self):
        """Settings load from environment variables."""
        env_vars = {
            "AWS_REGION": "us-west-2",
            "CODE_INTERPRETER_ID": "test-interpreter-123",
            "APP_TITLE": "Test App",
            "LOG_LEVEL": "DEBUG"
        }
        with patch.dict(os.environ, env_vars, clear=True):
            from app.config import Settings
            settings = Settings()
            assert settings.aws_region == "us-west-2"
            assert settings.code_interpreter_id == "test-interpreter-123"
            assert settings.app_title == "Test App"
            assert settings.log_level == "DEBUG"

    def test_get_settings_cached(self):
        """get_settings returns cached instance."""
        from app.config import get_settings
        # Get settings twice
        settings1 = get_settings()
        settings2 = get_settings()
        # Should be the same cached instance
        assert settings1 is settings2
