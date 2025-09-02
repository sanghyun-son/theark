"""Tests for error handler utilities."""

import pytest
from fastapi import HTTPException

from api.utils.error_handler import handle_api_operation, handle_async_api_operation


def test_handle_api_operation_returns_success_result() -> None:
    """Test successful API operation returns expected result."""

    def success_operation() -> str:
        return "success"

    result = handle_api_operation(success_operation)
    assert result == "success"


def test_handle_api_operation_raises_400_for_value_error() -> None:
    """Test API operation raises HTTP 400 for ValueError."""

    def value_error_operation() -> None:
        raise ValueError("Validation error")

    with pytest.raises(HTTPException) as exc_info:
        handle_api_operation(value_error_operation)

    assert exc_info.value.status_code == 400
    assert "Validation error" in str(exc_info.value.detail)


def test_handle_api_operation_raises_404_for_not_found_value_error() -> None:
    """Test API operation raises HTTP 404 for ValueError with not found message."""

    def not_found_operation() -> None:
        raise ValueError("Not found")

    with pytest.raises(HTTPException) as exc_info:
        handle_api_operation(
            not_found_operation, not_found_message="Resource not found"
        )

    assert exc_info.value.status_code == 404
    assert "Not found" in str(exc_info.value.detail)


def test_handle_api_operation_raises_500_for_unexpected_error() -> None:
    """Test API operation raises HTTP 500 for unexpected errors."""

    def unexpected_error_operation() -> None:
        raise Exception("Unexpected error")

    with pytest.raises(HTTPException) as exc_info:
        handle_api_operation(unexpected_error_operation, "Custom error message")

    assert exc_info.value.status_code == 500
    assert "Custom error message" in str(exc_info.value.detail)
    assert "Unexpected error" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_handle_async_api_operation_returns_success_result() -> None:
    """Test successful async API operation returns expected result."""

    async def success_operation() -> str:
        return "success"

    result = await handle_async_api_operation(success_operation)
    assert result == "success"


@pytest.mark.asyncio
async def test_handle_async_api_operation_raises_400_for_value_error() -> None:
    """Test async API operation raises HTTP 400 for ValueError."""

    async def value_error_operation() -> None:
        raise ValueError("Validation error")

    with pytest.raises(HTTPException) as exc_info:
        await handle_async_api_operation(value_error_operation)

    assert exc_info.value.status_code == 400
    assert "Validation error" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_handle_async_api_operation_raises_404_for_not_found_value_error() -> (
    None
):
    """Test async API operation raises HTTP 404 for ValueError with not found message."""

    async def not_found_operation() -> None:
        raise ValueError("Not found")

    with pytest.raises(HTTPException) as exc_info:
        await handle_async_api_operation(
            not_found_operation, not_found_message="Resource not found"
        )

    assert exc_info.value.status_code == 404
    assert "Not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_handle_async_api_operation_raises_500_for_unexpected_error() -> None:
    """Test async API operation raises HTTP 500 for unexpected errors."""

    async def unexpected_error_operation() -> None:
        raise Exception("Unexpected error")

    with pytest.raises(HTTPException) as exc_info:
        await handle_async_api_operation(
            unexpected_error_operation, "Custom error message"
        )

    assert exc_info.value.status_code == 500
    assert "Custom error message" in str(exc_info.value.detail)
    assert "Unexpected error" in str(exc_info.value.detail)
