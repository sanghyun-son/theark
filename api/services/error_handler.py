"""Service error handling utilities."""

from collections.abc import Callable, Coroutine
from typing import Any

from core.log import get_logger

logger = get_logger(__name__)


class ServiceErrorHandler:
    """Unified error handling for service operations."""

    @staticmethod
    async def safe_start_service(
        service_name: str,
        start_func: Callable[..., Coroutine[Any, Any, None]],
        *args: Any,
    ) -> bool:
        """Safely start a service with error handling."""
        try:
            await start_func(*args)
            logger.info(f"{service_name} started successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to start {service_name}: {e}")
            return False

    @staticmethod
    async def safe_stop_service(
        service_name: str,
        stop_func: Callable[..., Coroutine[Any, Any, None]],
        *args: Any,
    ) -> bool:
        """Safely stop a service with error handling."""
        try:
            await stop_func(*args)
            logger.info(f"{service_name} stopped successfully")
            return True
        except Exception as e:
            logger.error(f"Error stopping {service_name}: {e}")
            return False
