"""Integration tests for authentication functionality."""


from fastapi.testclient import TestClient


def test_development_mode_no_auth_required(integration_client: TestClient) -> None:
    """Test that development mode doesn't require auth."""
    # integration_client uses THEARK_ENV=testing, which behaves like development
    response = integration_client.get("/test-auth")
    assert response.status_code == 200

    data = response.json()
    assert data["environment"] == "testing"
    assert data["auth_required"] is False
    assert data["auth_header_present"] is False


def test_production_mode_auth_required(
    monkeypatch, integration_client: TestClient
) -> None:
    """Test that production mode requires auth."""
    # Patch environment variables to simulate production mode
    monkeypatch.setenv("THEARK_ENV", "production")
    monkeypatch.setenv("THEARK_AUTH_REQUIRED", "true")

    # Test auth endpoint without auth header - should fail
    response = integration_client.get("/test-auth")
    assert response.status_code == 401

    data = response.json()
    assert data["detail"]["detail"] == "Authentication required"
    assert data["detail"]["error"] == "missing_auth_header"
    assert data["detail"]["environment"] == "production"


def test_production_mode_with_auth_header(
    monkeypatch, integration_client: TestClient
) -> None:
    """Test that production mode works with auth header."""
    # Patch environment variables to simulate production mode
    monkeypatch.setenv("THEARK_ENV", "production")
    monkeypatch.setenv("THEARK_AUTH_REQUIRED", "true")

    # Test auth endpoint with auth header
    headers = {"Authorization": "Bearer test-token"}
    response = integration_client.get("/test-auth", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["environment"] == "production"
    assert data["auth_required"] is True
    assert data["auth_header_present"] is True
    assert data["auth_header_value"] == "Bearer test-token"


def test_testing_mode_no_auth_required(integration_client: TestClient) -> None:
    """Test that testing mode doesn't require auth."""
    # integration_client uses THEARK_ENV=testing
    response = integration_client.get("/test-auth")
    assert response.status_code == 200

    data = response.json()
    assert data["environment"] == "testing"
    assert data["auth_required"] is False
    assert data["auth_header_present"] is False


def test_health_endpoint_always_accessible(integration_client: TestClient) -> None:
    """Test that health endpoint is always accessible."""
    # Health endpoint should be accessible regardless of auth settings
    response = integration_client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "healthy"


def test_static_files_always_accessible(integration_client: TestClient) -> None:
    """Test that static files are always accessible."""
    # Static files should be accessible regardless of auth settings
    response = integration_client.get("/static/nonexistent.css")
    # Should return 404 for non-existent file, not 401
    assert response.status_code == 404


def test_root_endpoint_always_accessible(integration_client: TestClient) -> None:
    """Test that root endpoint is always accessible."""
    # Root endpoint should be accessible regardless of auth settings
    response = integration_client.get("/")
    assert response.status_code == 200


def test_custom_auth_header(monkeypatch, integration_client: TestClient) -> None:
    """Test custom auth header configuration."""
    # Patch environment variables to simulate production mode with custom auth header
    monkeypatch.setenv("THEARK_ENV", "production")
    monkeypatch.setenv("THEARK_AUTH_REQUIRED", "true")
    monkeypatch.setenv("THEARK_AUTH_HEADER", "X-API-Key")

    # Should fail with default Authorization header
    headers = {"Authorization": "Bearer test-token"}
    response = integration_client.get("/test-auth", headers=headers)
    assert response.status_code == 401

    # Should work with custom X-API-Key header
    headers = {"X-API-Key": "test-key"}
    response = integration_client.get("/test-auth", headers=headers)
    assert response.status_code == 200

    data = response.json()
    assert data["auth_header_present"] is True
    assert data["auth_header_value"] == "test-key"
