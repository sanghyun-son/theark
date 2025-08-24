"""Integration tests for star functionality using fixture+function format."""

import pytest
from fastapi.testclient import TestClient

from tests.integration.conftest import integration_client, parse_sse_events


@pytest.fixture
def sample_paper_data() -> dict:
    """Sample paper data for testing."""
    return {
        "url": "https://arxiv.org/abs/1409.0575",
        "summary_language": "English",
    }


@pytest.fixture
def created_paper_id(integration_client: TestClient, sample_paper_data: dict) -> int:
    """Create a paper and return its ID."""
    # Create a paper via streaming
    response = integration_client.post(
        "/v1/papers/stream-summary",
        json=sample_paper_data,
        headers={"Accept": "text/event-stream"},
    )

    assert response.status_code == 200
    content = response.content.decode("utf-8")
    events = parse_sse_events(content)

    # Find the complete event to get the paper ID
    complete_events = [e for e in events if e.get("type") == "complete"]
    assert len(complete_events) > 0, "No complete event found"

    paper = complete_events[-1]["paper"]
    paper_id = paper["paper_id"]
    assert paper_id is not None, "Paper ID should be present"

    return paper_id


@pytest.mark.asyncio
async def test_star_lifecycle_end_to_end(
    integration_client: TestClient, created_paper_id: int
) -> None:
    """Test complete star lifecycle: add star, check status, remove star."""
    paper_id = created_paper_id

    # Check initial star status (should be False)
    response = integration_client.get(f"/v1/papers/{paper_id}/star")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_starred"] is False
    assert data["paper_id"] == paper_id

    # Add star
    response = integration_client.post(
        f"/v1/papers/{paper_id}/star",
        json={"note": "Interesting paper for testing"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_starred"] is True
    assert data["paper_id"] == paper_id
    assert data["note"] == "Interesting paper for testing"

    # Check star status again (should be True)
    response = integration_client.get(f"/v1/papers/{paper_id}/star")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_starred"] is True
    assert data["paper_id"] == paper_id
    assert data["note"] == "Interesting paper for testing"

    # Get starred papers list
    response = integration_client.get("/v1/papers/starred/")
    assert response.status_code == 200
    data = response.json()
    assert data["total_count"] >= 1
    assert len(data["papers"]) >= 1

    # Find our paper in the starred list
    starred_paper = next((p for p in data["papers"] if p["paper_id"] == paper_id), None)
    assert starred_paper is not None, "Paper should be in starred list"
    assert starred_paper["arxiv_id"] == "1409.0575"

    # Remove star
    response = integration_client.delete(f"/v1/papers/{paper_id}/star")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_starred"] is False
    assert data["paper_id"] == paper_id
    assert data["note"] is None

    # Check star status again (should be False)
    response = integration_client.get(f"/v1/papers/{paper_id}/star")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_starred"] is False
    assert data["paper_id"] == paper_id


@pytest.mark.asyncio
async def test_star_nonexistent_paper(integration_client: TestClient) -> None:
    """Test star operations on non-existent paper."""
    # Try to add star to non-existent paper
    response = integration_client.post(
        "/v1/papers/99999/star", json={"note": "This should fail"}
    )
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

    # Try to remove star from non-existent paper
    response = integration_client.delete("/v1/papers/99999/star")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()

    # Try to check star status of non-existent paper
    response = integration_client.get("/v1/papers/99999/star")
    assert response.status_code == 404
    data = response.json()
    assert "not found" in data["detail"].lower()


@pytest.mark.asyncio
async def test_star_without_note(
    integration_client: TestClient, created_paper_id: int
) -> None:
    """Test adding star without note."""
    paper_id = created_paper_id

    # Add star without note
    response = integration_client.post(f"/v1/papers/{paper_id}/star", json={})
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_starred"] is True
    assert data["note"] is None

    # Check star status
    response = integration_client.get(f"/v1/papers/{paper_id}/star")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_starred"] is True
    assert data["note"] is None


@pytest.mark.asyncio
async def test_starred_papers_pagination(integration_client: TestClient) -> None:
    """Test starred papers pagination."""
    # Create multiple papers and star them
    papers_to_create = [
        "https://arxiv.org/abs/1409.0575",
        "https://arxiv.org/abs/1706.03762",
    ]

    paper_ids = []
    for url in papers_to_create:
        response = integration_client.post(
            "/v1/papers/stream-summary",
            json={
                "url": url,
                "summary_language": "English",
            },
            headers={"Accept": "text/event-stream"},
        )
        assert response.status_code == 200

        content = response.content.decode("utf-8")
        events = parse_sse_events(content)
        complete_events = [e for e in events if e.get("type") == "complete"]
        assert len(complete_events) > 0

        paper = complete_events[-1]["paper"]
        paper_id = paper["paper_id"]
        paper_ids.append(paper_id)

        # Add star
        response = integration_client.post(
            f"/v1/papers/{paper_id}/star",
            json={"note": f"Starred paper {paper_id}"},
        )
        assert response.status_code == 200

    # Test pagination
    response = integration_client.get("/v1/papers/starred/?limit=1&offset=0")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 1
    assert data["offset"] == 0
    assert len(data["papers"]) == 1

    response = integration_client.get("/v1/papers/starred/?limit=1&offset=1")
    assert response.status_code == 200
    data = response.json()
    assert data["limit"] == 1
    assert data["offset"] == 1
    assert len(data["papers"]) == 1

    # Verify different papers are returned
    response1 = integration_client.get("/v1/papers/starred/?limit=1&offset=0")
    response2 = integration_client.get("/v1/papers/starred/?limit=1&offset=1")

    paper1 = response1.json()["papers"][0]
    paper2 = response2.json()["papers"][0]

    assert (
        paper1["paper_id"] != paper2["paper_id"]
    ), "Different papers should be returned"


@pytest.mark.asyncio
async def test_add_star_success(
    integration_client: TestClient, created_paper_id: int
) -> None:
    """Test successful star addition via API."""
    paper_id = created_paper_id

    # Add star
    response = integration_client.post(
        f"/v1/papers/{paper_id}/star",
        json={"note": "Test note for API star"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_starred"] is True
    assert data["paper_id"] == paper_id
    assert data["note"] == "Test note for API star"


@pytest.mark.asyncio
async def test_remove_star_success(
    integration_client: TestClient, created_paper_id: int
) -> None:
    """Test successful star removal via API."""
    paper_id = created_paper_id

    # First add a star
    response = integration_client.post(
        f"/v1/papers/{paper_id}/star",
        json={"note": "Test note for removal"},
    )
    assert response.status_code == 200

    # Then remove it
    response = integration_client.delete(f"/v1/papers/{paper_id}/star")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_starred"] is False
    assert data["paper_id"] == paper_id
    assert data["note"] is None


@pytest.mark.asyncio
async def test_is_paper_starred_true(
    integration_client: TestClient, created_paper_id: int
) -> None:
    """Test checking if a paper is starred (when it is) via API."""
    paper_id = created_paper_id

    # Add a star first
    response = integration_client.post(
        f"/v1/papers/{paper_id}/star",
        json={"note": "Test note for checking"},
    )
    assert response.status_code == 200

    # Check star status
    response = integration_client.get(f"/v1/papers/{paper_id}/star")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_starred"] is True
    assert data["paper_id"] == paper_id
    assert data["note"] == "Test note for checking"


@pytest.mark.asyncio
async def test_is_paper_starred_false(
    integration_client: TestClient, created_paper_id: int
) -> None:
    """Test checking if a paper is starred (when it is not) via API."""
    paper_id = created_paper_id

    # Check star status without adding a star
    response = integration_client.get(f"/v1/papers/{paper_id}/star")
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert data["is_starred"] is False
    assert data["paper_id"] == paper_id
    assert data["note"] is None
