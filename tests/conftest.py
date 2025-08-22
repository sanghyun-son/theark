"""Pytest configuration for theark project."""

import pytest
from core import setup_test_logging


@pytest.fixture(scope="session", autouse=True)
def setup_logging():
    """Setup test logging for all tests."""
    setup_test_logging()


@pytest.fixture(scope="function")
def logger():
    """Provide a logger instance for tests."""
    from core import get_logger

    return get_logger("test")
