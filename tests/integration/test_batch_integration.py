"""Integration tests for batch processing functionality."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_batch_status_endpoint(integration_client: TestClient) -> None:
    """Test getting batch status."""
    response = integration_client.get("/batch/status")
    assert response.status_code == 200

    data = response.json()
    assert "pending_summaries" in data
    assert "active_batches" in data
    assert "batch_details" in data
    assert isinstance(data["pending_summaries"], int)
    assert isinstance(data["active_batches"], int)
    assert isinstance(data["batch_details"], list)


@pytest.mark.asyncio
async def test_list_batches_endpoint(integration_client: TestClient) -> None:
    """Test listing batches."""
    response = integration_client.get("/batch/batches")
    assert response.status_code == 200

    data = response.json()
    assert "batches" in data
    assert isinstance(data["batches"], list)


@pytest.mark.asyncio
async def test_get_pending_summaries_endpoint(integration_client: TestClient) -> None:
    """Test getting pending summaries."""
    response = integration_client.get("/batch/pending-summaries")
    assert response.status_code == 200

    data = response.json()
    assert "pending_summaries" in data
    assert "papers" in data
    assert isinstance(data["pending_summaries"], int)
    assert isinstance(data["papers"], list)


@pytest.mark.asyncio
async def test_get_batch_details_not_found(integration_client: TestClient) -> None:
    """Test getting batch details for non-existent batch."""
    response = integration_client.get("/batch/batches/nonexistent-batch-id")
    assert response.status_code == 404

    data = response.json()
    assert "detail" in data
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_get_batch_items_endpoint(integration_client: TestClient) -> None:
    """Test getting batch items."""
    # First try with a non-existent batch ID
    response = integration_client.get("/batch/batches/test-batch-id/items")
    # Should either return 404 or empty items list
    assert response.status_code in [200, 404]

    if response.status_code == 200:
        data = response.json()
        assert "batch_id" in data
        assert "items" in data
        assert data["batch_id"] == "test-batch-id"
        assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_cancel_batch_endpoint(integration_client: TestClient) -> None:
    """Test cancelling a batch."""
    response = integration_client.post("/batch/batches/test-batch-id/cancel")
    assert response.status_code == 200

    data = response.json()
    assert "message" in data
    assert "batch_id" in data
    assert data["batch_id"] == "test-batch-id"
    assert "cancelled" in data["message"].lower()


@pytest.mark.asyncio
async def test_trigger_processing_endpoint(integration_client: TestClient) -> None:
    """Test triggering batch processing."""
    response = integration_client.post("/batch/trigger-processing")
    assert response.status_code == 200

    data = response.json()
    assert "message" in data
    assert (
        "triggered" in data["message"].lower() or "success" in data["message"].lower()
    )


@pytest.mark.asyncio
async def test_batch_endpoints_with_empty_database(
    integration_client: TestClient,
) -> None:
    """Test batch endpoints with empty database state."""
    # Test status endpoint
    response = integration_client.get("/batch/status")
    assert response.status_code == 200
    data = response.json()
    assert data["pending_summaries"] == 0
    assert data["active_batches"] == 0
    assert len(data["batch_details"]) == 0

    # Test batches endpoint
    response = integration_client.get("/batch/batches")
    assert response.status_code == 200
    data = response.json()
    assert len(data["batches"]) == 0

    # Test pending summaries endpoint
    response = integration_client.get("/batch/pending-summaries")
    assert response.status_code == 200
    data = response.json()
    assert data["pending_summaries"] == 0
    assert len(data["papers"]) == 0


@pytest.mark.asyncio
async def test_batch_endpoints_error_handling(integration_client: TestClient) -> None:
    """Test error handling in batch endpoints."""
    # Test with invalid endpoint
    response = integration_client.get("/batch/nonexistent")
    assert response.status_code == 404

    # Test with invalid batch ID format
    response = integration_client.get("/batch/batches/invalid-batch-id")
    # Should handle gracefully (either 404 or 200 with empty data)
    assert response.status_code in [200, 404]
