"""Logging configuration for the theark system."""

import logging
import sys
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    format_string: Optional[str] = None,
    stream: Optional[logging.StreamHandler] = None,
) -> None:
    """Configure logging for the theark system.

    Args:
        level: Logging level to use
        format_string: Custom format string for log messages
        stream: Custom stream handler (defaults to sys.stdout)
    """
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    if stream is None:
        stream = logging.StreamHandler(sys.stdout)

    logging.basicConfig(
        level=level,
        format=format_string,
        handlers=[stream],
        force=True,
    )


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance for the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
