"""Core functionality for the theark system."""

from .config import Settings, settings
from .log import (
    get_logger,
    setup_logging,
    setup_production_logging,
    setup_test_logging,
)
from .services import (
    PaperService,
    StarService,
    StreamService,
)
from .types import Environment

__all__ = [
    "Environment",
    "Settings",
    "settings",
    "get_logger",
    "setup_logging",
    "setup_production_logging",
    "setup_test_logging",
    "PaperService",
    "StarService",
    "StreamService",
]
