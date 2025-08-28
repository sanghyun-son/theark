"""Tests for configuration management."""

import os
from unittest.mock import patch

import pytest

from core.config import Environment, Settings


def test_environment_values() -> None:
    """Test environment enum values."""
    assert Environment.DEVELOPMENT == "development"
    assert Environment.PRODUCTION == "production"
    assert Environment.TESTING == "testing"


def test_default_settings() -> None:
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


def test_development_mode_properties() -> None:
    """Test development mode properties."""
    with patch.dict(os.environ, {"THEARK_ENV": "development"}, clear=True):
        settings = Settings()

        assert settings.is_development is True
        assert settings.is_production is False
        assert settings.is_testing is False
        assert settings.auth_required is False


def test_production_mode_properties() -> None:
    """Test production mode properties."""
    with patch.dict(os.environ, {"THEARK_ENV": "production"}, clear=True):
        from core.config import load_settings

        settings = load_settings()

        assert settings.is_development is False
        assert settings.is_production is True
        assert settings.is_testing is False
        assert settings.auth_required is True


def test_testing_mode_properties() -> None:
    """Test testing mode properties."""
    with patch.dict(os.environ, {"THEARK_ENV": "testing"}, clear=True):
        from core.config import load_settings

        settings = load_settings()

        assert settings.is_development is False
        assert settings.is_production is False
        assert settings.is_testing is True
        assert settings.auth_required is False


def test_custom_settings() -> None:
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


def test_batch_settings_integration() -> None:
    """Test batch settings integration with other settings."""
    env_vars = {
        "THEARK_ENV": "production",
        "THEARK_BATCH_ENABLED": "false",
        "THEARK_BATCH_MAX_ITEMS": "500",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        from core.config import load_settings

        settings = load_settings()

        # Test that batch settings work with other settings
        assert settings.environment == Environment.PRODUCTION
        assert settings.auth_required is True  # Production mode
        assert settings.batch_enabled is False
        assert settings.batch_max_items == 500
        # Other batch settings should have defaults
        assert settings.batch_summary_interval == 3600
        assert settings.batch_fetch_interval == 600


def test_batch_settings_custom() -> None:
    """Test custom batch settings via environment variables."""
    env_vars = {
        "THEARK_BATCH_SUMMARY_INTERVAL": "1800",
        "THEARK_BATCH_FETCH_INTERVAL": "300",
        "THEARK_BATCH_MAX_ITEMS": "500",
        "THEARK_BATCH_DAILY_LIMIT": "5000",
        "THEARK_BATCH_ENABLED": "false",
        "THEARK_BATCH_MAX_RETRIES": "5",
    }

    with patch.dict(os.environ, env_vars, clear=True):
        from core.config import load_settings

        settings = load_settings()

        assert settings.batch_summary_interval == 1800
        assert settings.batch_fetch_interval == 300
        assert settings.batch_max_items == 500
        assert settings.batch_daily_limit == 5000
        assert settings.batch_enabled is False
        assert settings.batch_max_retries == 5


@pytest.mark.parametrize(
    "true_value",
    ["true", "True", "TRUE", "1", "yes", "on"],
)
def test_batch_settings_boolean_parsing_true(true_value: str) -> None:
    """Test batch enabled boolean parsing for true values."""
    with patch.dict(os.environ, {"THEARK_BATCH_ENABLED": true_value}, clear=True):
        from core.config import load_settings

        settings = load_settings()
        assert settings.batch_enabled is True


@pytest.mark.parametrize(
    "false_value",
    ["false", "False", "FALSE", "0", "no", "off", ""],
)
def test_batch_settings_boolean_parsing_false(false_value: str) -> None:
    """Test batch enabled boolean parsing for false values."""
    with patch.dict(os.environ, {"THEARK_BATCH_ENABLED": false_value}, clear=True):
        from core.config import load_settings

        settings = load_settings()
        assert settings.batch_enabled is False
