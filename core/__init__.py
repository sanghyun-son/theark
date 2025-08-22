"""Core functionality for the theark system."""

from .log import (
    get_logger,
    setup_logging,
    setup_production_logging,
    setup_test_logging,
)

__all__ = [
    "get_logger",
    "setup_logging",
    "setup_production_logging",
    "setup_test_logging",
]
