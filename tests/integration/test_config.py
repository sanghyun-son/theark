"""Tests for config router."""

from core.models import CategoriesResponse


def test_get_preset_categories(integration_client):
    """Test getting preset categories."""
    response = integration_client.get("/v1/config/categories")
    assert response.status_code == 200

    data = response.json()
    assert "categories" in data
    assert "count" in data
    assert isinstance(data["categories"], list)
    assert isinstance(data["count"], int)
    assert data["count"] == len(data["categories"])

    # Check if default categories are present
    expected_categories = [
        "cs.AI",
        "cs.CL",
        "cs.CV",
        "cs.DC",
        "cs.IR",
        "cs.LG",
        "cs.MA",
    ]
    for category in expected_categories:
        assert category in data["categories"]

    response_model = CategoriesResponse(**data)
    assert response_model.categories == data["categories"]
    assert response_model.count == data["count"]
