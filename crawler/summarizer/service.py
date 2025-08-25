"""Summarization service for paper abstracts."""

import asyncio

import httpx

from core import get_logger
from core.database.llm_sqlite_manager import LLMSQLiteManager
from crawler.summarizer import (
    SummaryRequest,
    SummaryResponse,
)
from crawler.summarizer.client import SummaryClient

logger = get_logger(__name__)


class SummarizationService:
    """Service for managing paper summarization."""

    def __init__(self) -> None:
        pass

    async def summarize_paper(
        self,
        paper_id: str,
        abstract: str,
        summary_client: SummaryClient,
        db_manager: LLMSQLiteManager,
        language: str = "English",
        interest_section: str = "",
    ) -> SummaryResponse | None:
        """Summarize a paper's abstract.

        Args:
            paper_id: Unique identifier for the paper
            abstract: The paper's abstract text
            summary_client: Summary client instance
            db_manager: LLM database manager instance
            language: Language for the summary
            interest_section: User's interest section for relevance scoring

        Returns:
            SummaryResponse with structured or text summary, or None if failed
        """
        try:
            logger.info(f"Summarizing paper {paper_id}")
            request = SummaryRequest(
                custom_id=paper_id,
                content=abstract,
                language=language,
                interest_section=interest_section,
                use_tools=summary_client.use_tools,
                model=summary_client.model,
            )

            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await summary_client.summarize(request, db_manager)
                    logger.info(f"Successfully summarized paper {paper_id}")
                    return response
                except httpx.ReadTimeout as e:
                    if attempt < max_retries - 1:
                        wait_time = (attempt + 1) * 5  # 5, 10, 15 seconds
                        logger.warning(
                            f"Timeout on attempt {attempt + 1} for paper {paper_id}, "
                            f"retrying in {wait_time} seconds: {e}"
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        logger.error(
                            f"All retry attempts failed for paper {paper_id}: {e}"
                        )
                        raise
                except Exception as e:
                    logger.error(
                        f"Failed to summarize paper {paper_id}: {e}", exc_info=True
                    )
                    raise

            # This should never be reached, but mypy needs it
            return None

        except Exception as e:
            logger.error(f"Failed to summarize paper {paper_id}: {e}", exc_info=True)
            return None

    async def close(self) -> None:
        """Close the summarization service and cleanup resources."""
        # No cleanup needed since summarizer is created per request
        logger.info("SummarizationService closed")
