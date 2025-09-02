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
            "THEARK_PRESET_CATEGORIES": "cs.AI,cs.CV,cs.NE",
        },
    ):
        return load_settings()


@pytest.fixture
def spaced_categories_settings() -> Settings:
    """Fixture for settings with spaced categories."""
    with patch.dict(
        os.environ,
        {
            "THEARK_PRESET_CATEGORIES": "cs.AI, cs.LG , cs.CL",
        },
    ):
        return load_settings()


def test_default_arxiv_settings(default_settings: Settings) -> None:
    """Test default ArXiv settings values."""
    assert default_settings.arxiv_categories == [
        "cs.AI",
        "cs.CL",
        "cs.CV",
        "cs.DC",
        "cs.IR",
        "cs.LG",
        "cs.MA",
    ]


def test_custom_arxiv_settings_from_env(custom_env_settings: Settings) -> None:
    """Test custom ArXiv settings from environment variables."""
    assert custom_env_settings.arxiv_categories == ["cs.AI", "cs.CV", "cs.NE"]


def test_arxiv_categories_list_property(default_settings: Settings) -> None:
    """Test that arxiv_categories is already a list."""
    assert isinstance(default_settings.arxiv_categories, list)
    assert default_settings.arxiv_categories == [
        "cs.AI",
        "cs.CL",
        "cs.CV",
        "cs.DC",
        "cs.IR",
        "cs.LG",
        "cs.MA",
    ]


def test_arxiv_categories_with_spaces(spaced_categories_settings: Settings) -> None:
    """Test ArXiv categories with spaces are handled correctly."""
    # Since arxiv_categories is now a list, spaces are already handled during parsing
    assert spaced_categories_settings.arxiv_categories == ["cs.AI", "cs.LG", "cs.CL"]
