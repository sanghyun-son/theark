"""Integration tests for overview functionality in lightweight paper list."""

import pytest
from fastapi.testclient import TestClient


@pytest.mark.asyncio
async def test_lightweight_papers_have_overview_data(integration_client: TestClient):
    """Test that lightweight papers return overview data instead of null."""
    # Test with prioritize_summaries=false
    response_normal = integration_client.get(
        "/v1/papers/lightweight?limit=10&prioritize_summaries=false"
    )
    assert response_normal.status_code == 200
    data_normal = response_normal.json()

    # Test with prioritize_summaries=true
    response_prioritized = integration_client.get(
        "/v1/papers/lightweight?limit=10&prioritize_summaries=true"
    )
    assert response_prioritized.status_code == 200
    data_prioritized = response_prioritized.json()

    print(f"\n=== OVERVIEW FUNCTIONALITY TEST ===")
    print(f"Normal response: {len(data_normal['papers'])} papers")
    print(f"Prioritized response: {len(data_prioritized['papers'])} papers")

    # Check that papers with summaries have overview data
    papers_with_summaries_normal = [
        p for p in data_normal["papers"] if p.get("has_summary", False)
    ]
    papers_with_summaries_prioritized = [
        p for p in data_prioritized["papers"] if p.get("has_summary", False)
    ]

    print(f"\nNormal: {len(papers_with_summaries_normal)} papers with summaries")
    print(
        f"Prioritized: {len(papers_with_summaries_prioritized)} papers with summaries"
    )

    # Check overview data for papers with summaries
    for i, paper in enumerate(papers_with_summaries_normal[:3]):
        overview = paper.get("overview")
        has_summary = paper.get("has_summary", False)
        status = paper.get("summary_status")
        print(
            f"Normal {i+1}. ID: {paper['paper_id']}, has_summary: {has_summary}, status: {status}, overview_length: {len(overview) if overview else 0}"
        )

        if has_summary:
            assert (
                overview is not None
            ), f"Paper {paper['paper_id']} has summary but overview is null"
            assert len(overview) > 0, f"Paper {paper['paper_id']} has empty overview"

    for i, paper in enumerate(papers_with_summaries_prioritized[:3]):
        overview = paper.get("overview")
        has_summary = paper.get("has_summary", False)
        status = paper.get("summary_status")
        print(
            f"Prioritized {i+1}. ID: {paper['paper_id']}, has_summary: {has_summary}, status: {status}, overview_length: {len(overview) if overview else 0}"
        )

        if has_summary:
            assert (
                overview is not None
            ), f"Paper {paper['paper_id']} has summary but overview is null"
            assert len(overview) > 0, f"Paper {paper['paper_id']} has empty overview"


@pytest.mark.asyncio
async def test_has_summary_field_accuracy(integration_client: TestClient):
    """Test that has_summary field accurately reflects summary status."""
    response = integration_client.get(
        "/v1/papers/lightweight?limit=20&prioritize_summaries=true"
    )
    assert response.status_code == 200
    data = response.json()

    print(f"\n=== HAS_SUMMARY FIELD ACCURACY TEST ===")
    print(f"Total papers: {len(data['papers'])}")

    # Check has_summary field accuracy
    for i, paper in enumerate(data["papers"]):
        has_summary = paper.get("has_summary", False)
        status = paper.get("summary_status")
        overview = paper.get("overview")

        # has_summary should be true only when status is "done"
        expected_has_summary = status == "done"

        if i < 5:  # Print first 5 for debugging
            print(
                f"{i+1}. ID: {paper['paper_id']}, status: {status}, has_summary: {has_summary}, expected: {expected_has_summary}, overview_length: {len(overview) if overview else 0}"
            )

        assert (
            has_summary == expected_has_summary
        ), f"Paper {paper['paper_id']}: has_summary={has_summary} but status={status} (expected has_summary={expected_has_summary})"


