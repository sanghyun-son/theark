"""Universal paper service for handling papers from any source."""

from urllib.parse import urlparse

from core.database.repository import PaperRepository
from core.database.sqlite_manager import SQLiteManager
from core.extractors.universal_extractor import UniversalPaperExtractor
from core.models.database.entities import PaperEntity
from core.models.domain.paper_source import PaperSource


class UniversalPaperService:
    """Universal paper service supporting any source."""

    def __init__(self) -> None:
        """Initialize universal paper service."""
        self.extractor = UniversalPaperExtractor()

    def create_paper_from_url(self, url: str, db_manager: SQLiteManager) -> PaperEntity:
        """Create paper from any supported URL.

        Args:
            url: URL to extract paper from
            db_manager: Database manager

        Returns:
            Created paper entity

        Raises:
            ValueError: If URL is not supported or extraction fails
        """
        # Extract identifier and metadata
        identifier, metadata = self.extractor.extract_paper(url)

        # Determine source from URL
        source = self._determine_source(url)

        # Create paper entity
        paper = PaperEntity(
            arxiv_id=identifier,  # For backward compatibility, use arxiv_id field
            title=metadata.title,
            abstract=metadata.abstract,
            authors=";".join(metadata.authors),
            url_abs=metadata.url_abs,
            url_pdf=metadata.url_pdf,
            published_at=metadata.published_date,
            updated_at=metadata.updated_date,
            primary_category=(
                metadata.categories[0]
                if metadata.categories
                else source.default_category
            ),
            categories=(
                ",".join(metadata.categories)
                if metadata.categories
                else ",".join(source.default_categories)
            ),
        )

        # Save to database
        paper_repo = PaperRepository(db_manager)
        paper_id = paper_repo.create(paper)
        paper.paper_id = paper_id

        return paper

    def get_paper_by_identifier(
        self, identifier: str, db_manager: SQLiteManager
    ) -> PaperEntity | None:
        """Get paper by universal identifier.

        Args:
            identifier: Paper identifier (can be source:identifier format)
            db_manager: Database manager

        Returns:
            Paper entity if found, None otherwise
        """
        # Try to parse as source:identifier format
        if ":" in identifier:
            source_str, source_id = identifier.split(":", 1)
            try:
                source = PaperSource(source_str)
                return self._get_by_source_identifier(source, source_id, db_manager)
            except ValueError:
                # Invalid source, try as regular identifier
                pass

        # Try all sources for backward compatibility
        for source in PaperSource:
            paper = self._get_by_source_identifier(source, identifier, db_manager)
            if paper:
                return paper

        return None

    def _get_by_source_identifier(
        self, source: PaperSource, identifier: str, db_manager: SQLiteManager
    ) -> PaperEntity | None:
        """Get paper by source-specific identifier.

        Args:
            source: Paper source
            identifier: Source-specific identifier
            db_manager: Database manager

        Returns:
            Paper entity if found, None otherwise
        """
        paper_repo = PaperRepository(db_manager)

        # For now, we'll use the existing arxiv_id field for backward compatibility
        # In the future, we might want to add source and source_identifier fields
        if source == PaperSource.ARXIV:
            return paper_repo.get_by_arxiv_id(identifier)

        # For other sources, we'll need to implement source-specific lookup
        # For now, return None
        return None

    def _determine_source(self, url: str) -> PaperSource:
        """Determine paper source from URL.

        Args:
            url: Paper URL

        Returns:
            Paper source
        """
        domain = urlparse(url).netloc.lower()

        if "arxiv.org" in domain:
            return PaperSource.ARXIV
        elif "pubmed.gov" in domain or "ncbi.nlm.nih.gov" in domain:
            return PaperSource.PUBMED
        elif "ieee.org" in domain or "ieeexplore.ieee.org" in domain:
            return PaperSource.IEEE
        else:
            return PaperSource.CUSTOM
