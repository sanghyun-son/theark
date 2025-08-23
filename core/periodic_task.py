"""Generic periodic task manager for background operations."""

import asyncio
from abc import ABC, abstractmethod
from datetime import datetime
from enum import Enum
from typing import Any, Awaitable, Callable

from core.log import get_logger
from core.models.domain.task import TaskManagerStatus, TaskStats

logger = get_logger(__name__)


class TaskStatus(Enum):
    """Status of periodic task operations."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class PeriodicTask(ABC):
    """Abstract base class for periodic tasks."""

    @abstractmethod
    async def execute(self) -> None:
        """Execute the task logic.

        This method should be implemented by subclasses to define
        what happens in each iteration of the periodic task.
        """
        pass

    @abstractmethod
    async def on_start(self) -> None:
        """Called when the task is starting.

        Use this for initialization logic.
        """
        pass

    @abstractmethod
    async def on_stop(self) -> None:
        """Called when the task is stopping.

        Use this for cleanup logic.
        """
        pass

    async def on_error(self, error: Exception) -> None:
        """Called when an error occurs during task execution.

        Args:
            error: The exception that occurred

        Override this method to customize error handling.
        """
        logger.error(f"Error in periodic task: {error}")


class PeriodicTaskManager:
    """Generic manager for running periodic tasks."""

    def __init__(
        self,
        task: PeriodicTask,
        interval_seconds: int = 60,
        retry_delay: int = 30,
        max_retries: int = 3,
        on_status_change: Callable[[TaskStatus], Awaitable[None]] | None = None,
        on_error: Callable[[Exception], Awaitable[None]] | None = None,
    ):
        """Initialize the periodic task manager.

        Args:
            task: The periodic task to execute
            interval_seconds: Interval between task executions in seconds
            retry_delay: Delay before retrying after an error (seconds)
            max_retries: Maximum number of consecutive retries
            on_status_change: Callback when status changes
            on_error: Callback when errors occur
        """
        self.task = task
        self.interval_seconds = interval_seconds
        self.retry_delay = retry_delay
        self.max_retries = max_retries
        self.on_status_change = on_status_change
        self.on_error = on_error

        # State management
        self.status = TaskStatus.IDLE
        self._background_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

        # Statistics
        self.stats = TaskStats()

        logger.info(
            f"PeriodicTaskManager initialized with {interval_seconds}s interval"
        )

    async def __aenter__(self) -> "PeriodicTaskManager":
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        """Async context manager exit."""
        await self.stop()

    async def start(self) -> None:
        """Start the periodic task manager."""
        if self.status != TaskStatus.IDLE:
            logger.warning(f"Task manager already in {self.status} state")
            return

        try:
            await self.task.on_start()
            self._stop_event.clear()
            await self._set_status(TaskStatus.IDLE)
            self.stats.start_time = datetime.now()
            logger.info("Periodic task manager started")

        except Exception as e:
            await self._set_status(TaskStatus.ERROR)
            logger.error(f"Failed to start task manager: {e}")
            await self._handle_error(e)
            raise

    async def stop(self) -> None:
        """Stop the periodic task manager."""
        logger.info("Stopping periodic task manager...")

        # Signal background task to stop
        self._stop_event.set()

        # Cancel background task if running
        if self._background_task and not self._background_task.done():
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        # Call task cleanup
        try:
            await self.task.on_stop()
        except Exception as e:
            logger.error(f"Error during task cleanup: {e}")

        await self._set_status(TaskStatus.STOPPED)
        logger.info("Periodic task manager stopped")

    async def start_periodic(self) -> None:
        """Start the periodic execution loop."""
        if self.status == TaskStatus.RUNNING:
            logger.warning("Periodic loop already running")
            return

        if self._background_task and not self._background_task.done():
            logger.warning("Background task already exists")
            return

        await self._set_status(TaskStatus.RUNNING)
        self._background_task = asyncio.create_task(self._periodic_loop())
        logger.info("Periodic execution loop started")

    async def stop_periodic(self) -> None:
        """Stop the periodic execution loop."""
        if self.status != TaskStatus.RUNNING:
            logger.warning("Periodic loop not running")
            return

        await self._set_status(TaskStatus.PAUSED)
        self._stop_event.set()

        if self._background_task:
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass

        logger.info("Periodic execution loop stopped")

    async def execute_once(self) -> None:
        """Execute the task once manually."""
        logger.info("Executing task manually")

        try:
            await self.task.execute()
            self.stats.executions += 1
            self.stats.consecutive_errors = 0
            self.stats.last_execution_time = datetime.now()
            logger.info("Manual task execution completed")

        except Exception as e:
            self.stats.errors += 1
            self.stats.consecutive_errors += 1
            self.stats.last_error_time = datetime.now()
            logger.error(f"Error during manual execution: {e}")
            await self._handle_error(e)
            raise

    def get_status(self) -> TaskManagerStatus:
        """Get current status and statistics.

        Returns:
            TaskManagerStatus with status information
        """
        return TaskManagerStatus(
            status=self.status.value,
            periodic_running=(
                self._background_task is not None and not self._background_task.done()
            ),
            stats=self.stats,
            config={
                "interval_seconds": self.interval_seconds,
                "retry_delay": self.retry_delay,
                "max_retries": self.max_retries,
            },
        )

    async def _periodic_loop(self) -> None:
        """Background loop for periodic task execution."""
        logger.info("Periodic loop started")

        while not self._stop_event.is_set():
            try:
                logger.debug("Periodic loop iteration")

                # Execute the task
                await self.task.execute()
                self.stats.executions += 1
                self.stats.consecutive_errors = 0
                self.stats.last_execution_time = datetime.now()

                # Wait for next iteration or stop signal
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self.interval_seconds,
                    )
                except asyncio.TimeoutError:
                    # Timeout means continue with next iteration
                    pass

            except asyncio.CancelledError:
                logger.info("Periodic loop cancelled")
                break
            except Exception as e:
                self.stats.errors += 1
                self.stats.consecutive_errors += 1
                self.stats.last_error_time = datetime.now()

                logger.error(f"Error in periodic loop: {e}")
                await self._handle_error(e)

                # Check if we should stop due to too many consecutive errors
                if self.stats.consecutive_errors >= self.max_retries:
                    logger.error(
                        f"Too many consecutive errors ({self.max_retries}), "
                        f"stopping periodic loop"
                    )
                    await self._set_status(TaskStatus.ERROR)
                    break

                # Wait before retrying
                await asyncio.sleep(self.retry_delay)

        logger.info("Periodic loop stopped")

    async def _set_status(self, status: TaskStatus) -> None:
        """Set the task status and notify callbacks.

        Args:
            status: New status to set
        """
        old_status = self.status
        self.status = status

        if old_status != status:
            logger.debug(f"Status changed: {old_status.value} -> {status.value}")
            if self.on_status_change:
                try:
                    await self.on_status_change(status)
                except Exception as e:
                    logger.error(f"Error in status change callback: {e}")

    async def _handle_error(self, error: Exception) -> None:
        """Handle errors from task execution.

        Args:
            error: The exception that occurred
        """
        # Call task error handler
        try:
            await self.task.on_error(error)
        except Exception as e:
            logger.error(f"Error in task error handler: {e}")

        # Call external error callback
        if self.on_error:
            try:
                await self.on_error(error)
            except Exception as e:
                logger.error(f"Error in external error callback: {e}")
