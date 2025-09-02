"""Integration tests for crawler API endpoints."""

from fastapi.testclient import TestClient


def test_start_crawler(integration_client: TestClient) -> None:
    """Test starting crawler."""
    response = integration_client.put("/v1/crawler")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert "message" in data
    assert "was_already_running" in data


def test_start_crawler_already_running(integration_client: TestClient) -> None:
    """Test starting crawler when already running."""
    # Start crawler first time
    response1 = integration_client.put("/v1/crawler")
    assert response1.status_code == 200

    # Try to start again
    response2 = integration_client.put("/v1/crawler")
    assert response2.status_code == 200
    data = response2.json()
    assert data["was_already_running"] is True


def test_stop_crawler(integration_client: TestClient) -> None:
    """Test stopping crawler."""
    # Start crawler first
    integration_client.put("/v1/crawler")

    # Stop crawler
    response = integration_client.delete("/v1/crawler")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "stopped"
    assert "message" in data


def test_stop_crawler_not_running(integration_client: TestClient) -> None:
    """Test stopping crawler when not running."""
    response = integration_client.delete("/v1/crawler")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "stopped"


def test_get_crawler_status(integration_client: TestClient) -> None:
    """Test getting crawler status."""
    response = integration_client.get("/v1/crawler")

    assert response.status_code == 200
    data = response.json()
    assert "is_running" in data
    assert "is_active" in data
    assert "current_date" in data
    assert "current_category_index" in data
    assert "categories" in data


def test_get_crawler_progress(integration_client: TestClient) -> None:
    """Test getting crawler progress."""
    response = integration_client.get("/v1/crawler/progress")

    assert response.status_code == 200
    data = response.json()
    assert "total_papers_found" in data
    assert "total_papers_stored" in data
    assert "completed_date_categories" in data
    assert "failed_date_categories" in data


def test_crawler_lifecycle(integration_client: TestClient) -> None:
    """Test complete crawler lifecycle."""
    # Check initial status
    status_response = integration_client.get("/v1/crawler")
    assert status_response.status_code == 200

    # Start crawler
    start_response = integration_client.put("/v1/crawler")
    assert start_response.status_code == 200
    start_data = start_response.json()
    assert start_data["status"] == "running"

    # Check status after start
    status_response = integration_client.get("/v1/crawler")
    assert status_response.status_code == 200
    running_status = status_response.json()
    assert running_status["is_running"] is True

    # Check progress
    progress_response = integration_client.get("/v1/crawler/progress")
    assert progress_response.status_code == 200
    progress_data = progress_response.json()
    assert isinstance(progress_data["total_papers_found"], int)
    assert isinstance(progress_data["total_papers_stored"], int)

    # Stop crawler
    stop_response = integration_client.delete("/v1/crawler")
    assert stop_response.status_code == 200
    stop_data = stop_response.json()
    assert stop_data["status"] == "stopped"

    # Check status after stop
    status_response = integration_client.get("/v1/crawler")
    assert status_response.status_code == 200
    stopped_status = status_response.json()
    assert stopped_status["is_running"] is False
