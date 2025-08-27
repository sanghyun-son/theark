"""Tests for FastAPI application."""


def test_docs_endpoint(integration_client):
    """Test that docs endpoint is accessible."""
    response = integration_client.get("/docs")
    assert response.status_code == 200
    assert "swagger-ui" in response.text


def test_openapi_schema(integration_client):
    """Test that OpenAPI schema is accessible."""
    response = integration_client.get("/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert schema["info"]["title"] == "TheArk API"
    assert schema["info"]["version"] == "1.0.0"


def test_cors_headers(integration_client):
    """Test CORS headers are set."""
    response = integration_client.get(
        "/health",
        headers={"Origin": "http://localhost:3000"},
    )
    assert response.status_code == 200
    # CORS headers should be present in the response
    assert "access-control-allow-origin" in response.headers
