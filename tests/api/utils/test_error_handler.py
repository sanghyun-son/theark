"""Tests for error handler utilities."""

import pytest
from fastapi import HTTPException

from api.utils.error_handler import handle_api_operation, handle_async_api_operation


def test_handle_api_operation_success():
    """Test successful API operation."""

    def success_operation():
        return "success"

    result = handle_api_operation(success_operation)
    assert result == "success"


def test_handle_api_operation_value_error():
    """Test API operation that raises ValueError."""

    def value_error_operation():
        raise ValueError("Validation error")

    with pytest.raises(HTTPException) as exc_info:
        handle_api_operation(value_error_operation)

    assert exc_info.value.status_code == 400
    assert "Validation error" in str(exc_info.value.detail)


def test_handle_api_operation_value_error_with_not_found():
    """Test API operation that raises ValueError with not found message."""

    def not_found_operation():
        raise ValueError("Not found")

    with pytest.raises(HTTPException) as exc_info:
        handle_api_operation(
            not_found_operation, not_found_message="Resource not found"
        )

    assert exc_info.value.status_code == 404
    assert "Not found" in str(exc_info.value.detail)


def test_handle_api_operation_unexpected_error():
    """Test API operation that raises unexpected error."""

    def unexpected_error_operation():
        raise Exception("Unexpected error")

    with pytest.raises(HTTPException) as exc_info:
        handle_api_operation(unexpected_error_operation, "Custom error message")

    assert exc_info.value.status_code == 500
    assert "Custom error message" in str(exc_info.value.detail)
    assert "Unexpected error" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_handle_async_api_operation_success():
    """Test successful async API operation."""

    async def success_operation():
        return "success"

    result = await handle_async_api_operation(success_operation)
    assert result == "success"


@pytest.mark.asyncio
async def test_handle_async_api_operation_value_error():
    """Test async API operation that raises ValueError."""

    async def value_error_operation():
        raise ValueError("Validation error")

    with pytest.raises(HTTPException) as exc_info:
        await handle_async_api_operation(value_error_operation)

    assert exc_info.value.status_code == 400
    assert "Validation error" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_handle_async_api_operation_value_error_with_not_found():
    """Test async API operation that raises ValueError with not found message."""

    async def not_found_operation():
        raise ValueError("Not found")

    with pytest.raises(HTTPException) as exc_info:
        await handle_async_api_operation(
            not_found_operation, not_found_message="Resource not found"
        )

    assert exc_info.value.status_code == 404
    assert "Not found" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_handle_async_api_operation_unexpected_error():
    """Test async API operation that raises unexpected error."""

    async def unexpected_error_operation():
        raise Exception("Unexpected error")

    with pytest.raises(HTTPException) as exc_info:
        await handle_async_api_operation(
            unexpected_error_operation, "Custom error message"
        )

    assert exc_info.value.status_code == 500
    assert "Custom error message" in str(exc_info.value.detail)
    assert "Unexpected error" in str(exc_info.value.detail)
