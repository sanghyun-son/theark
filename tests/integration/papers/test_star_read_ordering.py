"""Integration tests for star-based and read-status-based ordering functionality."""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select

from core.models.rows import Paper, Summary, SummaryRead, UserStar
from core.types import PaperSummaryStatus


@pytest.mark.asyncio
async def test_prioritize_starred_papers(
    integration_client: TestClient, mock_db_session: Session
):
    """Test that starred papers are prioritized when prioritize_starred=true."""
    # Create test papers
    papers = []
    for i in range(5):
        paper = Paper(
            arxiv_id=f"2401.0000{i}",
            title=f"Test Paper {i}",
            abstract=f"Abstract for paper {i}",
            primary_category="cs.AI",
            categories="cs.AI",
            authors=f"Author {i}",
            url_abs=f"https://arxiv.org/abs/2401.0000{i}",
            url_pdf=f"https://arxiv.org/pdf/2401.0000{i}.pdf",
            published_at="2024-01-01",
            summary_status=PaperSummaryStatus.DONE,
        )
        mock_db_session.add(paper)
        papers.append(paper)

    mock_db_session.commit()

    # Create summaries for all papers
    for paper in papers:
        summary = Summary(
            paper_id=paper.paper_id,
            language="Korean",
            overview=f"Overview for paper {paper.paper_id}",
            motivation=f"Motivation for paper {paper.paper_id}",
            method=f"Method for paper {paper.paper_id}",
            result=f"Result for paper {paper.paper_id}",
            conclusion=f"Conclusion for paper {paper.paper_id}",
            interests="AI, Machine Learning",
            relevance=5,
            version="v1",
        )
        mock_db_session.add(summary)

    mock_db_session.commit()

    # Star papers 0 and 2 (first and third)
    user_id = 1
    for paper_id in [papers[0].paper_id, papers[2].paper_id]:
        if paper_id:
            user_star = UserStar(user_id=user_id, paper_id=paper_id)
            mock_db_session.add(user_star)

    mock_db_session.commit()

    # Test without prioritization
    response_normal = integration_client.get(
        "/v1/papers/lightweight?limit=10&starred=false"
    )
    assert response_normal.status_code == 200
    data_normal = response_normal.json()

    # Test with starred prioritization
    response_starred = integration_client.get(
        "/v1/papers/lightweight?limit=10&starred=true"
    )
    assert response_starred.status_code == 200
    data_starred = response_starred.json()

    print(f"\n=== STAR PRIORITIZATION TEST ===")
    print(f"Normal response: {len(data_normal['papers'])} papers")
    print(f"Starred response: {len(data_starred['papers'])} papers")

    # Check that starred papers come first in prioritized response
    starred_paper_ids = {papers[0].paper_id, papers[2].paper_id}

    # Find first non-starred paper in prioritized response
    first_non_starred_idx = None
    for i, paper in enumerate(data_starred["papers"]):
        if paper["paper_id"] not in starred_paper_ids:
            first_non_starred_idx = i
            break

    if first_non_starred_idx is not None:
        print(f"First non-starred paper at index: {first_non_starred_idx}")

        # All papers before this index should be starred
        for i in range(first_non_starred_idx):
            paper = data_starred["papers"][i]
            assert (
                paper["paper_id"] in starred_paper_ids
            ), f"Paper at index {i} should be starred in prioritized response"

    # Both responses should have the same total number of papers
    assert len(data_normal["papers"]) == len(
        data_starred["papers"]
    ), "Normal and starred responses should have same number of papers"


