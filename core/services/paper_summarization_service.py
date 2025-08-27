"""Paper summarization service for handling paper summarization logic."""

import asyncio

import httpx

from core import get_logger
from core.config import load_settings
from core.database.interfaces import DatabaseManager
from core.database.repository import LLMBatchRepository, SummaryRepository
from core.llm.openai_client import UnifiedOpenAIClient
from core.llm.response_parser import parse_summary_response
from core.models.database.entities import PaperEntity, SummaryEntity
from core.models.summarization import SummaryResponse

logger = get_logger(__name__)


class PaperSummarizationService:
    """Service for paper summarization operations."""

    def __init__(self) -> None:
        """Initialize paper summarization service."""
        self.settings = load_settings()

    def start_background_summarization(
        self,
        paper: PaperEntity,
        db_manager: DatabaseManager,
        summary_client: UnifiedOpenAIClient,
        force_resummarize: bool = False,
        language: str = "Korean",
    ) -> None:
        """Start background summarization for a paper."""
        try:
            asyncio.create_task(
                self.summarize_paper(
                    paper,
                    db_manager,
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
        db_manager: DatabaseManager,
        summary_client: UnifiedOpenAIClient,
        force_resummarize: bool = False,
        language: str = "Korean",
    ) -> None:
        """Summarize a paper asynchronously."""
        logger.debug(f"Starting summarization for paper {paper.arxiv_id}")

        try:
            # Check if summary already exists and force_resummarize is False
            if not force_resummarize and await self._has_existing_summary(
                paper, db_manager, language
            ):
                logger.info(
                    f"Summary already exists for paper {paper.arxiv_id} in {language}"
                )
                return

            # Mark paper as processing to prevent batch manager from picking it up
            if paper.paper_id:
                batch_repo = LLMBatchRepository(db_manager)
                await batch_repo.update_paper_summary_status(
                    paper.paper_id, "processing"
                )

            # Get raw response from OpenAI with retry logic
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await summary_client.summarize_paper(
                        content=paper.abstract,
                        interest_section=self.settings.default_interests,
                        language=language,
                        db_manager=db_manager,
                        custom_id=paper.arxiv_id,
                    )

                    # Parse response into SummaryResponse
                    summary_response = parse_summary_response(
                        response=response,
                        original_content=paper.abstract,
                        custom_id=paper.arxiv_id,
                        model=summary_client.model,
                        use_tools=summary_client.use_tools,
                    )

                    # Save summary to database
                    await self._save_summary(
                        paper, summary_response, db_manager, language, force_resummarize
                    )

                    # Mark paper as done
                    if paper.paper_id:
                        await batch_repo.update_paper_summary_status(
                            paper.paper_id, "done"
                        )

                    logger.info(
                        f"Successfully summarized paper {paper.arxiv_id} in {language}"
                    )
                    return

                except httpx.ReadTimeout as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
                        logger.warning(
                            f"Timeout on attempt {attempt + 1} for paper "
                            f"{paper.arxiv_id}, retrying in {wait_time} seconds: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All retry attempts failed for paper {paper.arxiv_id}: {e}"
                        )
                        raise
                except Exception as e:
                    logger.error(f"Error summarizing paper {paper.arxiv_id}: {e}")
                    raise

        except Exception as e:
            logger.error(f"Error summarizing paper {paper.arxiv_id}: {e}")
            raise

    async def _has_existing_summary(
        self, paper: PaperEntity, db_manager: DatabaseManager, language: str
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

            existing_summary = await summary_repo.get_by_paper_and_language(
                paper.paper_id, language
            )
            return existing_summary is not None
        except Exception as e:
            logger.error(
                f"Error checking existing summary for paper {paper.arxiv_id}: {e}"
            )
            return False

    async def _save_summary(
        self,
        paper: PaperEntity,
        summary_response: SummaryResponse,
        db_manager: DatabaseManager,
        language: str,
        force_resummarize: bool = False,
    ) -> None:
        """Save summary to database."""
        if not paper.paper_id:
            logger.error("Paper has no ID")
            return

        try:
            summary_repo = SummaryRepository(db_manager)

            # Check if summary already exists for this paper and language
            existing_summary = await summary_repo.get_by_paper_and_language(
                paper.paper_id, language
            )

            if existing_summary and force_resummarize:
                # Update existing summary
                updated_summary = self._create_summary_entity(
                    paper, summary_response, db_manager, language
                )
                updated_summary.summary_id = existing_summary.summary_id
                updated_summary.version = existing_summary.version
                await summary_repo.update(updated_summary)
                logger.info(f"Updated summary for paper {paper.arxiv_id} in {language}")
            else:
                # Create new summary
                summary_entity = self._create_summary_entity(
                    paper, summary_response, db_manager, language
                )
                await summary_repo.create(summary_entity)
                logger.info(f"Saved summary for paper {paper.arxiv_id} in {language}")
        except Exception as e:
            logger.error(f"Error saving summary for paper {paper.arxiv_id}: {e}")
            raise

    def _create_summary_entity(
        self,
        paper: PaperEntity,
        summary_response: SummaryResponse,
        db_manager: DatabaseManager,
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

    async def get_paper_summary(
        self,
        paper: PaperEntity,
        db_manager: DatabaseManager,
        language: str = "Korean",
    ) -> SummaryEntity | None:
        """Get summary for a paper in specified language."""
        if not paper.paper_id:
            return None

        summary_repo = SummaryRepository(db_manager)

        try:
            summary_obj = await summary_repo.get_by_paper_and_language(
                paper.paper_id, language
            )
            if not summary_obj and language != "English":
                summary_obj = await summary_repo.get_by_paper_and_language(
                    paper.paper_id, "English"
                )

            return summary_obj
        except Exception as e:
            logger.error(f"Error getting paper summary for {paper.arxiv_id}: {e}")
            return None
