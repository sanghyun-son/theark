"""Integration tests for authentication functionality."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.app import create_app


class TestAuthIntegration:
    """Integration tests for authentication."""

    def test_development_mode_no_auth_required(self) -> None:
        """Test that development mode doesn't require auth."""
        with patch.dict(os.environ, {"THEARK_ENV": "development"}, clear=True):
            app = create_app()
            client = TestClient(app)

            # Test auth endpoint without auth header
            response = client.get("/test-auth")
            assert response.status_code == 200

            data = response.json()
            assert data["environment"] == "development"
            assert data["auth_required"] is False
            assert data["auth_header_present"] is False

    def test_production_mode_auth_required(self) -> None:
        """Test that production mode requires auth."""
        with patch.dict(os.environ, {"THEARK_ENV": "production"}, clear=True):
            app = create_app()
            client = TestClient(app)

            # Test auth endpoint without auth header - should fail
            response = client.get("/test-auth")
            assert response.status_code == 401

            data = response.json()
            assert data["detail"]["detail"] == "Authentication required"
            assert data["detail"]["error"] == "missing_auth_header"
            assert data["detail"]["environment"] == "production"

    def test_production_mode_with_auth_header(self) -> None:
        """Test that production mode works with auth header."""
        with patch.dict(os.environ, {"THEARK_ENV": "production"}, clear=True):
            app = create_app()
            client = TestClient(app)

            # Test auth endpoint with auth header
            headers = {"Authorization": "Bearer test-token"}
            response = client.get("/test-auth", headers=headers)
            assert response.status_code == 200

            data = response.json()
            assert data["environment"] == "production"
            assert data["auth_required"] is True
            assert data["auth_header_present"] is True
            assert data["auth_header_value"] == "Bearer test-token"

    def test_testing_mode_no_auth_required(self) -> None:
        """Test that testing mode doesn't require auth."""
        with patch.dict(os.environ, {"THEARK_ENV": "testing"}, clear=True):
            app = create_app()
            client = TestClient(app)

            # Test auth endpoint without auth header
            response = client.get("/test-auth")
            assert response.status_code == 200

            data = response.json()
            assert data["environment"] == "testing"
            assert data["auth_required"] is False
            assert data["auth_header_present"] is False

    def test_health_endpoint_always_accessible(self) -> None:
        """Test that health endpoint is always accessible."""
        for env in ["development", "production", "testing"]:
            with patch.dict(os.environ, {"THEARK_ENV": env}, clear=True):
                app = create_app()
                client = TestClient(app)

                response = client.get("/health")
                assert response.status_code == 200

                data = response.json()
                assert data["status"] == "healthy"

    def test_static_files_always_accessible(self) -> None:
        """Test that static files are always accessible."""
        for env in ["development", "production", "testing"]:
            with patch.dict(os.environ, {"THEARK_ENV": env}, clear=True):
                app = create_app()
                client = TestClient(app)

                response = client.get("/static/nonexistent.css")
                # Should return 404 for non-existent file, not 401
                assert response.status_code == 404

    def test_root_endpoint_always_accessible(self) -> None:
        """Test that root endpoint is always accessible."""
        for env in ["development", "production", "testing"]:
            with patch.dict(os.environ, {"THEARK_ENV": env}, clear=True):
                app = create_app()
                client = TestClient(app)

                response = client.get("/")
                assert response.status_code == 200

    def test_custom_auth_header(self) -> None:
        """Test custom auth header configuration."""
        env_vars = {
            "THEARK_ENV": "production",
            "THEARK_AUTH_HEADER": "X-API-Key",
        }

        with patch.dict(os.environ, env_vars, clear=True):
            app = create_app()
            client = TestClient(app)

            # Should fail with default Authorization header
            headers = {"Authorization": "Bearer test-token"}
            response = client.get("/test-auth", headers=headers)
            assert response.status_code == 401

            # Should work with custom X-API-Key header
            headers = {"X-API-Key": "test-key"}
            response = client.get("/test-auth", headers=headers)
            assert response.status_code == 200

            data = response.json()
            assert data["auth_header_present"] is True
            assert data["auth_header_value"] == "test-key"
