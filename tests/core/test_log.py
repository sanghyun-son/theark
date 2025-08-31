"""Unit tests for core logging functionality."""

import logging

from core import get_logger, setup_logging


def test_setup_logging_defaults() -> None:
    """Test setup_logging with default parameters."""
    setup_logging()
    root_logger = logging.getLogger()
    assert root_logger.level == logging.INFO


def test_setup_logging_custom_level() -> None:
    """Test setup_logging with custom level."""
    setup_logging(level=logging.DEBUG)
    root_logger = logging.getLogger()
    assert root_logger.level == logging.DEBUG


def test_get_logger() -> None:
    """Test get_logger returns a logger instance."""
    logger = get_logger("test_logger")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "test_logger"
