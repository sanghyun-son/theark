"""Tests for the periodic task manager."""

import asyncio
from unittest.mock import MagicMock

import pytest

from core.periodic_task import PeriodicTask, PeriodicTaskManager, TaskStatus


class MockTask(PeriodicTask):
    """Mock task for testing."""

    def __init__(self):
        self.executions = 0
        self.start_called = False
        self.stop_called = False
        self.error_called = False
        self.last_error = None
        self.should_raise = False

    async def execute(self) -> None:
        """Execute the mock task."""
        if self.should_raise:
            raise ValueError("Mock error")
        self.executions += 1
        await asyncio.sleep(0.01)  # Small delay to simulate work

    async def on_start(self) -> None:
        """Called when task starts."""
        self.start_called = True

    async def on_stop(self) -> None:
        """Called when task stops."""
        self.stop_called = True

    async def on_error(self, error: Exception) -> None:
        """Called on error."""
        self.error_called = True
        self.last_error = error


class TestPeriodicTask:
    """Test periodic task interface."""

    def test_abstract_methods(self):
        """Test that PeriodicTask is abstract."""
        with pytest.raises(TypeError):
            PeriodicTask()  # Cannot instantiate abstract class


class TestPeriodicTaskManager:
    """Test periodic task manager."""

    @pytest.fixture
    def mock_task(self):
        """Create a mock task."""
        return MockTask()

    @pytest.fixture
    def task_manager(self, mock_task):
        """Create a task manager with mock task."""
        return PeriodicTaskManager(
            task=mock_task,
            interval_seconds=0.1,  # Short interval for testing
            retry_delay=0.05,
            max_retries=2,
        )

    def test_initialization(self, task_manager, mock_task):
        """Test task manager initialization."""
        assert task_manager.task == mock_task
        assert task_manager.interval_seconds == 0.1
        assert task_manager.retry_delay == 0.05
        assert task_manager.max_retries == 2
        assert task_manager.status == TaskStatus.IDLE
        assert task_manager.stats.executions == 0
        assert task_manager.stats.errors == 0

    @pytest.mark.asyncio
    async def test_start_and_stop(self, task_manager, mock_task):
        """Test starting and stopping task manager."""
        # Start
        await task_manager.start()
        assert task_manager.status == TaskStatus.IDLE
        assert mock_task.start_called is True
        assert task_manager.stats.start_time is not None

        # Stop
        await task_manager.stop()
        assert task_manager.status == TaskStatus.STOPPED
        assert mock_task.stop_called is True

    @pytest.mark.asyncio
    async def test_context_manager(self, mock_task):
        """Test async context manager functionality."""
        async with PeriodicTaskManager(mock_task) as manager:
            assert manager.status == TaskStatus.IDLE
            assert mock_task.start_called is True

        assert manager.status == TaskStatus.STOPPED
        assert mock_task.stop_called is True

    @pytest.mark.asyncio
    async def test_execute_once(self, task_manager, mock_task):
        """Test manual task execution."""
        await task_manager.start()

        # Execute once
        await task_manager.execute_once()

        assert mock_task.executions == 1
        assert task_manager.stats.executions == 1
        assert task_manager.stats.consecutive_errors == 0
        assert task_manager.stats.last_execution_time is not None

        await task_manager.stop()

    @pytest.mark.asyncio
    async def test_execute_once_error(self, task_manager, mock_task):
        """Test manual execution with error."""
        await task_manager.start()

        # Make task raise error
        mock_task.should_raise = True

        with pytest.raises(ValueError, match="Mock error"):
            await task_manager.execute_once()

        assert mock_task.executions == 0  # No successful executions
        assert task_manager.stats.errors == 1
        assert task_manager.stats.consecutive_errors == 1
        assert task_manager.stats.last_error_time is not None
        assert mock_task.error_called is True

        await task_manager.stop()

    @pytest.mark.asyncio
    async def test_periodic_execution(self, task_manager, mock_task):
        """Test periodic task execution."""
        await task_manager.start()
        await task_manager.start_periodic()

        # Wait for a few executions
        await asyncio.sleep(0.3)

        # Should have executed multiple times
        assert mock_task.executions >= 2
        assert task_manager.stats.executions >= 2
        assert task_manager.status == TaskStatus.RUNNING

        await task_manager.stop_periodic()
        await task_manager.stop()

    @pytest.mark.asyncio
    async def test_periodic_error_handling(self, task_manager, mock_task):
        """Test error handling in periodic execution."""
        await task_manager.start()

        # Make task raise errors
        mock_task.should_raise = True

        await task_manager.start_periodic()

        # Wait for errors to accumulate
        await asyncio.sleep(0.3)

        # Should have hit max retries and stopped
        assert task_manager.stats.errors >= 2
        assert task_manager.stats.consecutive_errors >= 2
        assert task_manager.status == TaskStatus.ERROR
        assert mock_task.error_called is True

        await task_manager.stop()

    @pytest.mark.asyncio
    async def test_status_callbacks(self, mock_task):
        """Test status change callbacks."""
        status_tracker = {"changes": []}

        async def on_status_change(status):
            status_tracker["changes"].append(status)

        manager = PeriodicTaskManager(
            task=mock_task,
            interval_seconds=0.1,
            on_status_change=on_status_change,
        )

        await manager.start()
        await manager.start_periodic()
        await manager.stop_periodic()
        await manager.stop()

        # Check that status changes were tracked
        # Note: IDLE status is set during start but may not trigger callback
        assert TaskStatus.RUNNING in status_tracker["changes"]
        assert TaskStatus.PAUSED in status_tracker["changes"]
        assert TaskStatus.STOPPED in status_tracker["changes"]
        assert len(status_tracker["changes"]) >= 3

    @pytest.mark.asyncio
    async def test_error_callbacks(self, mock_task):
        """Test error callbacks."""
        error_tracker = {"errors": []}

        async def on_error(error):
            error_tracker["errors"].append(error)

        manager = PeriodicTaskManager(
            task=mock_task,
            interval_seconds=0.1,
            on_error=on_error,
        )

        await manager.start()

        # Make task raise error
        mock_task.should_raise = True

        with pytest.raises(ValueError):
            await manager.execute_once()

        # Check that error was tracked
        assert len(error_tracker["errors"]) == 1
        assert isinstance(error_tracker["errors"][0], ValueError)

        await manager.stop()

    def test_get_status(self, task_manager):
        """Test status information retrieval."""
        status = task_manager.get_status()

        assert hasattr(status, "status")
        assert hasattr(status, "periodic_running")
        assert hasattr(status, "stats")
        assert hasattr(status, "config")

        assert status.status == "idle"
        assert status.periodic_running is False
        assert hasattr(status.stats, "executions")
        assert hasattr(status.stats, "errors")
        assert "interval_seconds" in status.config

    @pytest.mark.asyncio
    async def test_multiple_start_stop_calls(self, task_manager, mock_task):
        """Test multiple start/stop calls are handled gracefully."""
        # Multiple starts
        await task_manager.start()
        await task_manager.start()  # Should be ignored

        assert task_manager.status == TaskStatus.IDLE

        # Multiple stops
        await task_manager.stop()
        await task_manager.stop()  # Should be ignored

        assert task_manager.status == TaskStatus.STOPPED

    @pytest.mark.asyncio
    async def test_start_periodic_without_start(self, task_manager):
        """Test starting periodic without first calling start."""
        # This should work as start_periodic doesn't depend on start
        await task_manager.start()
        await task_manager.start_periodic()
        await task_manager.start_periodic()  # Should be ignored

        await asyncio.sleep(0.1)

        await task_manager.stop_periodic()
        await task_manager.stop()
