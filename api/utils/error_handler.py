"""Error handling utilities for API endpoints."""

from collections.abc import Awaitable, Callable
from typing import TypeVar

from fastapi import HTTPException, status

T = TypeVar("T")


def handle_api_operation(
    operation: Callable[[], T],
    error_message: str = "Operation failed",
    not_found_message: str | None = None,
) -> T:
    """Handle API operations with consistent error handling."""
    try:
        return operation()
    except ValueError as e:
        if not_found_message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{error_message}: {str(e)}",
        )


async def handle_async_api_operation(
    operation: Callable[[], Awaitable[T]],
    error_message: str = "Operation failed",
    not_found_message: str | None = None,
) -> T:
    """Handle async API operations with consistent error handling."""
    try:
        return await operation()
    except ValueError as e:
        if not_found_message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
        else:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"{error_message}: {str(e)}",
        )
