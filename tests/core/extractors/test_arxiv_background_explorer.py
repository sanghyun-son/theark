"""Tests for ArXiv background explorer."""

import time
import pytest
from unittest.mock import patch
import asyncio

from sqlmodel import Session, select

from core.extractors.concrete.arxiv_background_explorer import ArxivBackgroundExplorer
from core.extractors.concrete.arxiv_source_explorer import ArxivSourceExplorer
from core.models.domain.arxiv import ArxivPaper
from core.models.rows import ArxivCrawlProgress


@pytest.fixture
def sample_arxiv_paper() -> "ArxivPaper":
    """Create a sample ArXiv paper for testing."""

    return ArxivPaper(
        arxiv_id="2401.12345",
        title="Test Paper Title",
        abstract="This is a test paper abstract for testing purposes.",
        authors=["Author One", "Author Two"],
        published_date="2024-01-15T00:00:00Z",
        updated_date="2024-01-15T00:00:00Z",
        url_abs="https://arxiv.org/abs/2401.12345",
        url_pdf="https://arxiv.org/pdf/2401.12345",
        categories=["cs.AI", "cs.LG"],
        primary_category="cs.AI",
        doi=None,
        journal=None,
        volume=None,
        pages=None,
    )


@pytest.fixture
def mock_arxiv_background_explorer(
    mock_db_engine, mock_arxiv_source_explorer
) -> ArxivBackgroundExplorer:
    """Create an ArxivBackgroundExplorer instance with mock server for testing."""
    return ArxivBackgroundExplorer(
        engine=mock_db_engine,
        categories=["cs.AI", "cs.LG"],
        paper_interval_seconds=0,  # Fast for testing
        retry_attempts=1,
        retry_base_delay_seconds=0.1,
    )


def test_parse_arxiv_categories_valid(mock_arxiv_background_explorer) -> None:
    """Test parsing valid ArXiv categories."""
    result = mock_arxiv_background_explorer.parse_arxiv_categories(
        "cs.AI,cs.LG,math.CO"
    )
    assert result == ["cs.AI", "cs.LG", "math.CO"]


def test_parse_arxiv_categories_empty_string(mock_arxiv_background_explorer) -> None:
    """Test parsing empty string raises ValueError."""
    with pytest.raises(ValueError, match="Categories string cannot be empty"):
        mock_arxiv_background_explorer.parse_arxiv_categories("")


def test_parse_arxiv_categories_whitespace_only(mock_arxiv_background_explorer) -> None:
    """Test parsing whitespace-only string raises ValueError."""
    with pytest.raises(ValueError, match="Categories string cannot be empty"):
        mock_arxiv_background_explorer.parse_arxiv_categories("   ")


def test_parse_arxiv_categories_no_valid_categories(
    mock_arxiv_background_explorer,
) -> None:
    """Test parsing string with no valid categories raises ValueError."""
    with pytest.raises(ValueError, match="No valid categories found in string"):
        mock_arxiv_background_explorer.parse_arxiv_categories(",,,")


def test_parse_arxiv_categories_invalid_format(mock_arxiv_background_explorer) -> None:
    """Test parsing invalid category format raises ValueError."""
    with pytest.raises(ValueError, match="Invalid ArXiv category format: invalid"):
        mock_arxiv_background_explorer.parse_arxiv_categories("cs.AI,invalid,cs.LG")


def test_parse_arxiv_categories_invalid_case(mock_arxiv_background_explorer) -> None:
    """Test parsing invalid case raises ValueError."""
    with pytest.raises(ValueError, match="Invalid ArXiv category format: cs.ai"):
        mock_arxiv_background_explorer.parse_arxiv_categories("cs.AI,cs.ai,cs.LG")


@pytest.mark.asyncio
async def test_load_crawl_progress_no_existing(mock_arxiv_background_explorer) -> None:
    """Test loading crawl progress when none exists."""
    result_date, result_index = (
        await mock_arxiv_background_explorer.load_crawl_progress("cs.AI", "2024-01-15")
    )
    assert result_date == "2024-01-15"
    assert result_index == 0


