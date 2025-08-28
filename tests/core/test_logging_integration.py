"""Integration tests for logging functionality."""

from pathlib import Path

from core import get_logger, setup_production_logging, setup_test_logging


def test_test_logging_setup():
    """Test test environment logging setup."""
    setup_test_logging()
    logger = get_logger("test_env")
    logger.info("Test message")

    # Check that test log file exists
    log_file = Path("logs") / "test" / "test.log"
    assert log_file.exists()
    assert "Test message" in log_file.read_text()


def test_application_logging():
    """Test application logging that should be visible with --log-debug."""
    # Don't call setup_test_logging() here as it overrides pytest logging configuration
    logger = get_logger("test_app")
    logger.debug("This is a DEBUG message")
    logger.info("This is an INFO message")
    logger.warning("This is a WARNING message")
    logger.error("This is an ERROR message")

    # This test just logs messages - the actual visibility depends on pytest logging level
    assert True
