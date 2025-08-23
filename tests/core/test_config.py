"""Tests for configuration management."""

import os
from unittest.mock import patch

import pytest

from core.config import Environment, Settings


class TestEnvironment:
    """Test environment enum."""

    def test_environment_values(self) -> None:
        """Test environment enum values."""
        assert Environment.DEVELOPMENT == "development"
        assert Environment.PRODUCTION == "production"
        assert Environment.TESTING == "testing"


class TestSettings:
    """Test settings class."""

    def test_default_settings(self) -> None:
        """Test default settings values."""
        with patch.dict(os.environ, {}, clear=True):
            settings = Settings()

            assert settings.environment == Environment.DEVELOPMENT
            assert settings.api_title == "TheArk API"
            assert settings.api_version == "1.0.0"
            assert settings.cors_allow_origins == ["*"]
            assert settings.auth_required is False
            assert settings.auth_header_name == "Authorization"
            assert settings.log_level == "INFO"

    def test_development_mode_properties(self) -> None:
        """Test development mode properties."""
        with patch.dict(os.environ, {"THEARK_ENV": "development"}, clear=True):
            settings = Settings()

            assert settings.is_development is True
            assert settings.is_production is False
            assert settings.is_testing is False
            assert settings.auth_required is False

    def test_production_mode_properties(self) -> None:
        """Test production mode properties."""
        with patch.dict(os.environ, {"THEARK_ENV": "production"}, clear=True):
            from core.config import load_settings

            settings = load_settings()

            assert settings.is_development is False
            assert settings.is_production is True
            assert settings.is_testing is False
            assert settings.auth_required is True

    def test_testing_mode_properties(self) -> None:
        """Test testing mode properties."""
        with patch.dict(os.environ, {"THEARK_ENV": "testing"}, clear=True):
            from core.config import load_settings

            settings = load_settings()

            assert settings.is_development is False
            assert settings.is_production is False
            assert settings.is_testing is True
            assert settings.auth_required is False

    def test_custom_settings(self) -> None:
        """Test custom settings via environment variables."""
        env_vars = {
            "THEARK_ENV": "production",
            "THEARK_API_TITLE": "Custom API",
            "THEARK_API_VERSION": "2.0.0",
            "THEARK_CORS_ORIGINS": "https://example.com,https://test.com",
            "THEARK_AUTH_HEADER": "X-API-Key",
            "THEARK_LOG_LEVEL": "DEBUG",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            from core.config import load_settings

            settings = load_settings()

            assert settings.environment == Environment.PRODUCTION
            assert settings.api_title == "Custom API"
            assert settings.api_version == "2.0.0"
            assert settings.cors_allow_origins == [
                "https://example.com",
                "https://test.com",
            ]
            assert settings.auth_required is True
            assert settings.auth_header_name == "X-API-Key"
            assert settings.log_level == "DEBUG"
