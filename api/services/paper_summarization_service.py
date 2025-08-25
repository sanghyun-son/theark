"""Paper summarization service for handling paper summarization logic."""

import asyncio

from core import get_logger
from core.config import load_settings
from core.database.llm_sqlite_manager import LLMSQLiteManager
from core.database.repository import SummaryRepository
from core.database.sqlite_manager import SQLiteManager
from core.models.database.entities import PaperEntity, SummaryEntity
from crawler.summarizer import SummaryResponse
from crawler.summarizer.client import SummaryClient
from crawler.summarizer.service import SummarizationService

logger = get_logger(__name__)


class PaperSummarizationService:
    """Service for paper summarization operations."""

    def __init__(self) -> None:
        """Initialize paper summarization service."""
        self.settings = load_settings()

    def start_background_summarization(
        self,
        paper: PaperEntity,
        db_manager: SQLiteManager,
        llm_db_manager: LLMSQLiteManager,
        summary_client: SummaryClient,
        force_resummarize: bool = False,
        language: str = "Korean",
    ) -> None:
        """Start background summarization for a paper."""
        try:
            asyncio.create_task(
                self.summarize_paper(
                    paper,
                    db_manager,
                    llm_db_manager,
                    summary_client,
                    force_resummarize,
                    language,
                )
            )
            logger.info(
                f"Started background summarization for paper "
                f"{paper.arxiv_id} in {language}"
            )
        except Exception as e:
            logger.error(
                f"Failed to start summarization for paper {paper.arxiv_id}: {e}"
            )

    async def summarize_paper(
        self,
        paper: PaperEntity,
        db_manager: SQLiteManager,
        llm_db_manager: LLMSQLiteManager,
        summary_client: SummaryClient,
        force_resummarize: bool = False,
        language: str = "Korean",
    ) -> None:
        """Summarize a paper asynchronously."""
        logger.debug(f"Starting summarization for paper {paper.arxiv_id}")
        summarization_service = SummarizationService()

        try:
            # Check if summary already exists and force_resummarize is False
            if not force_resummarize and self._has_existing_summary(
                paper, db_manager, language
            ):
                logger.info(
                    f"Summary already exists for paper {paper.arxiv_id} in {language}"
                )
                return

            summary_response = await summarization_service.summarize_paper(
                paper.arxiv_id,
                paper.abstract,
                summary_client,
                llm_db_manager,
                language=language,
                interest_section=self.settings.default_interests,
            )

            # Save summary to database
            if summary_response:
                self._save_summary(
                    paper, summary_response, db_manager, language, force_resummarize
                )
                logger.info(
                    f"Successfully summarized paper {paper.arxiv_id} in {language}"
                )
            else:
                logger.warning(
                    f"Failed to get summary response for paper {paper.arxiv_id}"
                )

        except Exception as e:
            logger.error(f"Error summarizing paper {paper.arxiv_id}: {e}")
            raise

    def _has_existing_summary(
        self, paper: PaperEntity, db_manager: SQLiteManager, language: str
    ) -> bool:
        """Check if paper already has a summary in the specified language."""
        if not paper.paper_id:
            return False

        try:
            logger.debug("Checking database connection state")
            logger.debug(f"DB manager type: {type(db_manager)}")
            logger.debug(
                f"DB manager connection: "
                f"{getattr(db_manager, 'connection', 'No connection attr')}"
            )

            logger.debug(f"Creating SummaryRepository with db_manager: {db_manager}")
            summary_repo = SummaryRepository(db_manager)

            existing_summary = summary_repo.get_by_paper_and_language(
                paper.paper_id, language
            )
            return existing_summary is not None
        except Exception as e:
            logger.error(
                f"Error checking existing summary for paper {paper.arxiv_id}: {e}"
            )
            return False

    def _save_summary(
        self,
        paper: PaperEntity,
        summary_response: SummaryResponse,
        db_manager: SQLiteManager,
        language: str,
        force_resummarize: bool = False,
    ) -> None:
        """Save summary to database."""
        if not paper.paper_id:
            logger.error("Paper has no ID")
            return

        try:
            logger.debug(
                f"Creating SummaryRepository for saving with db_manager: {db_manager}"
            )
            summary_repo = SummaryRepository(db_manager)

            # Check if summary already exists for this paper and language
            existing_summary = summary_repo.get_by_paper_and_language(
                paper.paper_id, language
            )

            if existing_summary and force_resummarize:
                # Update existing summary
                updated_summary = self._create_summary_entity(
                    paper, summary_response, db_manager, language
                )
                updated_summary.summary_id = existing_summary.summary_id
                updated_summary.version = existing_summary.version
                summary_repo.update(updated_summary)
                logger.info(f"Updated summary for paper {paper.arxiv_id} in {language}")
            else:
                # Create new summary
                summary_entity = self._create_summary_entity(
                    paper, summary_response, db_manager, language
                )
                summary_repo.create(summary_entity)
                logger.info(f"Saved summary for paper {paper.arxiv_id} in {language}")
        except Exception as e:
            logger.error(f"Error saving summary for paper {paper.arxiv_id}: {e}")
            raise

    def _create_summary_entity(
        self,
        paper: PaperEntity,
        summary_response: SummaryResponse,
        db_manager: SQLiteManager,
        language: str,
    ) -> SummaryEntity:
        """Create summary entity from summary response."""
        if not paper.paper_id:
            raise ValueError("Paper must have an ID")

        # Extract structured summary from response
        analysis = summary_response.structured_summary
        if analysis:
            return SummaryEntity(
                paper_id=paper.paper_id,
                version=1,
                overview=analysis.tldr or "No overview available",
                motivation=analysis.motivation or "No motivation available",
                method=analysis.method or "No method available",
                result=analysis.result or "No result available",
                conclusion=analysis.conclusion or "No conclusion available",
                language=language,
                interests=self.settings.default_interests,
                relevance=analysis.relevance,
                model=self.settings.llm_model,
                is_read=False,
            )
        else:
            # Fallback to simple summary
            simple_summary = summary_response.summary or "No summary available"
            return SummaryEntity(
                paper_id=paper.paper_id,
                version=1,
                overview=simple_summary,
                motivation="No structured motivation available",
                method="No structured method available",
                result="No structured result available",
                conclusion="No structured conclusion available",
                language=language,
                interests=self.settings.default_interests,
                relevance=5,  # Default relevance
                model=self.settings.llm_model,
                is_read=False,
            )

    def get_paper_summary(
        self,
        paper: PaperEntity,
        db_manager: SQLiteManager,
        language: str = "Korean",
    ) -> SummaryEntity | None:
        """Get summary for a paper in specified language."""
        if not paper.paper_id:
            return None

        summary_repo = SummaryRepository(db_manager)

        try:
            summary_obj = summary_repo.get_by_paper_and_language(
                paper.paper_id, language
            )
            if not summary_obj and language != "English":
                summary_obj = summary_repo.get_by_paper_and_language(
                    paper.paper_id, "English"
                )

            return summary_obj
        except Exception as e:
            logger.error(f"Error getting paper summary for {paper.arxiv_id}: {e}")
            return None