@pytest.mark.asyncio
async def test_load_crawl_progress_existing_same_day(
    mock_arxiv_background_explorer,
) -> None:
    """Test loading crawl progress for existing category on same day."""

    # Create existing progress
    with Session(mock_arxiv_background_explorer.engine) as session:
        progress = ArxivCrawlProgress(
            category="cs.AI",
            last_crawled_date="2024-01-15",
            last_crawled_index=25,
            is_active=True,
        )
        session.add(progress)
        session.commit()

    result_date, result_index = (
        await mock_arxiv_background_explorer.load_crawl_progress("cs.AI", "2024-01-15")
    )
    assert result_date == "2024-01-15"
    assert result_index == 25


@pytest.mark.asyncio
async def test_load_crawl_progress_existing_different_day(
    mock_arxiv_background_explorer,
) -> None:
    """Test loading crawl progress for existing category on different day."""

    # Create existing progress for yesterday
    with Session(mock_arxiv_background_explorer.engine) as session:
        progress = ArxivCrawlProgress(
            category="cs.AI",
            last_crawled_date="2024-01-14",
            last_crawled_index=30,
            is_active=True,
        )
        session.add(progress)
        session.commit()

    result_date, result_index = (
        await mock_arxiv_background_explorer.load_crawl_progress("cs.AI", "2024-01-15")
    )
    assert result_date == "2024-01-15"
    assert result_index == 0


@pytest.mark.asyncio
async def test_save_crawl_progress_new(mock_arxiv_background_explorer) -> None:
    """Test saving new crawl progress."""
    await mock_arxiv_background_explorer.save_crawl_progress("cs.AI", "2024-01-15", 10)

    from core.models.rows import ArxivCrawlProgress

    with Session(mock_arxiv_background_explorer.engine) as session:
        progress = session.exec(
            select(ArxivCrawlProgress).where(ArxivCrawlProgress.category == "cs.AI")
        ).first()

    assert progress is not None
    assert progress.category == "cs.AI"
    assert progress.last_crawled_date == "2024-01-15"
    assert progress.last_crawled_index == 10
    assert progress.is_active is True


@pytest.mark.asyncio
async def test_save_crawl_progress_update_existing(
    mock_arxiv_background_explorer,
) -> None:
    """Test updating existing crawl progress."""

    # Create existing progress
    with Session(mock_arxiv_background_explorer.engine) as session:
        progress = ArxivCrawlProgress(
            category="cs.AI",
            last_crawled_date="2024-01-15",
            last_crawled_index=5,
            is_active=True,
        )
        session.add(progress)
        session.commit()

    # Update progress
    await mock_arxiv_background_explorer.save_crawl_progress("cs.AI", "2024-01-15", 15)

    with Session(mock_arxiv_background_explorer.engine) as session:
        updated_progress = session.exec(
            select(ArxivCrawlProgress).where(ArxivCrawlProgress.category == "cs.AI")
        ).first()

    assert updated_progress is not None
    assert updated_progress.last_crawled_date == "2024-01-15"
    assert updated_progress.last_crawled_index == 15


@pytest.mark.asyncio
async def test_store_paper_metadata_new_paper(
    mock_arxiv_background_explorer, sample_arxiv_paper
) -> None:
    """Test storing new paper metadata."""
    result = await mock_arxiv_background_explorer.store_paper_metadata(
        sample_arxiv_paper
    )

    # Verify the paper was created
    assert result.paper_id is not None
    assert result.arxiv_id == "2401.12345"
    assert result.title == "Test Paper Title"
    assert result.abstract == "This is a test paper abstract for testing purposes."
    assert result.primary_category == "cs.AI"
    assert result.categories == "cs.AI,cs.LG"
    assert result.authors == "Author One;Author Two"
    assert result.url_abs == "https://arxiv.org/abs/2401.12345"
    assert result.url_pdf == "https://arxiv.org/pdf/2401.12345"
    assert result.published_at == "2024-01-15T00:00:00Z"
    assert result.summary_status.value == "batched"


