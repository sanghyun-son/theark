"""Task management domain models."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TaskStats(BaseModel):
    """Statistics for periodic task execution."""

    executions: int = 0
    errors: int = 0
    consecutive_errors: int = 0
    last_execution_time: datetime | None = None
    last_error_time: datetime | None = None
    start_time: datetime | None = None


class TaskManagerStatus(BaseModel):
    """Status information for periodic task manager."""

    status: str
    periodic_running: bool
    stats: TaskStats
    config: dict[str, Any]
