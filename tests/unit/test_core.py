"""Unit tests for core functionality."""

import logging
from unittest.mock import patch

import pytest

from core import get_logger, setup_logging


class TestLogging:
    """Test logging functionality."""

    def test_setup_logging_defaults(self) -> None:
        """Test setup_logging with default parameters."""
        setup_logging()
        root_logger = logging.getLogger()
        assert root_logger.level == logging.INFO

    def test_setup_logging_custom_level(self) -> None:
        """Test setup_logging with custom level."""
        setup_logging(level=logging.DEBUG)
        root_logger = logging.getLogger()
        assert root_logger.level == logging.DEBUG

    def test_get_logger(self) -> None:
        """Test get_logger returns a logger instance."""
        logger = get_logger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"

    @patch("sys.stdout")
    def test_logging_output(self, mock_stdout) -> None:
        """Test that logging actually outputs to stdout."""
        setup_logging()
        logger = get_logger("test")
        logger.info("Test message")

        # Verify that stdout was called (indicating log output)
        assert mock_stdout.write.called
