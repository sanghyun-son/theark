"""Paper creation service for handling paper creation logic."""

from core import get_logger
from core.database.interfaces import DatabaseManager
from core.database.repository import PaperRepository
from core.extractors import extractor_factory
from core.extractors.exceptions import ExtractionError
from core.models import PaperCreateRequest as PaperCreate
from core.models.database.entities import PaperEntity

logger = get_logger(__name__)


class PaperCreationService:
    """Service for paper creation operations."""

    def __init__(self) -> None:
        """Initialize paper creation service."""
        pass

    def _extract_arxiv_id(self, paper_data: PaperCreate) -> str:
        """Extract arXiv ID from paper data."""
        if not paper_data.url:
            raise ValueError("No URL provided")

        try:
            extractor = extractor_factory.find_extractor_for_url(paper_data.url)
            return extractor.extract_identifier(paper_data.url)
        except Exception as e:
            raise ValueError(f"Invalid URL format: {e}")

    async def _get_paper_by_arxiv_id(
        self, arxiv_id: str, paper_repo: PaperRepository
    ) -> PaperEntity | None:
        """Get paper by arXiv ID."""
        return await paper_repo.get_by_arxiv_id(arxiv_id)

    async def create_paper(
        self,
        paper_data: PaperCreate,
        db_manager: DatabaseManager,
    ) -> PaperEntity:
        """Create a paper using the new extractor system."""
        arxiv_id = self._extract_arxiv_id(paper_data)

        paper_repo = PaperRepository(db_manager)

        # Check if paper already exists
        existing_paper = await self._get_paper_by_arxiv_id(arxiv_id, paper_repo)
        if existing_paper:
            logger.info(f"Paper {arxiv_id} already exists, returning existing paper")
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
    ) -> PaperEntity:
        """Extract paper metadata using the new extractor system."""
        try:
            extractor = extractor_factory.find_extractor_for_url(url)
            metadata = await extractor.extract_metadata_async(url)

            # Convert PaperMetadata to PaperEntity
            paper_entity = PaperEntity(
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
                updated_at=metadata.updated_date,
            )

            # Save to database
            paper_id = await paper_repo.create(paper_entity)
            paper_entity.paper_id = paper_id

            logger.info(f"Successfully extracted paper {arxiv_id}")
            return paper_entity

        except ExtractionError as e:
            logger.error(f"Failed to extract paper {arxiv_id}: {e}")
            raise ValueError(f"Failed to extract paper {arxiv_id}: {e}")

    async def get_paper_by_identifier(
        self, paper_identifier: str, db_manager: DatabaseManager
    ) -> PaperEntity | None:
        """Get paper by ID or arXiv ID."""
        paper_repo = PaperRepository(db_manager)

        # Try to get by arXiv ID first
        paper = await paper_repo.get_by_arxiv_id(paper_identifier)
        if paper:
            return paper

        # Try to get by paper ID
        try:
            paper_id = int(paper_identifier)
            return await paper_repo.get_by_id(paper_id)
        except ValueError:
            return None
