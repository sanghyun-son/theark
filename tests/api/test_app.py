"""Tests for FastAPI application."""

from fastapi.testclient import TestClient

from api.app import app

client = TestClient(app)


def test_docs_endpoint():
    """Test that docs endpoint is accessible."""
    response = client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text


def test_openapi_schema():
    """Test that OpenAPI schema is accessible."""
    response = client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert schema["info"]["title"] == "TheArk API"
    assert schema["info"]["version"] == "1.0.0"


def test_cors_headers():
    """Test CORS headers are set."""
    response = client.get(
        "/health", headers={"Origin": "http://localhost:3000"}
    )
    assert response.status_code == 200
    # CORS headers should be present in the response
    assert "access-control-allow-origin" in response.headers
