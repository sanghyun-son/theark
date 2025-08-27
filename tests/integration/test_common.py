"""Tests for common router."""

from api.routers.common import HealthResponse


def test_health_check(integration_client):
    """Test health check endpoint."""
    response = integration_client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data


def test_health_response_model():
    """Test health response model structure."""

    response = HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp="2024-01-01T00:00:00",
    )

    assert response.status == "healthy"
    assert response.version == "1.0.0"
    assert response.timestamp == "2024-01-01T00:00:00"


def test_root_endpoint(integration_client):
    """Test root endpoint."""
    response = integration_client.get("/")
    assert response.status_code == 200
    assert "TheArk" in response.text
    assert "Paper Management" in response.text


def test_favicon_endpoint(integration_client):
    """Test favicon endpoint."""
    response = integration_client.get("/favicon.ico")
    assert response.status_code == 200
