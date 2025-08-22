"""Tests for common router."""

from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_health_check():
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"
    assert data["version"] == "1.0.0"
    assert "timestamp" in data


def test_health_response_model():
    """Test health response model structure."""
    from api.routers.common import HealthResponse

    response = HealthResponse(
        status="healthy",
        version="1.0.0",
        timestamp="2024-01-01T00:00:00",
    )

    assert response.status == "healthy"
    assert response.version == "1.0.0"
    assert response.timestamp == "2024-01-01T00:00:00"


def test_root_endpoint():
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "TheArk API" in response.text
    assert "Health Check" in response.text


def test_favicon_endpoint():
    """Test favicon endpoint."""
    response = client.get("/favicon.ico")
    assert response.status_code == 200
