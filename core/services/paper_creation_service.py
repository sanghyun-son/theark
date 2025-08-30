"""Paper creation service for handling paper creation logic."""

from sqlmodel import Session

from core import get_logger
from core.database.repository import PaperRepository
from core.extractors import extractor_factory
from core.extractors.exceptions import ExtractionError
from core.models import PaperCreateRequest
from core.models.rows import Paper

logger = get_logger(__name__)


class PaperCreationService:
    """Service for paper creation operations."""

    def __init__(self) -> None:
        """Initialize paper creation service."""
        pass

    def _extract_arxiv_id(self, paper_data: PaperCreateRequest) -> str:
        """Extract arXiv ID from paper data."""
        if not paper_data.url:
            raise ValueError("No URL provided")

        try:
            extractor = extractor_factory.find_extractor_for_url(paper_data.url)
            return extractor.extract_identifier(paper_data.url)
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")

    async def create_paper(
        self,
        paper_data: PaperCreateRequest,
        paper_repo: PaperRepository,
    ) -> Paper:
        """Create a paper using the new extractor system."""
        arxiv_id = self._extract_arxiv_id(paper_data)

        # Check if paper already exists
        existing_paper = paper_repo.get_by_arxiv_id(arxiv_id)
        if existing_paper:
            logger.info(f"[{arxiv_id}] Already exists")
            return existing_paper

        # Extract paper metadata using the new extractor system
        extracted_paper = await self._extract_paper(
            paper_data.url, arxiv_id, paper_repo
        )
        return extracted_paper

    async def _extract_paper(
        self,
        url: str,
        arxiv_id: str,
        paper_repo: PaperRepository,
    ) -> Paper:
        """Extract paper metadata using the new extractor system."""
        try:
            extractor = extractor_factory.find_extractor_for_url(url)
            metadata = await extractor.extract_metadata_async(url)

            # Convert PaperMetadata to Paper (SQLModel)
            paper = Paper(
                arxiv_id=arxiv_id,
                title=metadata.title,
                abstract=metadata.abstract,
                authors=";".join(metadata.authors),
                primary_category=(
                    metadata.categories[0] if metadata.categories else "cs.AI"
                ),
                categories=",".join(metadata.categories),
                url_abs=metadata.url_abs,
                url_pdf=metadata.url_pdf,
                published_at=metadata.published_date,
            )

            # Save to database
            saved_paper = paper_repo.create(paper)

            logger.info(f"[{arxiv_id}] Extraction success")
            return saved_paper

        except ExtractionError as e:
            logger.error(f"[{arxiv_id}] Extraction failed: {e}")
            raise ValueError(f"Failed to extract paper {arxiv_id}: {e}")

    async def get_paper_by_identifier(
        self, paper_identifier: str, db_session: Session
    ) -> Paper | None:
        """Get a paper by ID or arXiv ID."""
        paper_repo = PaperRepository(db_session)

        # Try to parse as integer (paper ID)
        try:
            paper_id = int(paper_identifier)
            return paper_repo.get_by_id(paper_id)
        except ValueError:
            # Try as arXiv ID
            return paper_repo.get_by_arxiv_id(paper_identifier)
