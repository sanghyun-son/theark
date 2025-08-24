"""Integration tests for paper CRUD operations."""

import pytest
from fastapi.testclient import TestClient

from tests.integration.conftest import integration_client


class TestPaperCRUDIntegration:
    """Test paper CRUD operations with real database."""

    @pytest.mark.asyncio
    async def test_get_papers_success(self, integration_client: TestClient):
        """Test successful paper list retrieval."""
        response = integration_client.get("/v1/papers/")

        assert response.status_code == 200
        data = response.json()
        assert "papers" in data
        assert "total_count" in data
        assert "limit" in data
        assert "offset" in data
        assert "has_more" in data

    @pytest.mark.asyncio
    async def test_get_papers_with_parameters(self, integration_client: TestClient):
        """Test paper list retrieval with custom parameters."""
        response = integration_client.get(
            "/v1/papers/?limit=5&offset=0&language=English"
        )

        assert response.status_code == 200
        data = response.json()
        assert data["limit"] == 5
        assert data["offset"] == 0
        assert len(data["papers"]) <= 5

    @pytest.mark.asyncio
    async def test_get_papers_invalid_limit(self, integration_client: TestClient):
        """Test paper list retrieval with invalid limit."""
        response = integration_client.get("/v1/papers/?limit=0")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_get_papers_invalid_offset(self, integration_client: TestClient):
        """Test paper list retrieval with invalid offset."""
        response = integration_client.get("/v1/papers/?offset=-1")

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_paper_success(self, integration_client: TestClient):
        """Test successful paper creation."""
        paper_data = {
            "url": "https://arxiv.org/abs/1706.03762",
            "skip_auto_summarization": True,
            "summary_language": "English",
        }

        response = integration_client.post("/v1/papers/", json=paper_data)

        assert response.status_code == 201
        data = response.json()
        assert data["arxiv_id"] == "1706.03762"
        assert data["title"] is not None
        assert data["paper_id"] is not None

    @pytest.mark.asyncio
    async def test_create_paper_invalid_arxiv_id(self, integration_client: TestClient):
        """Test paper creation with invalid arXiv ID."""
        paper_data = {
            "url": "https://invalid-url.com/paper",
            "skip_auto_summarization": True,
            "summary_language": "English",
        }

        response = integration_client.post("/v1/papers/", json=paper_data)

        # Should return 400 for invalid URL format
        assert response.status_code == 400

    @pytest.mark.asyncio
    async def test_get_paper_success(self, integration_client: TestClient):
        """Test successful paper retrieval."""
        # First create a paper
        paper_data = {
            "url": "https://arxiv.org/abs/1409.0575",
            "skip_auto_summarization": True,
            "summary_language": "English",
        }

        create_response = integration_client.post("/v1/papers/", json=paper_data)
        assert create_response.status_code == 201

        created_paper = create_response.json()
        paper_id = created_paper["paper_id"]

        # Then retrieve it
        response = integration_client.get(f"/v1/papers/{paper_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["paper_id"] == paper_id
        assert data["arxiv_id"] == "1409.0575"

    @pytest.mark.asyncio
    async def test_get_paper_by_arxiv_id(self, integration_client: TestClient):
        """Test paper retrieval by arXiv ID."""
        # First create a paper
        paper_data = {
            "url": "https://arxiv.org/abs/1706.03762",
            "skip_auto_summarization": True,
            "summary_language": "English",
        }

        create_response = integration_client.post("/v1/papers/", json=paper_data)
        assert create_response.status_code == 201

        # Then retrieve it by arXiv ID
        response = integration_client.get("/v1/papers/1706.03762")

        assert response.status_code == 200
        data = response.json()
        assert data["arxiv_id"] == "1706.03762"

    @pytest.mark.asyncio
    async def test_get_paper_not_found(self, integration_client: TestClient):
        """Test paper retrieval when paper not found."""
        response = integration_client.get("/v1/papers/99999")

        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_paper_success(self, integration_client: TestClient):
        """Test successful paper deletion."""
        # First create a paper
        paper_data = {
            "url": "https://arxiv.org/abs/1409.0575",
            "skip_auto_summarization": True,
            "summary_language": "English",
        }

        create_response = integration_client.post("/v1/papers/", json=paper_data)
        assert create_response.status_code == 201

        created_paper = create_response.json()
        paper_id = created_paper["paper_id"]

        # Then delete it
        response = integration_client.delete(f"/v1/papers/{paper_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "deleted successfully" in data["message"]

    @pytest.mark.asyncio
    async def test_delete_paper_not_found(self, integration_client: TestClient):
        """Test paper deletion when paper not found."""
        response = integration_client.delete("/v1/papers/99999")

        assert response.status_code == 404
