"""Integration tests for logging functionality."""

from pathlib import Path

import pytest

from core import get_logger, setup_production_logging, setup_test_logging


def test_production_logging_setup():
    """Test production logging setup."""
    setup_production_logging()
    logger = get_logger("test_prod")
    logger.info("Production test message")

    # Check that production log file exists
    log_file = Path("logs") / "theark.log"
    assert log_file.exists()
    assert "Production test message" in log_file.read_text()


def test_test_logging_setup():
    """Test test environment logging setup."""
    setup_test_logging()
    logger = get_logger("test_env")
    logger.info("Test message")

    # Check that test log file exists
    log_file = Path("logs") / "test" / "test.log"
    assert log_file.exists()
    assert "Test message" in log_file.read_text()