@pytest.mark.asyncio
async def test_store_paper_metadata_duplicate_arxiv_id(
    mock_arxiv_background_explorer, sample_arxiv_paper
) -> None:
    """Test storing paper with duplicate arxiv_id logs warning and returns existing paper."""
    # Store the first paper
    first_result = await mock_arxiv_background_explorer.store_paper_metadata(
        sample_arxiv_paper
    )

    # Try to store the same paper again
    second_result = await mock_arxiv_background_explorer.store_paper_metadata(
        sample_arxiv_paper
    )

    # Should return the existing paper (not raise an error)
    assert second_result.arxiv_id == "2401.12345"
    assert second_result.paper_id == first_result.paper_id  # Same paper ID


@pytest.mark.asyncio
async def test_store_paper_metadata_multiple_papers(
    mock_arxiv_background_explorer,
) -> None:
    """Test storing multiple papers."""
    from core.models.domain.arxiv import ArxivPaper

    # Create two different papers
    paper1 = ArxivPaper(
        arxiv_id="2401.12345",
        title="Test Paper 1",
        abstract="Abstract 1",
        authors=["Author 1"],
        published_date="2024-01-15T00:00:00Z",
        updated_date="2024-01-15T00:00:00Z",
        url_abs="https://arxiv.org/abs/2401.12345",
        url_pdf=None,
        categories=["cs.AI"],
        primary_category="cs.AI",
        doi=None,
        journal=None,
        volume=None,
        pages=None,
    )

    paper2 = ArxivPaper(
        arxiv_id="2401.12346",
        title="Test Paper 2",
        abstract="Abstract 2",
        authors=["Author 2"],
        published_date="2024-01-15T00:00:00Z",
        updated_date="2024-01-15T00:00:00Z",
        url_abs="https://arxiv.org/abs/2401.12346",
        url_pdf=None,
        categories=["cs.LG"],
        primary_category="cs.LG",
        doi=None,
        journal=None,
        volume=None,
        pages=None,
    )

    result1 = await mock_arxiv_background_explorer.store_paper_metadata(paper1)
    result2 = await mock_arxiv_background_explorer.store_paper_metadata(paper2)

    assert result1.arxiv_id == "2401.12345"
    assert result2.arxiv_id == "2401.12346"
    assert result1.paper_id != result2.paper_id


@pytest.mark.asyncio
async def test_handle_failed_paper_new_failure(mock_arxiv_background_explorer) -> None:
    """Test handling a new failed paper."""
    await mock_arxiv_background_explorer.handle_failed_paper(
        "2401.12345", "cs.AI", "Network timeout"
    )

    # Verify it was stored in the failed papers table
    from core.models.rows import ArxivFailedPaper

    with Session(mock_arxiv_background_explorer.engine) as session:
        failed_paper = session.exec(
            select(ArxivFailedPaper).where(ArxivFailedPaper.arxiv_id == "2401.12345")
        ).first()

        assert failed_paper is not None
    assert failed_paper.arxiv_id == "2401.12345"
    assert failed_paper.category == "cs.AI"
    assert failed_paper.error_message == "Network timeout"
    assert failed_paper.retry_count == 0


@pytest.mark.asyncio
async def test_handle_failed_paper_existing_failure(
    mock_arxiv_background_explorer,
) -> None:
    """Test handling an existing failed paper (increment retry count)."""
    from core.models.rows import ArxivFailedPaper

    # Create an existing failed paper
    with Session(mock_arxiv_background_explorer.engine) as session:
        existing_failed = ArxivFailedPaper(
            arxiv_id="2401.12345",
            category="cs.AI",
            error_message="Initial error",
            retry_count=1,
        )
        session.add(existing_failed)
        session.commit()

    # Handle the same paper failing again
    await mock_arxiv_background_explorer.handle_failed_paper(
        "2401.12345", "cs.AI", "New error message"
    )

    # Verify the retry count was incremented
    with Session(mock_arxiv_background_explorer.engine) as session:
        failed_paper = session.exec(
            select(ArxivFailedPaper).where(ArxivFailedPaper.arxiv_id == "2401.12345")
        ).first()

        assert failed_paper is not None
    assert failed_paper.retry_count == 2
    assert failed_paper.error_message == "New error message"
    assert failed_paper.last_retry_at is not None