@pytest.mark.asyncio
async def test_prioritize_read_papers(
    integration_client: TestClient, mock_db_session: Session
):
    """Test that read papers are prioritized when prioritize_read=true."""
    # Create test papers
    papers = []
    for i in range(5):
        paper = Paper(
            arxiv_id=f"2401.0001{i}",
            title=f"Test Paper {i}",
            abstract=f"Abstract for paper {i}",
            primary_category="cs.AI",
            categories="cs.AI",
            authors=f"Author {i}",
            url_abs=f"https://arxiv.org/abs/2401.0001{i}",
            url_pdf=f"https://arxiv.org/pdf/2401.0001{i}.pdf",
            published_at="2024-01-01",
            summary_status=PaperSummaryStatus.DONE,
        )
        mock_db_session.add(paper)
        papers.append(paper)

    mock_db_session.commit()

    # Create summaries for all papers
    for paper in papers:
        summary = Summary(
            paper_id=paper.paper_id,
            language="Korean",
            overview=f"Overview for paper {paper.paper_id}",
            motivation=f"Motivation for paper {paper.paper_id}",
            method=f"Method for paper {paper.paper_id}",
            result=f"Result for paper {paper.paper_id}",
            conclusion=f"Conclusion for paper {paper.paper_id}",
            interests="AI, Machine Learning",
            relevance=5,
            version="v1",
        )
        mock_db_session.add(summary)

    mock_db_session.commit()

    # Mark papers 1 and 3 as read (second and fourth)
    user_id = 1
    for paper_id in [papers[1].paper_id, papers[3].paper_id]:
        if paper_id:
            # Find the summary for this paper
            summary = mock_db_session.exec(
                select(Summary).where(Summary.paper_id == paper_id)
            ).first()
            if summary:
                summary_read = SummaryRead(
                    user_id=user_id,
                    summary_id=summary.summary_id,
                    read_at="2024-01-01T00:00:00Z",
                )
                mock_db_session.add(summary_read)

    mock_db_session.commit()

    # Test without prioritization
    response_normal = integration_client.get(
        "/v1/papers/lightweight?limit=10&read=false"
    )
    assert response_normal.status_code == 200
    data_normal = response_normal.json()

    # Test with read prioritization
    response_read = integration_client.get("/v1/papers/lightweight?limit=10&read=true")
    if response_read.status_code != 200:
        print(f"Error response: {response_read.text}")
    assert response_read.status_code == 200
    data_read = response_read.json()

    print(f"\n=== READ PRIORITIZATION TEST ===")
    print(f"Normal response: {len(data_normal['papers'])} papers")
    print(f"Read response: {len(data_read['papers'])} papers")

    # Check that read papers come first in prioritized response
    read_paper_ids = {papers[1].paper_id, papers[3].paper_id}

    # Find first non-read paper in prioritized response
    first_non_read_idx = None
    for i, paper in enumerate(data_read["papers"]):
        if paper["paper_id"] not in read_paper_ids:
            first_non_read_idx = i
            break

    if first_non_read_idx is not None:
        print(f"First non-read paper at index: {first_non_read_idx}")

        # All papers before this index should be read
        for i in range(first_non_read_idx):
            paper = data_read["papers"][i]
            assert (
                paper["paper_id"] in read_paper_ids
            ), f"Paper at index {i} should be read in prioritized response"

    # Both responses should have the same total number of papers
    assert len(data_normal["papers"]) == len(
        data_read["papers"]
    ), "Normal and read responses should have same number of papers"


@pytest.mark.asyncio
async def test_combined_star_read_prioritization(
    integration_client: TestClient, mock_db_session: Session
):
    """Test that both starred and read papers are prioritized when both options are enabled."""
    # Create test papers
    papers = []
    for i in range(6):
        paper = Paper(
            arxiv_id=f"2401.0002{i}",
            title=f"Test Paper {i}",
            abstract=f"Abstract for paper {i}",
            primary_category="cs.AI",
            categories="cs.AI",
            authors=f"Author {i}",
            url_abs=f"https://arxiv.org/abs/2401.0002{i}",
            url_pdf=f"https://arxiv.org/pdf/2401.0002{i}.pdf",
            published_at="2024-01-01",
            summary_status=PaperSummaryStatus.DONE,
        )
        mock_db_session.add(paper)
        papers.append(paper)

    mock_db_session.commit()

    # Create summaries for all papers
    for paper in papers:
        summary = Summary(
            paper_id=paper.paper_id,
            language="Korean",
            overview=f"Overview for paper {paper.paper_id}",
            motivation=f"Motivation for paper {paper.paper_id}",
            method=f"Method for paper {paper.paper_id}",
            result=f"Result for paper {paper.paper_id}",
            conclusion=f"Conclusion for paper {paper.paper_id}",
            interests="AI, Machine Learning",
            relevance=5,
            version="v1",
        )
        mock_db_session.add(summary)

    mock_db_session.commit()

    user_id = 1

    # Star papers 0, 2, 4 (first, third, fifth)
    for paper_id in [papers[0].paper_id, papers[2].paper_id, papers[4].paper_id]:
        if paper_id:
            user_star = UserStar(user_id=user_id, paper_id=paper_id)
            mock_db_session.add(user_star)

    # Mark papers 1, 3, 5 as read (second, fourth, sixth)
    for paper_id in [papers[1].paper_id, papers[3].paper_id, papers[5].paper_id]:
        if paper_id:
            # Find the summary for this paper
            summary = mock_db_session.exec(
                select(Summary).where(Summary.paper_id == paper_id)
            ).first()
            if summary:
                summary_read = SummaryRead(
                    user_id=user_id,
                    summary_id=summary.summary_id,
                    read_at="2024-01-01T00:00:00Z",
                )
                mock_db_session.add(summary_read)

    mock_db_session.commit()

    # Test with combined prioritization
    response_combined = integration_client.get(
        "/v1/papers/lightweight?limit=10&starred=true&read=true"
    )
    assert response_combined.status_code == 200
    data_combined = response_combined.json()

    print(f"\n=== COMBINED STAR/READ PRIORITIZATION TEST ===")
    print(f"Combined response: {len(data_combined['papers'])} papers")

    # Check ordering: starred papers should come first, then read papers
    starred_paper_ids = {papers[0].paper_id, papers[2].paper_id, papers[4].paper_id}
    read_paper_ids = {papers[1].paper_id, papers[3].paper_id, papers[5].paper_id}

    # Find boundaries
    first_read_idx = None
    first_unprioritized_idx = None

    for i, paper in enumerate(data_combined["papers"]):
        paper_id = paper["paper_id"]
        if paper_id in read_paper_ids and paper_id not in starred_paper_ids:
            if first_read_idx is None:
                first_read_idx = i
        elif paper_id not in starred_paper_ids and paper_id not in read_paper_ids:
            if first_unprioritized_idx is None:
                first_unprioritized_idx = i
            break

    print(f"First read paper at index: {first_read_idx}")
    print(f"First unprioritized paper at index: {first_unprioritized_idx}")

    # All papers before first_read_idx should be starred
    if first_read_idx is not None:
        for i in range(first_read_idx):
            paper = data_combined["papers"][i]
            assert (
                paper["paper_id"] in starred_paper_ids
            ), f"Paper at index {i} should be starred in combined response"

    # All papers between first_read_idx and first_unprioritized_idx should be read (but not starred)
    if first_read_idx is not None and first_unprioritized_idx is not None:
        for i in range(first_read_idx, first_unprioritized_idx):
            paper = data_combined["papers"][i]
            assert (
                paper["paper_id"] in read_paper_ids
            ), f"Paper at index {i} should be read in combined response"
            assert (
                paper["paper_id"] not in starred_paper_ids
            ), f"Paper at index {i} should not be starred in combined response"


