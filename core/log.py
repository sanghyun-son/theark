"""Logging configuration for the theark system."""

import logging
import logging.handlers
import sys
from pathlib import Path

import colorlog

# Base format string for log messages (without colors)
BASE_LOG_FORMAT = (
    "%(asctime)s %(levelname)8s %(message)s (%(name)s@%(filename)s:%(lineno)d)"
)


def setup_logging(
    level: int = logging.INFO,
    format_string: str | None = None,
    use_colors: bool = True,
    enable_file_logging: bool = False,
    log_dir: Path | None = None,
    is_test_env: bool = False,
) -> None:
    """Configure logging for the theark system.

    Args:
        level: Logging level to use
        format_string: Custom format string for log messages
        use_colors: Whether to use colored output for console
        enable_file_logging: Whether to enable file logging
        log_dir: Directory for log files (defaults to ./logs or ./logs/test)
        is_test_env: Whether this is a test environment
    """
    if log_dir is None:
        log_dir = Path("logs")
        if is_test_env:
            log_dir = log_dir / "test"

    if enable_file_logging:
        log_dir.mkdir(parents=True, exist_ok=True)

    console_format = format_string or _get_console_format(use_colors)

    handlers = [_create_console_handler(console_format, use_colors)]

    if enable_file_logging:
        handlers.append(
            _create_file_handler(
                log_dir,
                BASE_LOG_FORMAT,
                is_test_env,
            )
        )

    logging.basicConfig(
        level=level,
        handlers=handlers,
        force=True,
    )


def _get_console_format(use_colors: bool) -> str:
    """Get console format string based on color preference."""
    if use_colors:
        return (
            "%(asctime)s %(log_color)s%(levelname)8s%(reset)s %(message)s "
            "\033[90m(%(name)s@%(filename)s:%(lineno)d)\033[0m"
        )
    return BASE_LOG_FORMAT


def _create_console_handler(format_string: str, use_colors: bool) -> logging.Handler:
    """Create console handler with appropriate formatter."""
    console_handler = logging.StreamHandler(sys.stdout)

    if use_colors:
        console_formatter: logging.Formatter = colorlog.ColoredFormatter(
            format_string,
            datefmt="%m-%d %H:%M:%S",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
            secondary_log_colors={},
            style="%",
        )
    else:
        console_formatter = logging.Formatter(
            format_string,
            datefmt="%m-%d %H:%M:%S",
        )

    console_handler.setFormatter(console_formatter)
    return console_handler


def _create_file_handler(
    log_dir: Path, format_string: str, is_test_env: bool
) -> logging.Handler:
    """Create file handler with appropriate configuration."""
    file_formatter = logging.Formatter(
        format_string,
        datefmt="%m-%d %H:%M:%S",
    )

    if is_test_env:
        log_file = log_dir / "test.log"
        file_handler = logging.FileHandler(log_file, mode="w")
    else:
        log_file = log_dir / "theark.log"
        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=4,  # Keep 4 backup files (total 5 files)
            encoding="utf-8",
        )

    file_handler.setFormatter(file_formatter)
    return file_handler


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)


def setup_production_logging(level: int = logging.INFO) -> None:
    """Setup logging for production environment with file rotation.

    Args:
        level: Logging level to use
    """
    setup_logging(
        level=level,
        enable_file_logging=True,
        is_test_env=False,
    )


def setup_test_logging(level: int = logging.DEBUG) -> None:
    """Setup logging for test environment with file overwrite.

    Args:
        level: Logging level to use
    """
    setup_logging(
        level=level,
        enable_file_logging=True,
        is_test_env=True,
    )
