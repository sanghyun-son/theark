"""Tests for ArXiv settings configuration."""

import os
from unittest.mock import patch

import pytest

from core.config import Settings, load_settings


@pytest.fixture
def default_settings() -> Settings:
    """Fixture for default settings."""
    return Settings()


@pytest.fixture
def custom_env_settings() -> Settings:
    """Fixture for settings with custom environment variables."""
    with patch.dict(
        os.environ,
        {
            "THEARK_ARXIV_CATEGORIES": "cs.AI,cs.CV,cs.NE",
            "THEARK_ARXIV_PAPER_INTERVAL_SECONDS": "5",
            "THEARK_ARXIV_FETCH_INTERVAL_MINUTES": "15",
            "THEARK_ARXIV_RETRY_ATTEMPTS": "5",
            "THEARK_ARXIV_RETRY_BASE_DELAY_SECONDS": "3",
        },
    ):
        return load_settings()


@pytest.fixture
def spaced_categories_settings() -> Settings:
    """Fixture for settings with spaced categories."""
    with patch.dict(
        os.environ,
        {
            "THEARK_ARXIV_CATEGORIES": "cs.AI, cs.LG , cs.CL",
        },
    ):
        return load_settings()


def test_default_arxiv_settings(default_settings: Settings) -> None:
    """Test default ArXiv settings values."""
    assert default_settings.arxiv_categories == "cs.AI,cs.LG,cs.CL"
    assert default_settings.arxiv_paper_interval_seconds == 2
    assert default_settings.arxiv_fetch_interval_minutes == 10
    assert default_settings.arxiv_retry_attempts == 3
    assert default_settings.arxiv_retry_base_delay_seconds == 2


def test_custom_arxiv_settings_from_env(custom_env_settings: Settings) -> None:
    """Test custom ArXiv settings from environment variables."""
    assert custom_env_settings.arxiv_categories == "cs.AI,cs.CV,cs.NE"
    assert custom_env_settings.arxiv_paper_interval_seconds == 5
    assert custom_env_settings.arxiv_fetch_interval_minutes == 15
    assert custom_env_settings.arxiv_retry_attempts == 5
    assert custom_env_settings.arxiv_retry_base_delay_seconds == 3


def test_arxiv_categories_list_property(default_settings: Settings) -> None:
    """Test that arxiv_categories can be converted to a list."""
    categories_list = [
        cat.strip() for cat in default_settings.arxiv_categories.split(",")
    ]

    assert categories_list == ["cs.AI", "cs.LG", "cs.CL"]


def test_arxiv_categories_with_spaces(spaced_categories_settings: Settings) -> None:
    """Test ArXiv categories with spaces are handled correctly."""
    categories_list = [
        cat.strip() for cat in spaced_categories_settings.arxiv_categories.split(",")
    ]

    assert categories_list == ["cs.AI", "cs.LG", "cs.CL"]
