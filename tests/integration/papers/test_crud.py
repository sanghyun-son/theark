"""Integration tests for paper CRUD operations."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_get_papers_success(integration_client: TestClient):
    """Test successful paper list retrieval."""
    response = integration_client.get("/v1/papers/")

    if response.status_code != 200:
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")

    assert response.status_code == 200
    data = response.json()
    assert "papers" in data
    assert "total_count" in data
    assert "limit" in data
    assert "offset" in data
    assert "has_more" in data


@pytest.mark.asyncio
async def test_get_papers_with_parameters(integration_client: TestClient):
    """Test paper list retrieval with custom parameters."""
    response = integration_client.get("/v1/papers/?limit=5&offset=0&language=English")

    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 5
    assert data["offset"] == 0
    assert len(data["papers"]) <= 5


@pytest.mark.asyncio
async def test_get_papers_invalid_limit(integration_client: TestClient):
    """Test paper list retrieval with invalid limit."""
    response = integration_client.get("/v1/papers/?limit=0")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_papers_invalid_offset(integration_client: TestClient):
    """Test paper list retrieval with invalid offset."""
    response = integration_client.get("/v1/papers/?offset=-1")

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_create_paper_success(integration_client: TestClient):
    """Test successful paper creation."""
    paper_data = {
        "url": "https://arxiv.org/abs/1706.03762",
        "skip_auto_summarization": True,
        "summary_language": "English",
    }

    response = integration_client.post("/v1/papers/", json=paper_data)

    if response.status_code != 201:
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")

    assert response.status_code == 201
    data = response.json()
    assert data["arxiv_id"] == "1706.03762"
    assert data["title"] is not None
    assert data["paper_id"] is not None


@pytest.mark.asyncio
async def test_create_paper_invalid_arxiv_id(integration_client: TestClient):
    """Test paper creation with invalid arXiv ID."""
    paper_data = {
        "url": "https://invalid-url.com/paper",
        "skip_auto_summarization": True,
        "summary_language": "English",
    }

    response = integration_client.post("/v1/papers/", json=paper_data)

    if response.status_code != 400:
        print(f"Response status: {response.status_code}")
        print(f"Response content: {response.text}")

    # Should return 400 for invalid URL format
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_get_paper_success(integration_client: TestClient):
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


def test_get_paper_by_arxiv_id(integration_client: TestClient):
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


def test_get_paper_not_found(integration_client: TestClient):
    """Test paper retrieval when paper not found."""
    response = integration_client.get("/v1/papers/99999")

    assert response.status_code == 404


def test_delete_paper_success(integration_client: TestClient):
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


def test_delete_paper_not_found(integration_client: TestClient):
    """Test paper deletion when paper not found."""
    response = integration_client.delete("/v1/papers/99999")

    assert response.status_code == 404


# Lightweight endpoint tests
@pytest.mark.asyncio
async def test_get_papers_lightweight_success(integration_client: TestClient):
    """Test successful lightweight paper list retrieval."""
    response = integration_client.get("/v1/papers/lightweight")

    assert response.status_code == 200
    data = response.json()
    assert "papers" in data
    assert "total_count" in data
    assert "limit" in data
    assert "offset" in data
    assert "has_more" in data


@pytest.mark.asyncio
async def test_get_papers_lightweight_with_parameters(integration_client: TestClient):
    """Test lightweight paper list retrieval with custom parameters."""
    response = integration_client.get(
        "/v1/papers/lightweight?limit=5&offset=0&language=Korean"
    )

    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 5
    assert data["offset"] == 0
    assert len(data["papers"]) <= 5


@pytest.mark.asyncio
async def test_get_papers_lightweight_prioritize_summaries(
    integration_client: TestClient,
):
    """Test lightweight paper list with prioritize_summaries=true."""
    # First, get papers without prioritization
    response_normal = integration_client.get(
        "/v1/papers/lightweight?limit=10&prioritize_summaries=false"
    )
    assert response_normal.status_code == 200
    data_normal = response_normal.json()

    # Then, get papers with prioritization
    response_prioritized = integration_client.get(
        "/v1/papers/lightweight?limit=10&prioritize_summaries=true"
    )
    assert response_prioritized.status_code == 200
    data_prioritized = response_prioritized.json()

    # Both should return the same number of papers
    assert len(data_normal["papers"]) == len(data_prioritized["papers"])

    # Check if prioritized results have more papers with summaries
    normal_with_summaries = sum(
        1 for paper in data_normal["papers"] if paper.get("has_summary", False)
    )
    prioritized_with_summaries = sum(
        1 for paper in data_prioritized["papers"] if paper.get("has_summary", False)
    )

    print(f"Normal response: {len(data_normal['papers'])} papers")
    print(f"Prioritized response: {len(data_prioritized['papers'])} papers")
    print(f"Normal: {normal_with_summaries} papers with summaries")
    print(f"Prioritized: {prioritized_with_summaries} papers with summaries")

    # Print first few papers for debugging
    print("Normal first 3 papers:")
    for i, paper in enumerate(data_normal["papers"][:3]):
        print(
            f"  {i+1}. ID: {paper['paper_id']}, has_summary: {paper.get('has_summary', False)}, summary_status: {paper.get('summary_status', 'N/A')}"
        )

    print("Prioritized first 3 papers:")
    for i, paper in enumerate(data_prioritized["papers"][:3]):
        print(
            f"  {i+1}. ID: {paper['paper_id']}, has_summary: {paper.get('has_summary', False)}, summary_status: {paper.get('summary_status', 'N/A')}"
        )

    # Prioritized should have at least as many papers with summaries
    assert prioritized_with_summaries >= normal_with_summaries


@pytest.mark.asyncio
async def test_get_papers_lightweight_sort_by_relevance(integration_client: TestClient):
    """Test lightweight paper list with sort_by_relevance=true."""
    response = integration_client.get(
        "/v1/papers/lightweight?limit=5&sort_by_relevance=true"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["papers"]) <= 5


@pytest.mark.asyncio
async def test_get_papers_lightweight_combined_options(integration_client: TestClient):
    """Test lightweight paper list with both prioritize_summaries and sort_by_relevance."""
    response = integration_client.get(
        "/v1/papers/lightweight?limit=5&prioritize_summaries=true&sort_by_relevance=true"
    )

    assert response.status_code == 200
    data = response.json()
    assert len(data["papers"]) <= 5