@pytest.mark.asyncio
async def test_prioritize_summaries_ordering_with_overview(
    integration_client: TestClient,
):
    """Test that prioritize_summaries correctly orders papers and includes overview data."""
    # Get papers without prioritization
    response_normal = integration_client.get(
        "/v1/papers/lightweight?limit=15&prioritize_summaries=false"
    )
    assert response_normal.status_code == 200
    data_normal = response_normal.json()

    # Get papers with prioritization
    response_prioritized = integration_client.get(
        "/v1/papers/lightweight?limit=15&prioritize_summaries=true"
    )
    assert response_prioritized.status_code == 200
    data_prioritized = response_prioritized.json()

    print(f"\n=== PRIORITIZE SUMMARIES ORDERING TEST ===")
    print(f"Normal: {len(data_normal['papers'])} papers")
    print(f"Prioritized: {len(data_prioritized['papers'])} papers")

    # Count papers with summaries in each response
    normal_with_summaries = sum(
        1 for p in data_normal["papers"] if p.get("has_summary", False)
    )
    prioritized_with_summaries = sum(
        1 for p in data_prioritized["papers"] if p.get("has_summary", False)
    )

    print(f"Normal: {normal_with_summaries} papers with summaries")
    print(f"Prioritized: {prioritized_with_summaries} papers with summaries")

    # In prioritized response, papers with summaries should come first
    if prioritized_with_summaries > 0:
        first_paper_without_summary_idx = None
        for i, paper in enumerate(data_prioritized["papers"]):
            if not paper.get("has_summary", False):
                first_paper_without_summary_idx = i
                break

        if first_paper_without_summary_idx is not None:
            print(
                f"First paper without summary at index: {first_paper_without_summary_idx}"
            )

            # All papers before this index should have summaries
            for i in range(first_paper_without_summary_idx):
                paper = data_prioritized["papers"][i]
                assert paper.get(
                    "has_summary", False
                ), f"Paper at index {i} should have summary in prioritized response"

                # Check that overview data is present
                overview = paper.get("overview")
                assert (
                    overview is not None
                ), f"Paper {paper['paper_id']} has summary but overview is null"
                assert (
                    len(overview) > 0
                ), f"Paper {paper['paper_id']} has empty overview"

    # Both responses should have the same total number of papers
    assert len(data_normal["papers"]) == len(
        data_prioritized["papers"]
    ), "Normal and prioritized responses should have same number of papers"


@pytest.mark.asyncio
async def test_overview_content_quality(integration_client: TestClient):
    """Test that overview content is meaningful and not just placeholder text."""
    response = integration_client.get(
        "/v1/papers/lightweight?limit=10&prioritize_summaries=true"
    )
    assert response.status_code == 200
    data = response.json()

    print(f"\n=== OVERVIEW CONTENT QUALITY TEST ===")

    papers_with_overviews = [
        p
        for p in data["papers"]
        if p.get("overview") and len(p.get("overview", "")) > 0
    ]

    print(f"Papers with overview content: {len(papers_with_overviews)}")

    for i, paper in enumerate(papers_with_overviews[:3]):
        overview = paper.get("overview", "")
        print(f"{i+1}. ID: {paper['paper_id']}, overview preview: {overview[:100]}...")

        # Check that overview is not just placeholder text
        assert (
            overview != "Click to load..."
        ), f"Paper {paper['paper_id']} has placeholder overview text"
        assert (
            len(overview) > 10
        ), f"Paper {paper['paper_id']} has very short overview: {overview}"

        # Check that overview contains some meaningful content
        # (not just whitespace or special characters)
        meaningful_chars = sum(1 for c in overview if c.isalnum())
        assert (
            meaningful_chars > 5
        ), f"Paper {paper['paper_id']} overview has too few meaningful characters: {overview}"


@pytest.mark.asyncio
async def test_relevance_field_presence(integration_client: TestClient):
    """Test that relevance field is properly included in lightweight response."""
    response = integration_client.get(
        "/v1/papers/lightweight?limit=10&prioritize_summaries=true"
    )
    assert response.status_code == 200
    data = response.json()

    print(f"\n=== RELEVANCE FIELD TEST ===")
    print(f"Total papers: {len(data['papers'])}")

    papers_with_relevance = [
        p for p in data["papers"] if p.get("relevance") is not None
    ]
    print(f"Papers with relevance data: {len(papers_with_relevance)}")

    for i, paper in enumerate(data["papers"][:5]):
        relevance = paper.get("relevance")
        has_summary = paper.get("has_summary", False)
        overview = paper.get("overview")
        print(
            f"{i+1}. ID: {paper['paper_id']}, has_summary: {has_summary}, relevance: {relevance}, overview_length: {len(overview) if overview else 0}"
        )

        # Papers with summaries should have relevance data
        if has_summary:
            assert (
                relevance is not None
            ), f"Paper {paper['paper_id']} has summary but relevance is null"
            assert isinstance(
                relevance, int
            ), f"Paper {paper['paper_id']} relevance should be int, got {type(relevance)}"
            assert (
                1 <= relevance <= 10
            ), f"Paper {paper['paper_id']} relevance should be 1-10, got {relevance}"
