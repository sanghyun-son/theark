"""Paper service for CRUD operations."""

from datetime import datetime

from api.models.paper import PaperCreate, PaperDeleteResponse, PaperResponse
from crawler.database.models import Paper as CrawlerPaper


class PaperService:
    """Service for paper CRUD operations."""

    def __init__(self) -> None:
        """Initialize paper service."""
        # TODO: Initialize database connection or other dependencies
        pass

    async def create_paper(self, paper_data: PaperCreate) -> PaperResponse:
        """Create a new paper.

        Args:
            paper_data: Paper data to create

        Returns:
            Created paper with ID and timestamps

        Raises:
            ValueError: If paper with same arXiv ID already exists
        """
        # TODO: Implement paper creation logic
        # 1. Extract arXiv ID from either arxiv_id or url
        # 2. Validate paper data
        # 3. Check if paper with same arXiv ID exists
        # 4. Fetch metadata from arXiv API if needed
        # 5. Create paper in database using CrawlerPaper model
        # 6. Add to summarization queue if summarize_now=True
        # 7. Return created paper with ID and timestamps

        # Extract arXiv ID
        arxiv_id = self._extract_arxiv_id(paper_data)

        # TODO: Create CrawlerPaper instance and save to database
        # For now, return placeholder response
        placeholder_paper = CrawlerPaper(
            arxiv_id=arxiv_id,
            title="Placeholder Title",  # TODO: Fetch from arXiv
            abstract="Placeholder abstract",  # TODO: Fetch from arXiv
            primary_category="cs.AI",  # TODO: Fetch from arXiv
            categories="cs.AI,cs.LG",  # TODO: Fetch from arXiv
            authors="Placeholder Author",  # TODO: Fetch from arXiv
            url_abs=f"https://arxiv.org/abs/{arxiv_id}",
            url_pdf=f"https://arxiv.org/pdf/{arxiv_id}",
            published_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
        )

        return PaperResponse.from_crawler_paper(placeholder_paper)

    async def delete_paper(self, paper_identifier: str) -> PaperDeleteResponse:
        """Delete a paper by ID or arXiv ID.

        Args:
            paper_identifier: Paper ID or arXiv ID

        Returns:
            Deletion response with paper details

        Raises:
            ValueError: If paper not found
        """
        # TODO: Implement paper deletion logic
        # 1. Find paper by ID or arXiv ID
        # 2. Delete paper from database
        # 3. Cancel any pending summarization jobs
        # 4. Return deletion response

        # Placeholder implementation
        paper_id = "placeholder_id"
        arxiv_id = "placeholder_arxiv_id"

        return PaperDeleteResponse(
            id=paper_id,
            arxiv_id=arxiv_id,
            message=f"Paper {arxiv_id} deleted successfully",
        )

    def _extract_arxiv_id(self, paper_data: PaperCreate) -> str:
        """Extract arXiv ID from paper data.

        Args:
            paper_data: Paper creation data

        Returns:
            Extracted arXiv ID

        Raises:
            ValueError: If no valid arXiv ID can be extracted
        """
        # If arxiv_id is provided directly
        if paper_data.arxiv_id:
            return paper_data.arxiv_id

        # If URL is provided, extract arXiv ID from it
        if paper_data.url:
            # Extract arXiv ID from URL like https://arxiv.org/abs/2508.01234
            import re

            match = re.search(r"/abs/(\d{4}\.\d{5})$", paper_data.url)
            if match:
                return match.group(1)
            else:
                raise ValueError("Could not extract arXiv ID from URL")

        # This should not happen due to validation, but just in case
        raise ValueError("No arXiv ID or URL provided")