@pytest.mark.asyncio
async def test_star_read_prioritization_with_summary_priority(
    integration_client: TestClient, mock_db_session: Session
):
    """Test that star/read prioritization works correctly with summary prioritization."""
    # Create test papers with different summary statuses
    papers = []
    statuses = [
        PaperSummaryStatus.DONE,
        PaperSummaryStatus.PROCESSING,
        PaperSummaryStatus.BATCHED,
    ]

    for i in range(6):
        paper = Paper(
            arxiv_id=f"2401.0003{i}",
            title=f"Test Paper {i}",
            abstract=f"Abstract for paper {i}",
            primary_category="cs.AI",
            categories="cs.AI",
            authors=f"Author {i}",
            url_abs=f"https://arxiv.org/abs/2401.0003{i}",
            url_pdf=f"https://arxiv.org/pdf/2401.0003{i}.pdf",
            published_at="2024-01-01",
            summary_status=statuses[i % len(statuses)],
        )
        mock_db_session.add(paper)
        papers.append(paper)

    mock_db_session.commit()

    # Create summaries only for DONE papers
    for paper in papers:
        if paper.summary_status == PaperSummaryStatus.DONE:
            summary = Summary(
                paper_id=paper.paper_id,
                language="Korean",
                overview=f"Overview for paper {paper.paper_id}",
                motivation=f"Motivation for paper {paper.paper_id}",
                method=f"Method for paper {paper.paper_id}",
                result=f"Result for paper {paper.paper_id}",
                conclusion=f"Conclusion for paper {paper.paper_id}",
                interests="AI, Machine Learning",
                relevance=5,
                version="v1",
            )
            mock_db_session.add(summary)

    mock_db_session.commit()

    user_id = 1

    # Star some papers (mix of different statuses)
    for paper_id in [papers[1].paper_id, papers[3].paper_id]:  # PROCESSING and BATCHED
        if paper_id:
            user_star = UserStar(user_id=user_id, paper_id=paper_id)
            mock_db_session.add(user_star)

    mock_db_session.commit()

    # Test with both summary and star prioritization
    response = integration_client.get(
        "/v1/papers/lightweight?limit=10&summaries=true&starred=true"
    )
    assert response.status_code == 200
    data = response.json()

    print(f"\n=== STAR + SUMMARY PRIORITIZATION TEST ===")
    print(f"Response: {len(data['papers'])} papers")

    # Check that papers with summaries come first, then starred papers
    summary_paper_ids = {
        p.paper_id for p in papers if p.summary_status == PaperSummaryStatus.DONE
    }
    starred_paper_ids = {papers[1].paper_id, papers[3].paper_id}

    # Find first non-summary paper
    first_non_summary_idx = None
    for i, paper in enumerate(data["papers"]):
        if paper["paper_id"] not in summary_paper_ids:
            first_non_summary_idx = i
            break

    if first_non_summary_idx is not None:
        print(f"First non-summary paper at index: {first_non_summary_idx}")

        # All papers before this index should have summaries
        for i in range(first_non_summary_idx):
            paper = data["papers"][i]
            assert (
                paper["paper_id"] in summary_paper_ids
            ), f"Paper at index {i} should have summary in combined response"

    # Among non-summary papers, starred papers should come first
    non_summary_papers = (
        data["papers"][first_non_summary_idx:] if first_non_summary_idx else []
    )
    if non_summary_papers:
        first_non_starred_idx = None
        for i, paper in enumerate(non_summary_papers):
            if paper["paper_id"] not in starred_paper_ids:
                first_non_starred_idx = i
                break

        if first_non_starred_idx is not None:
            # All papers before this index should be starred
            for i in range(first_non_starred_idx):
                paper = non_summary_papers[i]
                assert (
                    paper["paper_id"] in starred_paper_ids
                ), f"Non-summary paper at index {i} should be starred in combined response"