@pytest.mark.asyncio
async def test_handle_failed_paper_multiple_failures(
    mock_arxiv_background_explorer,
) -> None:
    """Test handling multiple failed papers."""
    # Handle multiple failed papers
    await mock_arxiv_background_explorer.handle_failed_paper(
        "2401.12345", "cs.AI", "Error 1"
    )
    await mock_arxiv_background_explorer.handle_failed_paper(
        "2401.12346", "cs.LG", "Error 2"
    )

    # Verify both were stored
    from core.models.rows import ArxivFailedPaper

    with Session(mock_arxiv_background_explorer.engine) as session:
        failed_papers = session.exec(select(ArxivFailedPaper)).all()
        assert len(failed_papers) == 2

    # Check first paper
    paper1 = next(p for p in failed_papers if p.arxiv_id == "2401.12345")
    assert paper1.category == "cs.AI"
    assert paper1.error_message == "Error 1"
    assert paper1.retry_count == 0

    # Check second paper
    paper2 = next(p for p in failed_papers if p.arxiv_id == "2401.12346")
    assert paper2.category == "cs.LG"
    assert paper2.error_message == "Error 2"
    assert paper2.retry_count == 0


@pytest.mark.asyncio
async def test_retry_with_exponential_backoff_success_first_try(
    mock_arxiv_background_explorer,
) -> None:
    """Test retry function when first attempt succeeds."""
    call_count = 0

    async def mock_func() -> str:
        nonlocal call_count
        call_count += 1
        return "success"

    result = await mock_arxiv_background_explorer.retry_with_exponential_backoff(
        mock_func
    )

    assert result == "success"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_with_exponential_backoff_success_after_retries(
    mock_arxiv_background_explorer,
) -> None:
    """Test retry function when success occurs after some failures."""
    call_count = 0

    async def mock_func() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary error")
        return "success"

    result = await mock_arxiv_background_explorer.retry_with_exponential_backoff(
        mock_func, max_retries=3
    )

    assert result == "success"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_with_exponential_backoff_all_failures(
    mock_arxiv_background_explorer,
) -> None:
    """Test retry function when all attempts fail."""
    call_count = 0

    async def mock_func() -> str:
        nonlocal call_count
        call_count += 1
        raise RuntimeError(f"Error {call_count}")

    with pytest.raises(RuntimeError, match="Error 3"):
        await mock_arxiv_background_explorer.retry_with_exponential_backoff(
            mock_func, max_retries=2
        )

    assert call_count == 3  # Initial + 2 retries


@pytest.mark.asyncio
async def test_retry_with_exponential_backoff_custom_delays(
    mock_arxiv_background_explorer,
) -> None:
    """Test retry function with custom base delay."""

    call_count = 0
    start_time = time.time()

    async def mock_func() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary error")
        return "success"

    result = await mock_arxiv_background_explorer.retry_with_exponential_backoff(
        mock_func, max_retries=3, base_delay=0.1
    )

    end_time = time.time()
    elapsed_time = end_time - start_time

    assert result == "success"
    assert call_count == 3
    # Should have delays of 0.1s and 0.2s (total ~0.3s)
    assert elapsed_time >= 0.2  # Allow some tolerance


@pytest.mark.asyncio
async def test_retry_with_exponential_backoff_with_args_kwargs(
    mock_arxiv_background_explorer,
) -> None:
    """Test retry function with arguments and keyword arguments."""
    call_count = 0

    async def mock_func(arg1: str, arg2: int, kwarg1: str = "default") -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            raise ValueError("Temporary error")
        return f"{arg1}_{arg2}_{kwarg1}"

    result = await mock_arxiv_background_explorer.retry_with_exponential_backoff(
        mock_func, "test", 42, kwarg1="custom"
    )

    assert result == "test_42_custom"
    assert call_count == 2


