"""Common type definitions for the theark system."""

from enum import Enum
from typing import Any, TypeAlias

DatabaseParamType: TypeAlias = dict[str, Any] | list[Any] | tuple[Any, ...] | None
RepositoryRowType: TypeAlias = dict[str, Any] | tuple[Any, ...]


class Environment(str, Enum):
    """Application environment types."""

    DEVELOPMENT = "development"
    PRODUCTION = "production"
    TESTING = "testing"


class PaperSummaryStatus(str, Enum):
    """Paper summary status enum."""

    BATCHED = "batched"
    PROCESSING = "processing"
    DONE = "done"
    ERROR = "error"