@pytest.mark.asyncio
async def test_process_single_paper_success(
    mock_arxiv_background_explorer, sample_arxiv_paper
) -> None:
    """Test successful processing of a single paper."""
    # Mock the ArxivExtractor to return our sample paper
    with patch(
        "core.extractors.concrete.arxiv_extractor.ArxivExtractor"
    ) as mock_extractor_class:
        mock_extractor = mock_extractor_class.return_value

        async def mock_extract(arxiv_id: str):
            return sample_arxiv_paper

        mock_extractor.extract_metadata_async = mock_extract

        result = await mock_arxiv_background_explorer.process_single_paper(
            sample_arxiv_paper, "cs.AI"
        )

        assert result is True


@pytest.mark.asyncio
async def test_process_single_paper_storage_failure(
    mock_arxiv_background_explorer, sample_arxiv_paper
) -> None:
    """Test processing when paper storage fails."""
    # Mock the ArxivExtractor to return our sample paper
    with patch(
        "core.extractors.concrete.arxiv_extractor.ArxivExtractor"
    ) as mock_extractor_class:
        mock_extractor = mock_extractor_class.return_value

        async def mock_extract(arxiv_id: str):
            return sample_arxiv_paper

        mock_extractor.extract_metadata_async = mock_extract

        # Mock store_paper_metadata to raise an exception
        with patch.object(
            mock_arxiv_background_explorer, "store_paper_metadata"
        ) as mock_store:
            mock_store.side_effect = ValueError("Database error")

            result = await mock_arxiv_background_explorer.process_single_paper(
                sample_arxiv_paper, "cs.AI"
            )

            assert result is False

            # Verify failed paper was stored
            from core.models.rows import ArxivFailedPaper

            with Session(mock_arxiv_background_explorer.engine) as session:
                failed_paper = session.exec(
                    select(ArxivFailedPaper).where(
                        ArxivFailedPaper.arxiv_id == "2401.12345"
                    )
                ).first()

                assert failed_paper is not None
                assert "Database error" in failed_paper.error_message


@pytest.mark.asyncio
async def test_process_single_paper_duplicate_arxiv_id(
    mock_arxiv_background_explorer, sample_arxiv_paper
) -> None:
    """Test processing when paper with same arxiv_id already exists."""
    # First, store the paper
    await mock_arxiv_background_explorer.store_paper_metadata(sample_arxiv_paper)

    # Mock the ArxivExtractor to return the same paper
    with patch(
        "core.extractors.concrete.arxiv_extractor.ArxivExtractor"
    ) as mock_extractor_class:
        mock_extractor = mock_extractor_class.return_value

        async def mock_extract(arxiv_id: str):
            return sample_arxiv_paper

        mock_extractor.extract_metadata_async = mock_extract

        result = await mock_arxiv_background_explorer.process_single_paper(
            sample_arxiv_paper, "cs.AI"
        )

        assert (
            result is True
        )  # Should succeed since paper already exists (warning instead of error)

        # Verify that the paper was not stored again (no duplicate)
        from core.models.rows import Paper

        with Session(mock_arxiv_background_explorer.engine) as session:
            papers = session.exec(
                select(Paper).where(Paper.arxiv_id == "2401.12345")
            ).all()
            assert len(papers) == 1  # Only one paper should exist


@pytest.mark.asyncio
async def test_process_single_paper_multiple_papers(
    mock_arxiv_background_explorer,
) -> None:
    """Test processing multiple papers successfully."""

    # Create two different papers
    paper1 = ArxivPaper(
        arxiv_id="2401.12345",
        title="Test Paper 1",
        abstract="Abstract 1",
        authors=["Author 1"],
        published_date="2024-01-15T00:00:00Z",
        updated_date="2024-01-15T00:00:00Z",
        url_abs="https://arxiv.org/abs/2401.12345",
        url_pdf=None,
        categories=["cs.AI"],
        primary_category="cs.AI",
        doi=None,
        journal=None,
        volume=None,
        pages=None,
    )

    paper2 = ArxivPaper(
        arxiv_id="2401.12346",
        title="Test Paper 2",
        abstract="Abstract 2",
        authors=["Author 2"],
        published_date="2024-01-15T00:00:00Z",
        updated_date="2024-01-15T00:00:00Z",
        url_abs="https://arxiv.org/abs/2401.12346",
        url_pdf=None,
        categories=["cs.LG"],
        primary_category="cs.LG",
        doi=None,
        journal=None,
        volume=None,
        pages=None,
    )

    # Mock the ArxivExtractor to return different papers
    with patch(
        "core.extractors.concrete.arxiv_extractor.ArxivExtractor"
    ) as mock_extractor_class:
        mock_extractor = mock_extractor_class.return_value

        call_count = 0

        async def mock_extract(arxiv_id: str):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return paper1
            else:
                return paper2

        mock_extractor.extract_metadata_async = mock_extract

        result1 = await mock_arxiv_background_explorer.process_single_paper(
            paper1, "cs.AI"
        )
        result2 = await mock_arxiv_background_explorer.process_single_paper(
            paper2, "cs.LG"
        )

        assert result1 is True
        assert result2 is True

        # Verify both papers were stored
        from core.models.rows import Paper

        with Session(mock_arxiv_background_explorer.engine) as session:
            papers = session.exec(select(Paper)).all()
            assert len(papers) == 2
            assert papers[0].arxiv_id == "2401.12345"
            assert papers[1].arxiv_id == "2401.12346"


@pytest.mark.asyncio
async def test_process_category_papers_no_papers(
    mock_arxiv_background_explorer,
) -> None:
    """Test processing category when no papers are found."""
    with patch(
        "core.extractors.concrete.arxiv_source_explorer.ArxivSourceExplorer"
    ) as mock_explorer_class:
        mock_explorer = mock_explorer_class.return_value

        async def mock_explore(category: str, date: str, index: int, limit: int):
            return []

        mock_explorer.explore_new_papers_by_category = mock_explore

        processed, failed = (
            await mock_arxiv_background_explorer.process_category_papers(
                "cs.AI", "2024-01-15"
            )
        )

        assert processed == 0
        assert failed == 0


@pytest.mark.asyncio
async def test_process_category_papers_with_papers(
    mock_arxiv_background_explorer, sample_arxiv_paper
) -> None:
    """Test processing category with papers."""
    # Create a list of papers
    papers = [sample_arxiv_paper]

    with (
        patch(
            "core.extractors.concrete.arxiv_source_explorer.ArxivSourceExplorer"
        ) as mock_explorer_class,
        patch.object(
            mock_arxiv_background_explorer, "process_single_paper"
        ) as mock_process,
    ):
        mock_explorer = mock_explorer_class.return_value

        async def mock_explore(category: str, date: str, index: int, limit: int):
            return papers

        mock_explorer.explore_new_papers_by_category = mock_explore
        mock_process.return_value = True

        processed, failed = (
            await mock_arxiv_background_explorer.process_category_papers(
                "cs.AI", "2024-01-15"
            )
        )

        assert processed == 1
        assert failed == 0
        mock_process.assert_called_once_with(sample_arxiv_paper, "cs.AI")


@pytest.mark.asyncio
async def test_process_category_papers_with_failed_paper(
    mock_arxiv_background_explorer, sample_arxiv_paper
) -> None:
    """Test processing category with a failed paper."""
    papers = [sample_arxiv_paper]

    with (
        patch(
            "core.extractors.concrete.arxiv_source_explorer.ArxivSourceExplorer"
        ) as mock_explorer_class,
        patch.object(
            mock_arxiv_background_explorer, "process_single_paper"
        ) as mock_process,
    ):
        mock_explorer = mock_explorer_class.return_value

        async def mock_explore(category: str, date: str, index: int, limit: int):
            return papers

        mock_explorer.explore_new_papers_by_category = mock_explore
        mock_process.return_value = False

        processed, failed = (
            await mock_arxiv_background_explorer.process_category_papers(
                "cs.AI", "2024-01-15"
            )
        )

        assert processed == 0
        assert failed == 1


@pytest.mark.asyncio
async def test_process_category_papers_with_exception(
    mock_arxiv_background_explorer,
) -> None:
    """Test processing category when an exception occurs."""
    with patch(
        "core.extractors.concrete.arxiv_source_explorer.ArxivSourceExplorer"
    ) as mock_explorer_class:
        mock_explorer = mock_explorer_class.return_value

        async def mock_explore(category: str, date: str, index: int, limit: int):
            raise Exception("API Error")

        mock_explorer.explore_new_papers_by_category = mock_explore

        processed, failed = (
            await mock_arxiv_background_explorer.process_category_papers(
                "cs.AI", "2024-01-15"
            )
        )

        assert processed == 0
        assert failed == 1


# Note: Background service tests are complex due to infinite loop nature
# These would be better tested in integration tests with proper lifecycle management


@pytest.mark.asyncio
async def test_process_category_papers_with_mock_response(
    mock_arxiv_background_explorer: ArxivBackgroundExplorer,
    mock_arxiv_source_explorer: ArxivSourceExplorer,
) -> None:
    """Test processing category papers using mock server response."""
    # Mock the ArxivSourceExplorer to return papers from our mock response
    with patch(
        "core.extractors.concrete.arxiv_source_explorer.ArxivSourceExplorer",
        return_value=mock_arxiv_source_explorer,
    ):
        processed, failed = (
            await mock_arxiv_background_explorer.process_category_papers(
                "cs.AI", "2025-01-01"
            )
        )

        # Should process some papers from the mock response
        assert processed > 0
        assert failed == 0

        # Verify that papers were stored in the database
        with Session(mock_arxiv_background_explorer.engine) as session:
            from core.models.rows import Paper

            papers = session.exec(select(Paper)).all()
            assert len(papers) > 0

            # Check that all stored papers have cs.AI category
            for paper in papers:
                assert (
                    "cs.AI" in paper.categories
                ), f"Paper {paper.arxiv_id} should have cs.AI category"


@pytest.mark.asyncio
async def test_store_paper_metadata_with_mock_response(
    mock_arxiv_background_explorer: ArxivBackgroundExplorer,
) -> None:
    """Test storing paper metadata using mock server response."""
    # Create an ArxivPaper from our mock response
    from core.models.domain.arxiv import ArxivPaper

    arxiv_paper = ArxivPaper(
        arxiv_id="2501.00961v3",
        title="Uncovering Memorization Effect in the Presence of Spurious Correlations",
        abstract="Machine learning models often rely on simple spurious features...",
        authors=["Chenyu You", "Haocheng Dai", "Yifei Min"],
        published_date="2025-01-01T21:45:00+00:00",
        updated_date="2025-06-05T00:06:59+00:00",
        url_abs="https://arxiv.org/abs/2501.00961v3",
        url_pdf="https://arxiv.org/pdf/2501.00961v3",
        categories=["cs.LG", "cs.AI", "cs.CV", "eess.IV"],
        primary_category="cs.LG",
        doi=None,
        journal=None,
        volume=None,
        pages=None,
    )

    # Store the paper metadata
    stored_paper = await mock_arxiv_background_explorer.store_paper_metadata(
        arxiv_paper
    )

    # Verify the paper was stored correctly
    assert stored_paper.arxiv_id == "2501.00961v3"
    assert stored_paper.primary_category == "cs.LG"
    assert stored_paper.categories == "cs.LG,cs.AI,cs.CV,eess.IV"
    assert "cs.AI" in stored_paper.categories.split(",")
